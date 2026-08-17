import { test } from 'node:test';
import assert from 'node:assert/strict';
import { main, buildContext } from '../src/cli.mjs';
import { PROBE_TARGETS, probeCapabilities, doctor } from '../src/commands/doctor.mjs';
import { Client } from '../src/client.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';
import { captureStreams } from './helpers/capture-streams.mjs';

test('PROBE_TARGETS covers the endpoints recorded in the spec', () => {
  const names = PROBE_TARGETS.map((t) => t.name);
  for (const expected of ['issues', 'states', 'labels', 'cycles', 'modules', 'members']) {
    assert.ok(names.includes(expected), `missing probe target: ${expected}`);
  }
});

test('every probe target declares a workspace or project scope', () => {
  for (const target of PROBE_TARGETS) {
    assert.ok(['workspace', 'project'].includes(target.scope), `bad scope on ${target.name}`);
  }
});

test('probeCapabilities skips project-scoped targets when no project exists', async () => {
  const workspaceTargets = PROBE_TARGETS.filter((t) => t.scope === 'workspace');
  const { fetchImpl, calls } = makeFakeFetch(
    workspaceTargets.map(() => ({ status: 200, body: { results: [] } })),
  );
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const observed = await probeCapabilities(client, null);
  assert.equal(calls.length, workspaceTargets.length);
  assert.equal(observed.members, 200);
  assert.equal(observed.issues, undefined);
});

test('probeCapabilities records the failing status instead of throwing', async () => {
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { results: [] } },
    { status: 404, body: {} },
  ]);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const observed = await probeCapabilities(client, null);
  assert.equal(observed.members, 200);
  assert.equal(observed.pages, 404);
});

test('doctor --probe reports observed capability statuses', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
    { status: 200, body: { results: [] } },
    { status: 200, body: { results: [] } },
  ]);
  await main(['doctor', '--probe', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  const report = JSON.parse(s.outText());
  assert.equal(report.capabilities.members, 200);
});

test('doctor reports identity, workspace and a token fingerprint only', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ]);
  const code = await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  assert.equal(code, 0);
  const report = JSON.parse(s.outText());
  assert.equal(report.workspace, 'cybernetics');
  assert.equal(report.user.display_name, 'avarile');
  assert.equal(report.token, 'plane_api_…beef');
  assert.ok(!s.outText().includes('ffffffffffff'));
});

test('doctor reports the project count it observed', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 3, results: [] } },
  ]);
  await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  assert.equal(JSON.parse(s.outText()).projects, 3);
});

test('doctor surfaces an auth failure as exit code 4', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([{ status: 401, body: { detail: 'bad token' } }]);
  const code = await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_wrong' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  assert.equal(code, 4);
});

test('a bare doctor call does not set or bump checkedAt on the cache', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ]);
  const ctx = buildContext({
    values: { json: true },
    positionals: [],
    deps: {
      streams: s,
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
      cwd: '/nonexistent-cyb-dir',
      configPath: '/nonexistent-cyb-dir/config.json',
      fetchImpl,
      cachePath: '/nonexistent-cyb-dir/cache-bare.json',
      sleep: async () => {},
    },
  });
  await doctor(ctx);
  assert.equal(ctx.cache.capabilities.checkedAt, undefined);
});

test('doctor --probe merges new results into the cache instead of replacing it', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } }, // no projects: project-scoped probes skip
    { status: 200, body: { results: [] } }, // members
    { status: 200, body: { results: [] } }, // pages
  ]);
  const ctx = buildContext({
    values: { json: true, probe: true },
    positionals: [],
    deps: {
      streams: s,
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
      cwd: '/nonexistent-cyb-dir',
      configPath: '/nonexistent-cyb-dir/config.json',
      fetchImpl,
      cachePath: '/nonexistent-cyb-dir/cache-merge.json',
      sleep: async () => {},
    },
  });
  // Simulate an earlier probe that ran against a workspace that did have a
  // project — these entries must survive a probe that has none to check.
  ctx.cache.capabilities = { issues: 200, states: 200, labels: 200, cycles: 200, modules: 200 };
  await doctor(ctx);
  assert.equal(ctx.cache.capabilities.issues, 200);
  assert.equal(ctx.cache.capabilities.states, 200);
  assert.equal(ctx.cache.capabilities.labels, 200);
  assert.equal(ctx.cache.capabilities.cycles, 200);
  assert.equal(ctx.cache.capabilities.modules, 200);
  assert.equal(ctx.cache.capabilities.members, 200);
  assert.ok(ctx.cache.capabilities.checkedAt);
});
