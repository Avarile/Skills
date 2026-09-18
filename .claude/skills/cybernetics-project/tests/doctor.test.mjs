import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { main, buildContext } from '../src/cli.mjs';
import { PROBE_TARGETS, probeCapabilities, doctor } from '../src/commands/doctor.mjs';
import { Client } from '../src/client.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';
import { captureStreams } from './helpers/capture-streams.mjs';

// Every test gets its own throwaway directory rather than a shared
// '/nonexistent-cyb-dir' path. As root (the default in most CI images),
// `mkdirSync` under `/` succeeds instead of failing, so a shared path would
// make these tests share one real cache file across the whole file —
// `resolver.me()` served from an earlier test's cache shifts every
// subsequent fake-fetch response by one, and it would write a directory to
// the filesystem root besides.
function tmpPaths() {
  const dir = mkdtempSync(join(tmpdir(), 'cyb-doctor-test-'));
  return { cwd: dir, configPath: join(dir, 'config.json'), cachePath: join(dir, 'cache.json') };
}

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
  const { observed } = await probeCapabilities(client, null);
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
  const { observed } = await probeCapabilities(client, null);
  assert.equal(observed.members, 200);
  assert.equal(observed.pages, 404);
});

test('probeCapabilities omits a 5xx status as unknown instead of recording it as a capability', async () => {
  // 5xx is retryable, so a sustained 500 on `pages` costs all 3 attempts
  // before the client gives up and throws.
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { results: [] } }, // members
    { status: 500, body: {} }, // pages attempt 1
    { status: 500, body: {} }, // pages attempt 2
    { status: 500, body: {} }, // pages attempt 3 -> throws
  ]);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const { observed, unknown } = await probeCapabilities(client, null);
  assert.equal(observed.members, 200);
  assert.equal(observed.pages, undefined);
  assert.deepEqual(unknown, ['pages']);
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
    ...tmpPaths(),
    fetchImpl,
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
    ...tmpPaths(),
    fetchImpl,
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
    ...tmpPaths(),
    fetchImpl,
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
    ...tmpPaths(),
    fetchImpl,
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
      ...tmpPaths(),
      fetchImpl,
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
      ...tmpPaths(),
      fetchImpl,
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

test('doctor --probe does not clobber a pre-existing capability entry with an unknown 5xx result', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } }, // no projects: project-scoped probes skip
    { status: 200, body: { results: [] } }, // members
    { status: 500, body: {} }, // pages attempt 1
    { status: 500, body: {} }, // pages attempt 2
    { status: 500, body: {} }, // pages attempt 3 -> throws, recorded as unknown
  ]);
  const ctx = buildContext({
    values: { json: true, probe: true },
    positionals: [],
    deps: {
      streams: s,
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
      ...tmpPaths(),
      fetchImpl,
      sleep: async () => {},
    },
  });
  // A previous, conclusive probe recorded `pages` as present.
  ctx.cache.capabilities = { pages: 200 };
  await doctor(ctx);
  assert.equal(ctx.cache.capabilities.pages, 200, 'a transient 500 must not clobber the known-good value');
  assert.equal(ctx.cache.capabilities.members, 200);
  assert.ok(ctx.cache.capabilities.checkedAt);

  const report = JSON.parse(s.outText());
  assert.equal(report.capabilities.pages, undefined);
  assert.deepEqual(report.capabilitiesUnknown, ['pages']);
});
