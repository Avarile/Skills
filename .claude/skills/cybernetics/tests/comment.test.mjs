import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commentList, commentAdd } from '../src/commands/comment.mjs';
import { makeCtx } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

test('comment list fetches the comments for a resolved item', async () => {
  const { ctx, calls, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'c1', comment_html: '<p>hi</p>', created_at: '2026-08-17T00:00:00Z' }] } },
  ], { positionals: ['CYB-42'] });
  await commentList(ctx);
  assert.match(calls.at(-1).url, /comments/);
  assert.equal(JSON.parse(outText()).length, 1);
});

test('comment add posts comment_html wrapped from plain text', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 201, body: { id: 'c1' } },
  ], { positionals: ['CYB-42', 'looks good'] });
  await commentAdd(ctx);
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), { comment_html: '<p>looks good</p>' });
});

test('comment add requires text', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB-42'] });
  await assert.rejects(() => commentAdd(ctx), (err) => err.code === EXIT.GENERAL);
});

test('comment add escapes HTML metacharacters in the supplied text', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 201, body: { id: 'c1' } },
  ], { positionals: ['CYB-42', 'a < b & c'] });
  await commentAdd(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.comment_html, '<p>a &lt; b &amp; c</p>');
});
