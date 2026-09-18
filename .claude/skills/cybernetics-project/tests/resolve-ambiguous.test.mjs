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

// Real ids returned by the Plane API are UUIDs, so these collision fixtures
// (unlike the shorthand 's1'/'label-a'/'m1' ids used elsewhere in this file)
// use actual UUID-shaped ids — the point of the test is that passing one of
// them back in trips the isUuid() short-circuit.
const UUID_S1 = '11111111-1111-1111-1111-111111111111';
const UUID_S2 = '22222222-2222-2222-2222-222222222222';
const UUID_L1 = '33333333-3333-3333-3333-333333333333';
const UUID_L2 = '44444444-4444-4444-4444-444444444444';
const UUID_M1 = '55555555-5555-5555-5555-555555555555';
const UUID_M2 = '66666666-6666-6666-6666-666666666666';

test('passing the UUID of one of two case-colliding states resolves it directly, without the ambiguity error', async () => {
  const { resolver, calls } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: UUID_S1, name: 'Todo', group: 'unstarted' },
          { id: UUID_S2, name: 'todo', group: 'unstarted' },
        ],
      },
    },
  ]);
  // Prime the collision first, exactly as the hint scenario would: the named
  // lookup fails with the ambiguity error that names UUID_S1 and UUID_S2 as
  // the UUIDs to disambiguate with.
  await assert.rejects(() => resolver.state(UUID_A, 'todo'), (err) => err.code === 3);
  assert.equal(calls.length, 1, 'the map build for the failed lookup is the only request so far');

  const id = await resolver.state(UUID_A, UUID_S1);
  assert.equal(id, UUID_S1);
  assert.equal(calls.length, 1, 'resolving by UUID must add zero requests beyond the map build already paid for');
});

test('passing the UUID of one of two case-colliding labels resolves it directly, without the ambiguity error', async () => {
  const { resolver, calls } = makeResolver([
    { status: 200, body: { results: [{ id: UUID_L1, name: 'Bug' }, { id: UUID_L2, name: 'bug' }] } },
  ]);
  await assert.rejects(() => resolver.label(UUID_A, 'bug'), (err) => err.code === 3);
  assert.equal(calls.length, 1);

  const id = await resolver.label(UUID_A, UUID_L1);
  assert.equal(id, UUID_L1);
  assert.equal(calls.length, 1, 'resolving by UUID must add zero requests beyond the map build already paid for');
});

test('passing the UUID of one of two case-colliding members resolves it directly, without the ambiguity error', async () => {
  const { resolver, calls } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: UUID_M1, display_name: 'alex', email: 'alex@one.test' },
          { id: UUID_M2, display_name: 'Alex', email: 'alex@two.test' },
        ],
      },
    },
  ]);
  await assert.rejects(() => resolver.member('alex'), (err) => err.code === 3);
  assert.equal(calls.length, 1);

  const id = await resolver.member(UUID_M2);
  assert.equal(id, UUID_M2);
  assert.equal(calls.length, 1, 'resolving by UUID must add zero requests beyond the map build already paid for');
});

test('a bogus UUID passed to state/label/member is returned as-is, not rejected locally', async () => {
  const bogus = 'ffffffff-ffff-ffff-ffff-ffffffffffff';
  const { resolver: stateResolver, calls: stateCalls } = makeResolver([]);
  assert.equal(await stateResolver.state(UUID_A, bogus), bogus);
  assert.equal(stateCalls.length, 0);

  const { resolver: labelResolver, calls: labelCalls } = makeResolver([]);
  assert.equal(await labelResolver.label(UUID_A, bogus), bogus);
  assert.equal(labelCalls.length, 0);

  const { resolver: memberResolver, calls: memberCalls } = makeResolver([]);
  assert.equal(await memberResolver.member(bogus), bogus);
  assert.equal(memberCalls.length, 0);
});

test("invalidate('label', …) clears the stale collisions entry, so a no-longer-ambiguous name resolves cleanly (guard bypass fix)", async () => {
  const cache = emptyCache('cybernetics');
  const { resolver } = makeResolver([
    { status: 200, body: { results: [{ id: 'label-a', name: 'Bug' }, { id: 'label-b', name: 'bug' }] } },
    { status: 200, body: { results: [{ id: 'label-a', name: 'Bug' }] } }, // after the rename, only one 'Bug' label remains
  ], { cache });

  await assert.rejects(() => resolver.label(UUID_A, 'bug'), (err) => err.code === 3 && /ambiguous label/.test(err.message));

  resolver.invalidate('label', UUID_A, 'bug');
  assert.equal(cache.byProject[UUID_A].labelCollisions.bug, undefined);

  const id = await resolver.label(UUID_A, 'bug');
  assert.equal(id, 'label-a');
});

test("invalidate('member', …) clears the stale collisions entry, so a no-longer-ambiguous name resolves cleanly (guard bypass fix)", async () => {
  const cache = emptyCache('cybernetics');
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
    { status: 200, body: { results: [{ id: 'm1', display_name: 'alex', email: 'alex@one.test' }] } }, // after the rename
  ], { cache });

  await assert.rejects(() => resolver.member('alex'), (err) => err.code === 3 && /ambiguous member/.test(err.message));

  resolver.invalidate('member', null, 'alex');
  assert.equal(cache.memberCollisions.alex, undefined);

  const id = await resolver.member('alex');
  assert.equal(id, 'm1');
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
