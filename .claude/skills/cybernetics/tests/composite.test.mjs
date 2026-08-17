import { test } from 'node:test';
import assert from 'node:assert/strict';
import { board, my, search, groupByState, MY_PROJECT_SCAN_CAP } from '../src/commands/composite.mjs';
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

test('board emits a truncation notice on stderr when the project has more items than one page', async () => {
  const { ctx, calls, outText } = makeCtx([
    {
      status: 200,
      body: {
        total_count: 5,
        results: [
          { id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_BACKLOG, priority: 'low' },
          { id: 'b', sequence_id: 2, name: 'y', state: UUID_STATE_PROGRESS, priority: 'high' },
        ],
        next_page_results: false,
      },
    },
  ], { positionals: ['CYB'] });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await board(ctx);

  assert.equal(calls.length, 1);
  const report = JSON.parse(outText());
  assert.equal(report.Backlog.length, 1);
  assert.match(stderrOut.join(''), /more \(--limit/);
});

test('my filters to items assigned to the current user', async () => {
  const { ctx, calls, outText } = makeCtx([
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
  // Pins the cost this command exists to guarantee: me + project list + one
  // issues request per project (here, 1 project) — never more.
  assert.equal(calls.length, 3);
});

test('my reports an empty result set without error', async () => {
  const { ctx, calls, outText } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ], { positionals: [], warmCache: false, mode: 'plain' });
  await my(ctx);
  assert.match(outText(), /no results|no work items/i);
  assert.equal(calls.length, 2);
});

test('my caps project fan-out at MY_PROJECT_SCAN_CAP and reports the skipped projects (sparse case)', async () => {
  // The sparse case is the one that actually stresses the budget: with no
  // matches ever found, `rows.length >= limit` never fires, so only a
  // project-count cap — not the row-count bailout — stops the fan-out.
  const totalProjects = MY_PROJECT_SCAN_CAP + 5;
  const projects = Array.from({ length: totalProjects }, (_, i) => ({
    id: `p${i}`, identifier: `P${i}`, name: `Proj ${i}`,
  }));
  const responses = [
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: totalProjects, results: projects } },
    ...Array.from({ length: MY_PROJECT_SCAN_CAP }, () => ({
      status: 200,
      body: { results: [], next_page_results: false },
    })),
  ];
  const { ctx, calls, outText } = makeCtx(responses, { positionals: [], warmCache: false });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await my(ctx);

  // 2 (me + project list) + the capped number of per-project issues
  // requests — never one per project in a 20-project workspace (52).
  assert.equal(calls.length, 2 + MY_PROJECT_SCAN_CAP);
  assert.equal(JSON.parse(outText()).length, 0);
  assert.match(stderrOut.join(''), /5 more projects not scanned/);
});

test('my stays silent about project count when the workspace is within the scan cap', async () => {
  const projects = Array.from({ length: 3 }, (_, i) => ({ id: `p${i}`, identifier: `P${i}`, name: `Proj ${i}` }));
  const responses = [
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 3, results: projects } },
    ...Array.from({ length: 3 }, () => ({ status: 200, body: { results: [], next_page_results: false } })),
  ];
  const { ctx, calls, outText } = makeCtx(responses, { positionals: [], warmCache: false });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await my(ctx);

  assert.equal(calls.length, 2 + 3);
  assert.equal(JSON.parse(outText()).length, 0);
  assert.equal(stderrOut.join(''), '');
});

test('search matches names case-insensitively', async () => {
  const { ctx, calls, outText } = makeCtx([
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
  // Pins the scan cost: one page fetch (cache warm), not one per item.
  assert.equal(calls.length, 1);
});

test('search requires a query', async () => {
  const { ctx, calls } = makeCtx([], { positionals: [] });
  await assert.rejects(() => search(ctx), (err) => /query/.test(err.message));
  assert.equal(calls.length, 0);
});

test('search stays silent when the project has exactly SEARCH_SCAN_CAP items', async () => {
  // A project whose true size is exactly the cap is fully scanned by the
  // 5th page (next_page_results: false) — the over-fetch-by-one request for
  // a 501st item is never issued, so `scanned` never exceeds the cap and
  // the cap notice, which would be false here, must not fire.
  const CAP = 500;
  const pageOf = (n, cursor, hasNext) => ({
    status: 200,
    body: {
      results: Array.from({ length: 100 }, (_, i) => ({
        id: `i${n}-${i}`, sequence_id: n * 100 + i, name: `unrelated item ${n}-${i}`, state: UUID_STATE_BACKLOG,
      })),
      next_page_results: hasNext,
      next_cursor: hasNext ? cursor : undefined,
    },
  });
  const responses = [
    pageOf(0, 'c1', true),
    pageOf(1, 'c2', true),
    pageOf(2, 'c3', true),
    pageOf(3, 'c4', true),
    pageOf(4, 'c5', false),
  ];
  const { ctx, calls, outText } = makeCtx(responses, { positionals: ['zzzznomatch'], values: { project: 'CYB' } });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await search(ctx);

  assert.equal(calls.length, 5);
  assert.equal(JSON.parse(outText()).length, 0);
  assert.equal(stderrOut.join(''), '');
});

test('search reports a notice when the scan cap is reached before the project is exhausted', async () => {
  // 501 items total: five full pages of 100, then a final page with just
  // the one item past the cap. The over-fetch-by-one request only happens
  // because there genuinely is more left unscanned, proving the "more
  // exist" case the cap notice is meant to distinguish from "exactly full".
  const CAP = 500;
  const pageOf = (n, cursor, hasNext) => ({
    status: 200,
    body: {
      results: Array.from({ length: 100 }, (_, i) => ({
        id: `i${n}-${i}`, sequence_id: n * 100 + i, name: `unrelated item ${n}-${i}`, state: UUID_STATE_BACKLOG,
      })),
      next_page_results: hasNext,
      next_cursor: hasNext ? cursor : undefined,
    },
  });
  const responses = [
    pageOf(0, 'c1', true),
    pageOf(1, 'c2', true),
    pageOf(2, 'c3', true),
    pageOf(3, 'c4', true),
    pageOf(4, 'c5', true),
    {
      status: 200,
      body: {
        results: [{ id: 'i5-0', sequence_id: 500, name: 'unrelated item 5-0', state: UUID_STATE_BACKLOG }],
        next_page_results: false,
      },
    },
  ];
  const { ctx, calls, outText } = makeCtx(responses, { positionals: ['zzzznomatch'], values: { project: 'CYB' } });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await search(ctx);

  assert.equal(calls.length, 6);
  assert.equal(JSON.parse(outText()).length, 0);
  assert.match(stderrOut.join(''), new RegExp(`scan cap of ${CAP}`));
});

test('search stays silent when the project is fully scanned within the cap', async () => {
  const { ctx, calls, outText } = makeCtx([
    {
      status: 200,
      body: {
        results: Array.from({ length: 10 }, (_, i) => ({
          id: `i${i}`, sequence_id: i, name: `unrelated item ${i}`, state: UUID_STATE_BACKLOG,
        })),
        next_page_results: false,
      },
    },
  ], { positionals: ['zzzznomatch'], values: { project: 'CYB' } });
  const stderrOut = [];
  ctx.streams.stderr.write = (s) => stderrOut.push(s);

  await search(ctx);

  assert.equal(calls.length, 1);
  assert.equal(JSON.parse(outText()).length, 0);
  assert.equal(stderrOut.join(''), '');
});
