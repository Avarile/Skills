import { test } from 'node:test';
import assert from 'node:assert/strict';
import { list, show, decorate, ITEM_COLUMNS, LIST_FIELDS } from '../src/commands/item.mjs';
import { EXIT } from '../src/errors.mjs';
import { makeCtx, STATE_LIST, UUID_STATE_PROGRESS, UUID_PROJECT } from './helpers/ctx.mjs';

const RAW_ITEM_UUID = '11111111-1111-1111-1111-111111111111';

test('LIST_FIELDS is the token-bounded projection from the spec', () => {
  assert.deepEqual(LIST_FIELDS, ['id', 'sequence_id', 'name', 'state', 'priority', 'assignees']);
});

test('ITEM_COLUMNS leads with the human reference', () => {
  assert.equal(ITEM_COLUMNS[0].key, 'ref');
});

test('decorate builds CYB-42 refs and resolves state names', () => {
  const rows = decorate(
    [{ id: 'a', sequence_id: 42, name: 'Fix auth', state: UUID_STATE_PROGRESS, priority: 'high' }],
    { project: { identifier: 'CYB' }, states: STATE_LIST },
  );
  assert.equal(rows[0].ref, 'CYB-42');
  assert.equal(rows[0].state, 'In Progress');
  assert.equal(rows[0].name, 'Fix auth');
});

test('decorate falls back to the raw state id when it is unknown', () => {
  const rows = decorate(
    [{ id: 'a', sequence_id: 1, name: 'x', state: 'unmapped', priority: 'none' }],
    { project: { identifier: 'CYB' }, states: STATE_LIST },
  );
  assert.equal(rows[0].state, 'unmapped');
});

test('item list requests only the projected fields by default', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS, priority: 'low' }], next_page_results: false } },
  ], { positionals: ['CYB'] });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.get('fields'), LIST_FIELDS.join(','));
});

test('item list with --full omits the fields projection', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'], values: { full: true } });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.has('fields'), false);
});

test('item list defaults to a limit of 30', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'] });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.get('per_page'), '30');
});

test('item list filters by state name, resolving it to a uuid', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 0, results: [], next_page_results: false } },
  ], { positionals: ['CYB'], values: { state: 'In Progress' } });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.get('state'), UUID_STATE_PROGRESS);
});

test('item list prints a truncation notice when results were withheld', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { total_count: 77, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'], mode: 'plain' });
  await list(ctx);
  assert.match(outText(), /more \(--limit/);
});

test('item list caches the sequence-to-uuid mapping it saw', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'item-uuid', sequence_id: 42, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'] });
  await list(ctx);
  assert.equal(ctx.cache.byProject[UUID_PROJECT].items[42], 'item-uuid');
});

test('item list --json emits a clean array on stdout and the truncation notice on stderr', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { total_count: 77, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'], mode: 'json' });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await list(ctx);

  const parsed = JSON.parse(outText());
  assert.ok(Array.isArray(parsed));
  assert.equal(parsed.length, 1);
  assert.match(stderrOut.join(''), /more \(--limit/);
});

test('item list --json leaves stderr empty when nothing was withheld', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'], mode: 'json' });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await list(ctx);

  assert.equal(JSON.parse(outText()).length, 1);
  assert.equal(stderrOut.join(''), '');
});

// Important 7: `list` used to send `per_page: limit` straight through,
// unclamped, so `--limit 250` sent per_page=250, got back only
// PAGE_CEILING (100) rows from the server, and the truncation notice then
// recommended `--limit 250` again — advice that can never succeed. Routing
// through paginate() means a --limit above the ceiling costs more requests
// but is actually reachable.
test('item list pages past the per-request ceiling to reach a --limit above it', async () => {
  const page = (n, cursor, hasNext) => ({
    status: 200,
    body: {
      total_count: 250,
      results: Array.from({ length: 100 }, (_, i) => ({
        id: `i${n}-${i}`, sequence_id: n * 100 + i, name: `x${n}-${i}`, state: UUID_STATE_PROGRESS,
      })),
      next_page_results: hasNext,
      next_cursor: hasNext ? cursor : undefined,
    },
  });
  const { ctx, calls, outText } = makeCtx([
    page(0, 'c1', true),
    page(1, 'c2', true),
    { status: 200, body: { total_count: 250, results: [{ id: 'i2-0', sequence_id: 200, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'], values: { limit: 250 } });

  await list(ctx);

  assert.equal(calls.length, 3, 'reached the requested limit by paging, not by one oversized request');
  for (const call of calls) {
    assert.ok(Number(new URL(call.url).searchParams.get('per_page')) <= 100, 'no single request exceeds the page ceiling');
  }
  assert.equal(JSON.parse(outText()).length, 201);
});

test('item list stamps itemsFetchedAt so the cache it writes is actually usable', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'item-uuid', sequence_id: 42, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'] });
  // Force the cold-cache state a real first run starts from — `projectBucket`
  // defaults `itemsFetchedAt` to null (cache.mjs) — rather than relying on
  // makeCtx's warmed stamp, which would make this indistinguishable from
  // "the stamp was already fresh and list() never touched it".
  ctx.cache.byProject[UUID_PROJECT].itemsFetchedAt = null;

  await list(ctx);
  assert.ok(ctx.cache.byProject[UUID_PROJECT].itemsFetchedAt, 'itemsFetchedAt must be stamped');

  const callsBeforeResolve = calls.length;
  const resolved = await ctx.resolver.item('CYB-42');
  assert.equal(calls.length, callsBeforeResolve, 'resolver.item should hit the cache, not the network');
  assert.equal(resolved.id, 'item-uuid');
});

test('item show resolves CYB-42 and fetches the full record', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42, name: 'Fix auth', state: UUID_STATE_PROGRESS } },
  ], { positionals: ['CYB-42'] });
  await show(ctx);
  assert.equal(JSON.parse(outText()).name, 'Fix auth');
});

test('item show <uuid> with --project resolves the project instead of building /projects/null/', async () => {
  const { ctx, calls, outText } = makeCtx([
    { status: 200, body: { id: RAW_ITEM_UUID, sequence_id: 42, name: 'Fix auth', state: UUID_STATE_PROGRESS } },
  ], { positionals: [RAW_ITEM_UUID], values: { project: 'CYB' } });

  await show(ctx);

  const path = new URL(calls[0].url).pathname;
  assert.equal(path, `/api/v1/workspaces/cybernetics/projects/${UUID_PROJECT}/issues/${RAW_ITEM_UUID}/`);
  assert.doesNotMatch(path, /projects\/null/);
  assert.equal(JSON.parse(outText()).name, 'Fix auth');
});

test('item show <uuid> with no project available fails with a clear hint, not a null-project request', async () => {
  const { ctx, calls } = makeCtx([], { positionals: [RAW_ITEM_UUID] });

  await assert.rejects(
    () => show(ctx),
    (err) => {
      assert.equal(err.code, EXIT.GENERAL);
      assert.match(err.message, /project/i);
      return true;
    },
  );
  assert.equal(calls.length, 0, 'must fail before sending any request');
});
