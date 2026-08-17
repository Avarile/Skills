import { test } from 'node:test';
import assert from 'node:assert/strict';
import { list, show, decorate, ITEM_COLUMNS, LIST_FIELDS } from '../src/commands/item.mjs';
import { makeCtx, STATE_LIST, UUID_STATE_PROGRESS, UUID_PROJECT } from './helpers/ctx.mjs';

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

test('item show resolves CYB-42 and fetches the full record', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42, name: 'Fix auth', state: UUID_STATE_PROGRESS } },
  ], { positionals: ['CYB-42'] });
  await show(ctx);
  assert.equal(JSON.parse(outText()).name, 'Fix auth');
});
