import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Resolver, buildNameMap } from '../src/resolve.mjs';
import { emptyCache } from '../src/cache.mjs';
import { Client } from '../src/client.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';

// Split out from resolve.test.mjs: covers ambiguous-name detection (I3, the
// final-review fix), keeping resolve.test.mjs under the project's line limit
// — same reasoning as resolve-refresh.test.mjs.

const UUID_A = '50fc7f95-db38-4fe8-850b-41643c1ca2f5';

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
  const resolver = new Resolver({
    client,
    cache: cache ?? emptyCache('cybernetics'),
    persist: () => {},
    now: () => 1_000_000,
  });
  return { resolver, calls };
}

test('buildNameMap records a collision without throwing, and excludes the key from the map', () => {
  const { map, collisions } = buildNameMap(
    [{ id: 'a', name: 'Bug' }, { id: 'b', name: 'bug' }, { id: 'c', name: 'Feature' }],
    (x) => x.name,
  );
  assert.equal(map.bug, undefined);
  assert.equal(map.feature, 'c');
  assert.equal(collisions.bug.length, 2);
});

test('two labels differing only in case raise an ambiguous-label error naming both candidates', async () => {
  const { resolver } = makeResolver([
    { status: 200, body: { results: [{ id: 'label-a', name: 'Bug' }, { id: 'label-b', name: 'bug' }] } },
  ]);
  await assert.rejects(
    () => resolver.label(UUID_A, 'bug'),
    (err) =>
      err.name === 'CybError' &&
      err.code === 3 &&
      /ambiguous label/.test(err.message) &&
      /label-a/.test(err.hint) &&
      /label-b/.test(err.hint),
  );
});

test('an unrelated label collision does not break lookup of a different, unambiguous label', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: 'label-a', name: 'Bug' },
          { id: 'label-b', name: 'bug' },
          { id: 'label-c', name: 'Feature' },
        ],
      },
    },
  ]);
  const id = await resolver.label(UUID_A, 'Feature');
  assert.equal(id, 'label-c');
});

test('two states differing only in case raise an ambiguous-state error naming both candidates', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: { results: [{ id: 's1', name: 'Todo', group: 'unstarted' }, { id: 's2', name: 'todo', group: 'unstarted' }] },
    },
  ]);
  await assert.rejects(
    () => resolver.state(UUID_A, 'todo'),
    (err) => err.code === 3 && /ambiguous state/.test(err.message) && /s1/.test(err.hint) && /s2/.test(err.hint),
  );
});

test('an unrelated state collision does not break lookup of a different, unambiguous state', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: 's1', name: 'Todo', group: 'unstarted' },
          { id: 's2', name: 'todo', group: 'unstarted' },
          { id: 's3', name: 'Done', group: 'completed' },
        ],
      },
    },
  ]);
  assert.equal(await resolver.state(UUID_A, 'Done'), 's3');
});

test('two members whose display names differ only in case raise an ambiguous-member error naming both', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: 'm1', display_name: 'alex', email: 'alex@one.test' },
          { id: 'm2', display_name: 'Alex', email: 'alex@two.test' },
        ],
      },
    },
  ]);
  await assert.rejects(
    () => resolver.member('alex'),
    (err) => err.code === 3 && /ambiguous member/.test(err.message) && /m1/.test(err.hint) && /m2/.test(err.hint),
  );
});

test('a member-name collision does not break resolving that member by their (unique) email', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: 'm1', display_name: 'alex', email: 'alex@one.test' },
          { id: 'm2', display_name: 'Alex', email: 'alex@two.test' },
        ],
      },
    },
  ]);
  const id = await resolver.member('alex@two.test');
  assert.equal(id, 'm2');
});

test('a cached ambiguous label is rejected again with zero extra requests inside the TTL', async () => {
  const cache = emptyCache('cybernetics');
  const { resolver, calls } = makeResolver([
    { status: 200, body: { results: [{ id: 'label-a', name: 'Bug' }, { id: 'label-b', name: 'bug' }] } },
  ], { cache });

  await assert.rejects(() => resolver.label(UUID_A, 'bug'), (err) => err.code === 3);
  assert.equal(calls.length, 1);

  await assert.rejects(() => resolver.label(UUID_A, 'bug'), (err) => err.code === 3 && /ambiguous label/.test(err.message));
  assert.equal(calls.length, 1, 'the second lookup must be served from cache, not refetched');
});
