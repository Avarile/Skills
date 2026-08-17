import { test } from 'node:test';
import assert from 'node:assert/strict';
import { list, show, create, update, remove, PROJECT_COLUMNS } from '../src/commands/project.mjs';
import { Client } from '../src/client.mjs';
import { Resolver } from '../src/resolve.mjs';
import { emptyCache } from '../src/cache.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';
import { EXIT } from '../src/errors.mjs';

const UUID_A = '50fc7f95-db38-4fe8-850b-41643c1ca2f5';

export function makeCtx(responses, { values = {}, positionals = [], mode = 'json' } = {}) {
  const { fetchImpl, calls } = makeFakeFetch(responses);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const cache = emptyCache('cybernetics');
  const out = [];
  const ctx = {
    config: { baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok', defaultProject: null, defaults: { limit: 30 } },
    client, cache,
    resolver: new Resolver({ client, cache, persist: () => {}, now: () => 1_000_000 }),
    save: () => {},
    mode,
    streams: { stdout: { write: (s) => out.push(s), isTTY: false }, stderr: { write: () => {} } },
    values: { limit: undefined, ...values },
    positionals,
  };
  return { ctx, calls, outText: () => out.join('') };
}

test('PROJECT_COLUMNS exposes key, name and id', () => {
  assert.deepEqual(PROJECT_COLUMNS.map((c) => c.key), ['identifier', 'name', 'id']);
});

test('project list emits the projects it fetched', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ]);
  await list(ctx);
  assert.equal(JSON.parse(outText())[0].identifier, 'CYB');
});

test('project list reports an empty workspace without crashing', async () => {
  const { ctx, outText } = makeCtx([{ status: 200, body: { total_count: 0, results: [] } }], { mode: 'plain' });
  await list(ctx);
  assert.match(outText(), /no results/);
});

test('project show resolves an identifier then fetches the record', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
    { status: 200, body: { id: UUID_A, identifier: 'CYB', name: 'Core', description: 'd' } },
  ], { positionals: ['CYB'] });
  await show(ctx);
  assert.equal(JSON.parse(outText()).id, UUID_A);
});

test('project create posts name and identifier and uppercases the identifier', async () => {
  const { ctx, calls } = makeCtx([{ status: 201, body: { id: UUID_A, identifier: 'CYB', name: 'Core' } }], {
    values: { name: 'Core', identifier: 'cyb' },
  });
  await create(ctx);
  assert.equal(JSON.parse(calls[0].init.body).identifier, 'CYB');
  assert.equal(JSON.parse(calls[0].init.body).name, 'Core');
});

test('project create requires --name and --identifier', async () => {
  const { ctx } = makeCtx([], { values: { name: 'Core' } });
  await assert.rejects(() => create(ctx), (err) => err.code === EXIT.GENERAL);
});

test('project create rejects an identifier over the 10-char instance limit', async () => {
  const { ctx } = makeCtx([], { values: { name: 'Core', identifier: 'WAYTOOLONGIDENT' } });
  await assert.rejects(() => create(ctx), (err) => /10/.test(err.message));
});

test('project delete without --yes refuses and issues no request', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ], { positionals: ['CYB'] });
  await assert.rejects(() => remove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});

test('project delete with --yes issues the DELETE', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
    { status: 204, body: undefined },
  ], { positionals: ['CYB'], values: { yes: true } });
  await remove(ctx);
  assert.equal(calls.at(-1).init.method, 'DELETE');
});

test('project update patches the resolved project', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
    { status: 200, body: { id: UUID_A, identifier: 'CYB', name: 'Renamed' } },
  ], { positionals: ['CYB'], values: { name: 'Renamed' } });
  await update(ctx);
  const patch = calls.at(-1);
  assert.equal(patch.init.method, 'PATCH');
  assert.deepEqual(JSON.parse(patch.init.body), { name: 'Renamed' });
});

test('project update requires --name or --description', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ], { positionals: ['CYB'], values: {} });
  await assert.rejects(() => update(ctx), (err) => /nothing to update/.test(err.message));
  assert.ok(calls.every((c) => c.init.method !== 'PATCH'));
});

// Important 5: a cached project uuid can go stale (the project was deleted
// or its id otherwise changed outside this CLI within the TTL). `update`
// and `remove` now route through the same refresh-and-retry contract items
// already have — on a 404, drop the mapping, re-resolve by ref, and retry
// exactly once before failing.
test('project update retries once on a stale cached uuid and succeeds', async () => {
  const { ctx, calls } = makeCtx([
    { status: 404, body: {} },
    { status: 200, body: { total_count: 1, results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
    { status: 200, body: { id: UUID_A, identifier: 'CYB', name: 'Renamed' } },
  ], { positionals: ['CYB'], values: { name: 'Renamed' } });
  ctx.cache.projects.CYB = { id: 'stale-project-uuid', name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };

  await update(ctx);

  assert.match(calls[0].url, /stale-project-uuid/, 'first PATCH hits the stale cached uuid');
  assert.match(calls.at(-1).url, new RegExp(UUID_A), 'retry PATCH hits the freshly resolved uuid');
  assert.equal(calls.at(-1).init.method, 'PATCH');
});

test('project delete retries once on a stale cached uuid, succeeds, and cleans up the fresh mapping', async () => {
  const { ctx, calls } = makeCtx([
    { status: 404, body: {} },
    { status: 200, body: { total_count: 1, results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
    { status: 204, body: undefined },
  ], { positionals: ['CYB'], values: { yes: true } });
  ctx.cache.projects.CYB = { id: 'stale-project-uuid', name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };

  await remove(ctx);

  assert.match(calls[0].url, /stale-project-uuid/, 'first DELETE hits the stale cached uuid');
  assert.match(calls.at(-1).url, new RegExp(UUID_A), 'retry DELETE hits the freshly resolved uuid');
  assert.equal(calls.at(-1).init.method, 'DELETE');
  assert.equal(ctx.cache.projects.CYB, undefined, 'the mapping to the deleted project must not survive');
});

// The "worst residue" case from the review: resolving a project by
// identifier caches identifier -> uuid, and then deleting *that same
// project* by its raw uuid used to key the cache cleanup off
// `project.identifier`, which is null for a uuid ref — deleting
// cache.projects[''], a no-op, and leaving the stale identifier mapping in
// place pointing at a now-deleted project.
test('project delete by uuid cleans up the identifier cache entry that pointed at it', async () => {
  const { ctx } = makeCtx([
    { status: 204, body: undefined },
  ], { positionals: [UUID_A], values: { yes: true } });
  ctx.cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };

  await remove(ctx);

  assert.equal(ctx.cache.projects.CYB, undefined);
});
