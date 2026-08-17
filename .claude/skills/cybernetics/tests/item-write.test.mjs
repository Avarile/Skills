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

test('item create requires --name', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB'], values: {} });
  await assert.rejects(() => create(ctx), (err) => err.code === EXIT.GENERAL && /--name/.test(err.hint));
});

test('item create rejects an invalid priority before any request', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB'], values: { name: 'x', priority: 'critical' } });
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

test('item move is sugar for updating the state', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42 } },
  ], { positionals: ['CYB-42', 'In Progress'] });
  await move(ctx);
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), { state: UUID_STATE_PROGRESS });
});

test('item move requires a target state', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB-42'] });
  await assert.rejects(() => move(ctx), (err) => /state/.test(err.message));
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
