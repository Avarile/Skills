import { test } from 'node:test';
import assert from 'node:assert/strict';
import { list, show, create, remove, PROJECT_COLUMNS } from '../src/commands/project.mjs';
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
