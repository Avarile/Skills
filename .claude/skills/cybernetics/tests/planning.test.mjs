import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  cycleList, cycleCreate, cycleAddItem, cycleRemove,
  moduleList, moduleCreate, moduleAddItem, moduleRemove,
} from '../src/commands/planning.mjs';
import { makeCtx, UUID_PROJECT } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

const RAW_ITEM_UUID = '7c9cd656-c9cf-4622-9d2a-b44ad1766113';

test('cycle list emits cycles', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1', start_date: '2026-08-01', end_date: '2026-08-14' }] } },
  ], { positionals: ['CYB'] });
  await cycleList(ctx);
  assert.equal(JSON.parse(outText())[0].name, 'Sprint 1');
});

test('cycle create posts name with start and end dates', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'c1', name: 'Sprint 1' } },
  ], { positionals: ['CYB'], values: { name: 'Sprint 1', start: '2026-08-01', end: '2026-08-14' } });
  await cycleCreate(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.name, 'Sprint 1');
  assert.equal(body.start_date, '2026-08-01');
  assert.equal(body.end_date, '2026-08-14');
});

test('cycle create requires --name', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB'], values: {}, warmCache: false });
  await assert.rejects(() => cycleCreate(ctx), (err) => /--name/.test(err.hint));
  assert.equal(calls.length, 0);
});

test('cycle add-item posts the issue uuid to cycle-issues', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1' }] } },
    { status: 201, body: {} },
  ], { positionals: ['CYB-42'], values: { cycle: 'Sprint 1' } });
  await cycleAddItem(ctx);
  const post = calls.at(-1);
  assert.match(post.url, /cycle-issues/);
  assert.deepEqual(JSON.parse(post.init.body), { issues: ['item-uuid'] });
});

test('cycle add-item requires --cycle', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB-42'], values: {} });
  await assert.rejects(() => cycleAddItem(ctx), (err) => /--cycle/.test(err.hint));
});

test('cycle add-item reports an unknown cycle by name', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1' }] } },
  ], { positionals: ['CYB-42'], values: { cycle: 'Sprint 9' } });
  await assert.rejects(() => cycleAddItem(ctx), (err) => err.code === EXIT.NOT_FOUND);
});

// Important 3: cycleAddItem read `item.projectId` directly, which is null
// for a raw UUID ref (resolver.item() can't know the project without an
// extra request), building a request path containing the literal "null".
// Must fall back to --project via item.mjs's resolveItemProjectId.
test('cycle add-item <uuid> with --project resolves the project instead of building /projects/null/', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1' }] } },
    { status: 201, body: {} },
  ], { positionals: [RAW_ITEM_UUID], values: { cycle: 'Sprint 1', project: 'CYB' } });

  await cycleAddItem(ctx);

  for (const call of calls) {
    assert.doesNotMatch(new URL(call.url).pathname, /projects\/null/);
  }
  assert.match(calls.at(-1).url, new RegExp(`projects/${UUID_PROJECT}/cycles/c1/cycle-issues`));
});

test('cycle delete without --yes refuses', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1' }] } },
  ], { positionals: ['CYB', 'Sprint 1'] });
  await assert.rejects(() => cycleRemove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});

test('module list emits modules', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', name: 'Auth' }] } },
  ], { positionals: ['CYB'] });
  await moduleList(ctx);
  assert.equal(JSON.parse(outText())[0].name, 'Auth');
});

test('module create posts a name', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'm1', name: 'Auth' } },
  ], { positionals: ['CYB'], values: { name: 'Auth' } });
  await moduleCreate(ctx);
  assert.equal(JSON.parse(calls.at(-1).init.body).name, 'Auth');
});

test('module create requires --name', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB'], values: {}, warmCache: false });
  await assert.rejects(() => moduleCreate(ctx), (err) => /--name/.test(err.hint));
  assert.equal(calls.length, 0);
});

test('module add-item posts to module-issues', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'm1', name: 'Auth' }] } },
    { status: 201, body: {} },
  ], { positionals: ['CYB-42'], values: { module: 'Auth' } });
  await moduleAddItem(ctx);
  const post = calls.at(-1);
  assert.match(post.url, /module-issues/);
  assert.deepEqual(JSON.parse(post.init.body), { issues: ['item-uuid'] });
});

test('module add-item <uuid> with --project resolves the project instead of building /projects/null/', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', name: 'Auth' }] } },
    { status: 201, body: {} },
  ], { positionals: [RAW_ITEM_UUID], values: { module: 'Auth', project: 'CYB' } });

  await moduleAddItem(ctx);

  for (const call of calls) {
    assert.doesNotMatch(new URL(call.url).pathname, /projects\/null/);
  }
  assert.match(calls.at(-1).url, new RegExp(`projects/${UUID_PROJECT}/modules/m1/module-issues`));
});

test('module delete without --yes refuses and issues no DELETE', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', name: 'Auth' }] } },
  ], { positionals: ['CYB', 'Auth'] });
  await assert.rejects(() => moduleRemove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});
