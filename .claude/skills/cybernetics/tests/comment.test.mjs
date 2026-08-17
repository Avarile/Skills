import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commentList, commentAdd } from '../src/commands/comment.mjs';
import { makeCtx, UUID_PROJECT } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

const RAW_ITEM_UUID = '7c9cd656-c9cf-4622-9d2a-b44ad1766113';

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

// Important 3: `resolver.item()` can't know the project for a raw UUID ref
// without an extra request, so it hands back `projectId: null`. commentList
// and commentAdd used to read that field directly, building a request path
// containing the literal string "null". Both must fall back to --project
// (or the configured default) via item.mjs's resolveItemProjectId, exactly
// like `item show` already does.
test('comment list <uuid> with --project resolves the project instead of building /projects/null/', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [] } },
  ], { positionals: [RAW_ITEM_UUID], values: { project: 'CYB' } });

  await commentList(ctx);

  const path = new URL(calls.at(-1).url).pathname;
  assert.equal(
    path,
    `/api/v1/workspaces/cybernetics/projects/${UUID_PROJECT}/issues/${RAW_ITEM_UUID}/comments/`,
  );
  assert.doesNotMatch(path, /projects\/null/);
});

test('comment add <uuid> with --project resolves the project instead of building /projects/null/', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'c1' } },
  ], { positionals: [RAW_ITEM_UUID, 'looks good'], values: { project: 'CYB' } });

  await commentAdd(ctx);

  const path = new URL(calls.at(-1).url).pathname;
  assert.equal(
    path,
    `/api/v1/workspaces/cybernetics/projects/${UUID_PROJECT}/issues/${RAW_ITEM_UUID}/comments/`,
  );
  assert.doesNotMatch(path, /projects\/null/);
});

test('comment list <uuid> with no project available fails with a clear hint, not a null-project request', async () => {
  const { ctx, calls } = makeCtx([], { positionals: [RAW_ITEM_UUID] });

  await assert.rejects(
    () => commentList(ctx),
    (err) => {
      assert.equal(err.code, EXIT.GENERAL);
      assert.match(err.message, /project/i);
      return true;
    },
  );
  assert.equal(calls.length, 0, 'must fail before sending any request');
});
