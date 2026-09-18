import { test } from 'node:test';
import assert from 'node:assert/strict';
import { create, update, move, assign, remove } from '../src/commands/item.mjs';
import { makeCtx, UUID_STATE_PROGRESS, UUID_PROJECT } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

test('item create posts name and resolved state', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'new-uuid', sequence_id: 1, name: 'Fix auth', state: UUID_STATE_PROGRESS } },
  ], { positionals: ['CYB'], values: { name: 'Fix auth', state: 'In Progress' } });
  await create(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.name, 'Fix auth');
  assert.equal(body.state, UUID_STATE_PROGRESS);
});

test('item create requires --name, cold cache, zero requests', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB'], values: {}, warmCache: false });
  await assert.rejects(() => create(ctx), (err) => err.code === EXIT.GENERAL && /--name/.test(err.hint));
  assert.equal(calls.length, 0);
});

// warmCache: false is load-bearing here: with the default warm cache,
// `cache.projects.CYB` is already fresh, so the project resolves from cache
// and the test would pass even if the priority check ran after the resolver
// call. A cold cache is what actually proves the check runs before any
// request — see task-10-review.md's Important finding.
test('item create rejects an invalid priority before any request', async () => {
  const { ctx, calls } = makeCtx([], {
    positionals: ['CYB'], values: { name: 'x', priority: 'critical' }, warmCache: false,
  });
  await assert.rejects(() => create(ctx), (err) => /invalid priority/.test(err.message));
  assert.equal(calls.length, 0);
});

test('item create maps --description to description_html', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'a', sequence_id: 1, name: 'x' } },
  ], { positionals: ['CYB'], values: { name: 'x', description: 'hello' } });
  await create(ctx);
  assert.equal(JSON.parse(calls.at(-1).init.body).description_html, '<p>hello</p>');
});

// Important 4: `comment add` already escaped its text; `--description` did
// not, so a description containing markup-looking characters (a pasted
// stack trace, "a < b", "Foo & Bar") was either corrupted or, worse, stored
// as literal HTML. Both create and update must escape it the same way.
test('item create escapes HTML metacharacters in --description', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'a', sequence_id: 1, name: 'x' } },
  ], { positionals: ['CYB'], values: { name: 'x', description: '<script>x</script> a & b' } });
  await create(ctx);
  assert.equal(
    JSON.parse(calls.at(-1).init.body).description_html,
    '<p>&lt;script&gt;x&lt;/script&gt; a &amp; b</p>',
  );
});

test('item update escapes HTML metacharacters in --description', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42 } },
  ], { positionals: ['CYB-42'], values: { description: '<script>x</script> a & b' } });
  await update(ctx);
  assert.equal(
    JSON.parse(calls.at(-1).init.body).description_html,
    '<p>&lt;script&gt;x&lt;/script&gt; a &amp; b</p>',
  );
});

test('item create resolves --parent to a uuid', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'parent-uuid', sequence_id: 1 }] } },
    { status: 201, body: { id: 'a', sequence_id: 2, name: 'child' } },
  ], { positionals: ['CYB'], values: { name: 'child', parent: 'CYB-1' } });
  await create(ctx);
  assert.equal(JSON.parse(calls.at(-1).init.body).parent, 'parent-uuid');
});

test('item update PATCHes only the fields supplied', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42, name: 'renamed' } },
  ], { positionals: ['CYB-42'], values: { name: 'renamed' } });
  await update(ctx);
  const patch = calls.at(-1);
  assert.equal(patch.init.method, 'PATCH');
  assert.deepEqual(JSON.parse(patch.init.body), { name: 'renamed' });
});

test('item update with no fields is rejected', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
  ], { positionals: ['CYB-42'], values: {} });
  await assert.rejects(() => update(ctx), (err) => /nothing to update/.test(err.message));
});

test('item update rejects an invalid priority before any request', async () => {
  const { ctx, calls } = makeCtx([], {
    positionals: ['CYB-42'], values: { priority: 'bogus' }, warmCache: false,
  });
  await assert.rejects(() => update(ctx), (err) => /invalid priority/.test(err.message));
  assert.equal(calls.length, 0, 'must reject before the item-resolution GET');
});

