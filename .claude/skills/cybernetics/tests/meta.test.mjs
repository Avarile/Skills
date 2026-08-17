import { test } from 'node:test';
import assert from 'node:assert/strict';
import { stateList, labelList, labelCreate, labelRemove, memberList } from '../src/commands/meta.mjs';
import { makeCtx } from './helpers/ctx.mjs';
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
