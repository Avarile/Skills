import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Resolver, isUuid, parseItemRef, suggest } from '../src/resolve.mjs';
import { emptyCache } from '../src/cache.mjs';
import { Client } from '../src/client.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';

const UUID_A = '50fc7f95-db38-4fe8-850b-41643c1ca2f5';
const UUID_B = '8c3d7fcf-662c-44db-8d50-ccb556664063';

function makeResolver(responses, { cache } = {}) {
  const { fetchImpl, calls } = makeFakeFetch(responses);
  const client = new Client({
    baseUrl: 'https://example.test',
    workspace: 'cybernetics',
    token: 'tok',
    fetchImpl,
    sleep: async () => {},
    now: () => 1_000_000,
  });
  const saved = [];
  const resolver = new Resolver({
    client,
    cache: cache ?? emptyCache('cybernetics'),
    persist: (c) => saved.push(c),
    now: () => 1_000_000,
  });
  return { resolver, calls, saved };
}

test('isUuid distinguishes UUIDs from identifiers', () => {
  assert.equal(isUuid(UUID_A), true);
  assert.equal(isUuid('CYB'), false);
  assert.equal(isUuid('CYB-42'), false);
});

test('parseItemRef splits identifier and sequence', () => {
  assert.deepEqual(parseItemRef('CYB-42'), { identifier: 'CYB', sequence: 42 });
  assert.deepEqual(parseItemRef('cyb-7'), { identifier: 'CYB', sequence: 7 });
  assert.equal(parseItemRef('CYB'), null);
  assert.equal(parseItemRef(UUID_A), null);
});

test('suggest finds the nearest candidate', () => {
  assert.equal(suggest('in progres', ['Backlog', 'In Progress', 'Done']), 'In Progress');
  assert.equal(suggest('zzzzzzzzzz', ['Backlog', 'Done']), null);
});

test('project resolves an identifier and caches the result', async () => {
  const { resolver, calls, saved } = makeResolver([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ]);
  const project = await resolver.project('CYB');
  assert.deepEqual(project, { id: UUID_A, identifier: 'CYB', name: 'Core' });
  assert.equal(calls.length, 1);
  assert.equal(saved.at(-1).projects.CYB.id, UUID_A);
});

test('a cached project costs no request', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000 - 1000).toISOString() };
  const { resolver, calls } = makeResolver([], { cache });
  const project = await resolver.project('CYB');
  assert.equal(project.id, UUID_A);
  assert.equal(calls.length, 0);
});

test('a UUID passed as a project ref is returned without a lookup', async () => {
  const { resolver, calls } = makeResolver([]);
  const project = await resolver.project(UUID_A);
  assert.equal(project.id, UUID_A);
  assert.equal(calls.length, 0);
});

test('an unknown project raises a not-found CybError naming the ref', async () => {
  const { resolver } = makeResolver([{ status: 200, body: { results: [] } }]);
  await assert.rejects(
    () => resolver.project('ZZZ'),
    (err) => err.name === 'CybError' && err.code === 3 && /ZZZ/.test(err.message),
  );
});

test('state resolves case-insensitively from the project state list', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: UUID_B, name: 'In Progress', group: 'started' },
          { id: 'other', name: 'Done', group: 'completed' },
        ],
      },
    },
  ]);
  assert.equal(await resolver.state(UUID_A, 'in progress'), UUID_B);
});

test('an unknown state error lists the valid states and suggests the nearest', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: { results: [{ id: UUID_B, name: 'In Progress', group: 'started' }] },
    },
  ]);
  await assert.rejects(
    () => resolver.state(UUID_A, 'in progres'),
    (err) => err.code === 3 && /In Progress/.test(err.hint),
  );
});

test('item resolves CYB-42 via the sequence_id filter when it narrows to one', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  const { resolver, calls } = makeResolver(
    [{ status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } }],
    { cache },
  );
  const item = await resolver.item('CYB-42');
  assert.deepEqual(item, { id: 'item-uuid', projectId: UUID_A, sequence_id: 42 });
  assert.equal(calls.length, 1);
});

test('item falls back to a projected scan when the filter fails to narrow', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  const { resolver } = makeResolver(
    [
      { status: 200, body: { results: [{ id: 'a', sequence_id: 1 }, { id: 'b', sequence_id: 42 }] } },
      {
        status: 200,
        body: {
          results: [{ id: 'a', sequence_id: 1 }, { id: 'b', sequence_id: 42 }],
          next_page_results: false,
          next_cursor: null,
        },
      },
    ],
    { cache },
  );
  const item = await resolver.item('CYB-42');
  assert.equal(item.id, 'b');
});

test('a cached item sequence costs no request', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  cache.byProject[UUID_A] = { states: {}, labels: {}, members: {}, items: { 42: 'item-uuid' }, fetchedAt: null };
  const { resolver, calls } = makeResolver([], { cache });
  assert.equal((await resolver.item('CYB-42')).id, 'item-uuid');
  assert.equal(calls.length, 0);
});

test('an unparseable item ref is rejected with guidance', async () => {
  const { resolver } = makeResolver([]);
  await assert.rejects(
    () => resolver.item('nonsense'),
    (err) => err.code === 3 && /CYB-42/.test(err.hint),
  );
});

test('noCache forces a refetch even when the cache is warm', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  const { fetchImpl, calls } = makeFakeFetch([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ]);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const resolver = new Resolver({ client, cache, persist: () => {}, now: () => 1_000_000, noCache: true });
  await resolver.project('CYB');
  assert.equal(calls.length, 1);
});

test('me is fetched once and cached', async () => {
  const { resolver, calls } = makeResolver([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
  ]);
  assert.equal((await resolver.me()).id, 'me-uuid');
  assert.equal((await resolver.me()).id, 'me-uuid');
  assert.equal(calls.length, 1);
});