test('item move is sugar for updating the state', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42 } },
  ], { positionals: ['CYB-42', 'In Progress'] });
  await move(ctx);
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), { state: UUID_STATE_PROGRESS });
});

// `move` and `assign` have no --priority option (src/cli.mjs registers
// `options: {}` for both), so the equivalent locally-checkable input for
// them is the required positional (target state / assignee). warmCache:
// false proves the check runs before mutateItem's item-resolution GET.
test('item move requires a target state, cold cache, zero requests', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB-42'], warmCache: false });
  await assert.rejects(() => move(ctx), (err) => /state/.test(err.message));
  assert.equal(calls.length, 0);
});

test('item assign requires an assignee, cold cache, zero requests', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB-42'], warmCache: false });
  await assert.rejects(() => assign(ctx), (err) => /assignee/.test(err.message));
  assert.equal(calls.length, 0);
});

test('item assign resolves the member and PATCHes assignees', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'member-uuid', display_name: 'avarile', email: 'a@b.c' }] } },
    { status: 200, body: { id: 'item-uuid' } },
  ], { positionals: ['CYB-42', 'avarile'] });
  await assign(ctx);
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), { assignees: ['member-uuid'] });
});

test('item delete without --yes refuses and issues no DELETE', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
  ], { positionals: ['CYB-42'] });
  await assert.rejects(() => remove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});

test('item delete with --yes issues the DELETE and drops the cache entry', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 204, body: undefined },
  ], { positionals: ['CYB-42'], values: { yes: true } });
  await remove(ctx);
  assert.equal(calls.at(-1).init.method, 'DELETE');
  assert.equal(ctx.cache.byProject[UUID_PROJECT].items[42], undefined);
});

// Amendment: route mutations through mutateItem() so a 404 against a cached
// item UUID (the work item was deleted server-side after we cached its id)
// triggers exactly one refresh-and-retry, per the spec quoted in the task
// brief. These two tests pre-seed a stale mapping so the first resolution is
// a cache hit (no network call), forcing the 404 to come from the mutation
// request itself — the exact scenario the amendment describes.
test('item update on a stale cached UUID invalidates, re-resolves, and retries the PATCH exactly once', async () => {
  const { ctx, calls } = makeCtx([
    { status: 404, body: { detail: 'not found' } },
    { status: 200, body: { results: [{ id: 'fresh-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'fresh-uuid', sequence_id: 42, name: 'renamed' } },
  ], { positionals: ['CYB-42'], values: { name: 'renamed' } });
  ctx.cache.byProject[UUID_PROJECT].items[42] = 'stale-uuid';

  await update(ctx);

  assert.equal(calls.length, 3, 'exactly one refresh-and-retry: PATCH, GET refetch, PATCH retry');
  assert.equal(
    new URL(calls[0].url).pathname,
    `/api/v1/workspaces/cybernetics/projects/${UUID_PROJECT}/issues/stale-uuid/`,
  );
  assert.equal(
    new URL(calls.at(-1).url).pathname,
    `/api/v1/workspaces/cybernetics/projects/${UUID_PROJECT}/issues/fresh-uuid/`,
  );
  assert.equal(ctx.cache.byProject[UUID_PROJECT].items[42], 'fresh-uuid');
});

test('item update propagates a second 404 as exit 3 after exactly one retry', async () => {
  const { ctx, calls } = makeCtx([
    { status: 404, body: { detail: 'not found' } },
    { status: 200, body: { results: [{ id: 'still-uuid', sequence_id: 42 }] } },
    { status: 404, body: { detail: 'not found' } },
  ], { positionals: ['CYB-42'], values: { name: 'renamed' } });
  ctx.cache.byProject[UUID_PROJECT].items[42] = 'stale-uuid';

  await assert.rejects(() => update(ctx), (err) => err.code === EXIT.NOT_FOUND);
  assert.equal(calls.length, 3, 'must not attempt a second retry');
});
