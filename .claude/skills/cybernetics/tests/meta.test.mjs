import { test } from 'node:test';
import assert from 'node:assert/strict';
import { stateList, labelList, labelCreate, labelRemove, memberList } from '../src/commands/meta.mjs';
import { makeCtx, UUID_PROJECT } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

test('state list emits the project states with their groups', async () => {
  const { ctx, outText } = makeCtx([], { positionals: ['CYB'] });
  await stateList(ctx);
  const rows = JSON.parse(outText());
  assert.equal(rows.length, 3);
  assert.equal(rows.find((r) => r.name === 'In Progress').group, 'started');
});

test('label list emits labels', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'l1', name: 'bug', color: '#f00' }] } },
  ], { positionals: ['CYB'] });
  await labelList(ctx);
  assert.equal(JSON.parse(outText())[0].name, 'bug');
});

test('label create posts name and colour', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'l1', name: 'bug', color: '#ff0000' } },
  ], { positionals: ['CYB'], values: { name: 'bug', color: '#ff0000' } });
  await labelCreate(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.name, 'bug');
  assert.equal(body.color, '#ff0000');
});

test('label create requires --name', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB'], values: {}, warmCache: false });
  await assert.rejects(() => labelCreate(ctx), (err) => /--name/.test(err.hint));
  assert.equal(calls.length, 0);
});

test('label delete without --yes refuses', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'l1', name: 'bug' }] } },
  ], { positionals: ['CYB', 'bug'] });
  await assert.rejects(() => labelRemove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});

// Important 5: a cached label uuid can go stale (edited or deleted outside
// this CLI within the TTL), and `label delete` was itself the easiest way
// to cause it — it deleted the label server-side but left its own cache
// entry in place, so the *next* create/delete against that name got a raw
// 400 instead of a clean not-found. Route through the same
// refresh-and-retry contract items already have, and drop the mapping
// immediately after a successful delete too.
test('label delete retries once on a stale cached uuid and clears the mapping after success', async () => {
  const { ctx, calls } = makeCtx([
    { status: 404, body: {} },
    { status: 200, body: { results: [{ id: 'fresh-label-uuid', name: 'bug' }] } },
    { status: 204, body: undefined },
  ], { positionals: ['CYB', 'bug'], values: { yes: true } });
  ctx.cache.byProject[UUID_PROJECT].labels.bug = 'stale-label-uuid';

  await labelRemove(ctx);

  assert.match(calls[0].url, /stale-label-uuid/, 'first DELETE hits the stale cached uuid');
  assert.equal(calls.at(-1).init.method, 'DELETE');
  assert.match(calls.at(-1).url, /fresh-label-uuid/, 'retry DELETE hits the freshly resolved uuid');
  assert.equal(
    ctx.cache.byProject[UUID_PROJECT].labels.bug,
    undefined,
    'the mapping must not be left behind after a successful delete',
  );
});

test('label delete propagates a not-found as exit 3 when the label is gone even after a refresh', async () => {
  const { ctx, calls } = makeCtx([
    { status: 404, body: {} },
    { status: 200, body: { results: [] } },
  ], { positionals: ['CYB', 'bug'], values: { yes: true } });
  ctx.cache.byProject[UUID_PROJECT].labels.bug = 'stale-label-uuid';

  await assert.rejects(() => labelRemove(ctx), (err) => err.code === EXIT.NOT_FOUND);
  assert.equal(calls.length, 2, 'must not attempt a second retry');
});

test('member list emits workspace members', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', display_name: 'avarile', email: 'a@b.c', role: 20 }] } },
  ]);
  await memberList(ctx);
  assert.equal(JSON.parse(outText())[0].display_name, 'avarile');
});

test('member list never emits raw emails in table mode', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', display_name: 'avarile', email: 'a@b.c', role: 20 }] } },
  ], { mode: 'plain' });
  await memberList(ctx);
  assert.match(outText(), /avarile/);
  assert.doesNotMatch(outText(), /a@b\.c/);
});
