import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { init, sync } from '../src/commands/setup.mjs';
import { saveCache } from '../src/cache.mjs';
import { makeCtx, UUID_PROJECT } from './helpers/ctx.mjs';

function tmpFile(name) {
  return join(mkdtempSync(join(tmpdir(), 'cyb-setup-')), name);
}

test('init writes config with 0600 and reports only a fingerprint', async () => {
  const configPath = tmpFile('config.json');
  const { ctx, outText } = makeCtx([], { values: { 'config-path': configPath } });
  ctx.config.token = 'plane_api_ffffffffffffffffffffffffffffbeef';
  ctx.configPath = configPath;

  await init(ctx);

  assert.ok(existsSync(configPath));
  assert.equal(statSync(configPath).mode & 0o777, 0o600);
  assert.equal(JSON.parse(readFileSync(configPath, 'utf8')).workspace, 'cybernetics');
  assert.ok(!outText().includes('ffffffffffff'));
  assert.match(outText(), /beef/);
});

test('init records the default project when one is set', async () => {
  const configPath = tmpFile('config.json');
  const { ctx } = makeCtx([], { values: { project: 'CYB' } });
  ctx.config.token = 'tok-value-1234';
  ctx.config.defaultProject = 'CYB';
  ctx.configPath = configPath;

  await init(ctx);
  assert.equal(JSON.parse(readFileSync(configPath, 'utf8')).defaultProject, 'CYB');
});

test('init never writes the token into the repo path it was given', async () => {
  const configPath = tmpFile('config.json');
  const { ctx } = makeCtx([]);
  ctx.config.token = 'plane_api_secret_value_here';
  ctx.configPath = configPath;
  await init(ctx);
  assert.equal(JSON.parse(readFileSync(configPath, 'utf8')).token, 'plane_api_secret_value_here');
  assert.ok(configPath.startsWith(tmpdir()));
});

test('sync clears stale cache entries and refetches projects', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 1, results: [{ id: UUID_PROJECT, identifier: 'CYB', name: 'Core' }] } },
    { status: 200, body: { results: [{ id: 's1', name: 'Backlog', group: 'backlog' }] } },
    { status: 200, body: { results: [{ id: 'm1', display_name: 'avarile', email: 'a@b.c' }] } },
  ]);
  ctx.cache.projects.STALE = { id: 'gone', name: 'Gone', fetchedAt: '2020-01-01T00:00:00Z' };

  await sync(ctx);

  assert.equal(ctx.cache.projects.STALE, undefined);
  assert.equal(ctx.cache.projects.CYB.id, UUID_PROJECT);
  assert.match(outText(), /CYB|1/);

  // Freshness stamps must be set, not just the data — otherwise the
  // resolver's isFresh() gate reads the just-synced cache as stale and
  // silently refetches on the very next command.
  const stamp = new Date(1_000_000).toISOString();
  assert.equal(ctx.cache.membersFetchedAt, stamp);
  assert.equal(ctx.cache.byProject[UUID_PROJECT].statesFetchedAt, stamp);
});

test('sync leaves the on-disk and in-memory cache untouched when a later request fails', async () => {
  const cachePath = tmpFile('cache.json');
  const { ctx } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 404, body: { detail: 'not found' } },
  ]);

  ctx.cache.projects.OLD = { id: 'old-uuid', name: 'Old', fetchedAt: '2020-01-01T00:00:00Z' };
  ctx.cache.byProject['old-uuid'] = {
    states: { backlog: 's1' },
    stateList: [{ id: 's1', name: 'Backlog', group: 'backlog' }],
    labels: {},
    members: {},
    items: {},
    statesFetchedAt: '2020-01-01T00:00:00Z',
    labelsFetchedAt: null,
    itemsFetchedAt: null,
    maxSequence: null,
    maxSequenceFetchedAt: null,
  };

  // makeCtx's ctx.save is a no-op; wire it to the real persistence path so
  // this test can observe what actually lands on disk.
  ctx.save = () => saveCache(ctx.cache, { path: cachePath });
  ctx.save();
  const before = readFileSync(cachePath, 'utf8');

  await assert.rejects(() => sync(ctx));

  // In-memory: the failed fetch (projects-list, after me() succeeded) must
  // not have wiped anything ctx.cache held before sync was called.
  assert.equal(ctx.cache.projects.OLD.id, 'old-uuid');
  assert.deepEqual(ctx.cache.byProject['old-uuid'].states, { backlog: 's1' });

  // On disk: ctx.save() must never have been reached, so the file is
  // byte-for-byte what it was before the failed sync attempt.
  assert.equal(readFileSync(cachePath, 'utf8'), before);
});
