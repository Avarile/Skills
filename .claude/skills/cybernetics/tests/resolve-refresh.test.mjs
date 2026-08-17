import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Resolver } from '../src/resolve.mjs';
import { emptyCache } from '../src/cache.mjs';
import { Client } from '../src/client.mjs';
import { ApiError } from '../src/errors.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';

// Split out from resolve.test.mjs: these tests cover the invalidate()/
// withRefresh() cache-invalidation primitives (I7) rather than name/ref
// resolution itself, and keep both files under the project's line limit.

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
  const saved = [];
  const resolver = new Resolver({
    client,
    cache: cache ?? emptyCache('cybernetics'),
    persist: (c) => saved.push(c),
    now: () => 1_000_000,
  });
  return { resolver, calls, saved };
}

test('invalidate drops the targeted cache entry for each kind and persists', () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  cache.byProject[UUID_A] = {
    states: { todo: 'state-uuid' },
    stateList: [{ id: 'state-uuid', name: 'Todo', group: 'unstarted' }],
    labels: { bug: 'label-uuid' },
    members: {},
    items: { 42: 'item-uuid' },
    statesFetchedAt: new Date(1_000_000).toISOString(),
    labelsFetchedAt: new Date(1_000_000).toISOString(),
    itemsFetchedAt: new Date(1_000_000).toISOString(),
  };
  cache.members = { 'ava rile': 'member-uuid' };
  cache.membersFetchedAt = new Date(1_000_000).toISOString();

  const { resolver, saved } = makeResolver([], { cache });

  resolver.invalidate('project', null, 'CYB');
  assert.equal(cache.projects.CYB, undefined);

  resolver.invalidate('item', UUID_A, 42);
  assert.equal(cache.byProject[UUID_A].items[42], undefined);

  resolver.invalidate('label', UUID_A, 'Bug');
  assert.equal(cache.byProject[UUID_A].labels.bug, undefined);

  resolver.invalidate('member', null, 'Ava Rile');
  assert.equal(cache.members['ava rile'], undefined);

  resolver.invalidate('state', UUID_A);
  assert.equal(cache.byProject[UUID_A].statesFetchedAt, null);
  assert.equal(cache.byProject[UUID_A].stateList, null);

  assert.equal(saved.length, 5);
});

test('withRefresh retries exactly once on a 404 and then succeeds', async () => {
  let attempts = 0;
  const fn = async () => {
    attempts++;
    if (attempts === 1) throw new ApiError(404, {}, '/issues/stale-uuid/');
    return 'ok';
  };
  let invalidated = 0;
  const { resolver } = makeResolver([]);
  const result = await resolver.withRefresh(fn, () => { invalidated++; });
  assert.equal(result, 'ok');
  assert.equal(attempts, 2);
  assert.equal(invalidated, 1);
});

test('withRefresh propagates a second 404 after exactly one retry', async () => {
  let attempts = 0;
  const fn = async () => {
    attempts++;
    throw new ApiError(404, {}, '/issues/stale-uuid/');
  };
  let invalidated = 0;
  const { resolver } = makeResolver([]);
  await assert.rejects(
    () => resolver.withRefresh(fn, () => { invalidated++; }),
    (err) => err instanceof ApiError && err.status === 404,
  );
  assert.equal(attempts, 2);
  assert.equal(invalidated, 1);
});

test('withRefresh propagates a non-404 error without invalidating or retrying', async () => {
  let attempts = 0;
  const fn = async () => {
    attempts++;
    throw new ApiError(500, {}, '/issues/');
  };
  let invalidated = 0;
  const { resolver } = makeResolver([]);
  await assert.rejects(
    () => resolver.withRefresh(fn, () => { invalidated++; }),
    (err) => err instanceof ApiError && err.status === 500,
  );
  assert.equal(attempts, 1);
  assert.equal(invalidated, 0);
});
