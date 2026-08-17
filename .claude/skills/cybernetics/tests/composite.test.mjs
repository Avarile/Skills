import { test } from 'node:test';
import assert from 'node:assert/strict';
import { board, my, search, groupByState } from '../src/commands/composite.mjs';
import { makeCtx, STATE_LIST, UUID_STATE_PROGRESS, UUID_STATE_BACKLOG } from './helpers/ctx.mjs';

test('groupByState buckets rows under their state group in canonical order', () => {
  const grouped = groupByState(
    [
      { ref: 'CYB-1', state: UUID_STATE_PROGRESS },
      { ref: 'CYB-2', state: UUID_STATE_BACKLOG },
      { ref: 'CYB-3', state: UUID_STATE_BACKLOG },
    ],
    STATE_LIST,
  );
  assert.deepEqual(Object.keys(grouped), ['Backlog', 'In Progress', 'Done']);
  assert.equal(grouped.Backlog.length, 2);
  assert.equal(grouped['In Progress'].length, 1);
  assert.equal(grouped.Done.length, 0);
});

test('board fetches once and emits grouped counts', async () => {
  const { ctx, calls, outText } = makeCtx([
    {
      status: 200,
      body: {
        total_count: 2,
        results: [
          { id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_BACKLOG, priority: 'low' },
          { id: 'b', sequence_id: 2, name: 'y', state: UUID_STATE_PROGRESS, priority: 'high' },
        ],
        next_page_results: false,
      },
    },
  ], { positionals: ['CYB'] });
  await board(ctx);
  assert.equal(calls.length, 1);
  const report = JSON.parse(outText());
  assert.equal(report.Backlog.length, 1);
  assert.equal(report['In Progress'].length, 1);
});

test('my filters to items assigned to the current user', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 1, results: [{ id: 'p1', identifier: 'CYB', name: 'Core' }] } },
    {
      status: 200,
      body: {
        results: [
          { id: 'a', sequence_id: 1, name: 'mine', state: UUID_STATE_BACKLOG, assignees: ['me-uuid'] },
          { id: 'b', sequence_id: 2, name: 'theirs', state: UUID_STATE_BACKLOG, assignees: ['other'] },
        ],
        next_page_results: false,
      },
    },
  ], { positionals: [], warmCache: false });
  await my(ctx);
  const rows = JSON.parse(outText());
  assert.equal(rows.length, 1);
  assert.equal(rows[0].name, 'mine');
});

test('my reports an empty result set without error', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ], { positionals: [], warmCache: false, mode: 'plain' });
  await my(ctx);
  assert.match(outText(), /no results|no work items/i);
});

test('search matches names case-insensitively', async () => {
  const { ctx, outText } = makeCtx([
    {
      status: 200,
      body: {
        results: [
          { id: 'a', sequence_id: 1, name: 'Fix AUTH timeout', state: UUID_STATE_BACKLOG },
          { id: 'b', sequence_id: 2, name: 'Update docs', state: UUID_STATE_BACKLOG },
        ],
        next_page_results: false,
      },
    },
  ], { positionals: ['auth'], values: { project: 'CYB' } });
  await search(ctx);
  const rows = JSON.parse(outText());
  assert.equal(rows.length, 1);
  assert.match(rows[0].name, /Fix AUTH/);
});

test('search requires a query', async () => {
  const { ctx } = makeCtx([], { positionals: [] });
  await assert.rejects(() => search(ctx), (err) => /query/.test(err.message));
});
