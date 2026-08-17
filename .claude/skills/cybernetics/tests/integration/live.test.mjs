import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { main } from '../../src/cli.mjs';

const ENABLED = Boolean(process.env.CYB_TOKEN) && process.env.CYB_RUN_INTEGRATION === '1';
const IDENTIFIER = 'ZZITEST';

const scratch = mkdtempSync(join(tmpdir(), 'cyb-int-'));
const deps = () => ({
  env: { CYB_TOKEN: process.env.CYB_TOKEN },
  cwd: scratch,
  configPath: join(scratch, 'config.json'),
  cachePath: join(scratch, 'cache.json'),
});

function capture() {
  const out = [];
  const err = [];
  return {
    stdout: { write: (s) => out.push(s), isTTY: false },
    stderr: { write: (s) => err.push(s) },
    outText: () => out.join(''),
    errText: () => err.join(''),
  };
}

async function run(argv) {
  const streams = capture();
  const code = await main([...argv, '--json'], { ...deps(), streams });
  return { code, out: streams.outText(), err: streams.errText() };
}

async function cleanup() {
  await run(['project', 'delete', IDENTIFIER, '--yes']).catch(() => {});
}

before(async () => {
  if (!ENABLED) return;
  await cleanup();
});

after(async () => {
  if (!ENABLED) return;
  await cleanup();
});

test('doctor authenticates against the live instance', { skip: !ENABLED }, async () => {
  const { code, out } = await run(['doctor']);
  assert.equal(code, 0);
  const report = JSON.parse(out);
  assert.equal(report.workspace, 'cybernetics');
  assert.ok(report.user.id);
  assert.match(report.token, /^plane_api_…/);
});

test('full work item lifecycle against the live instance', { skip: !ENABLED }, async () => {
  try {
    const created = await run(['project', 'create', '--name', 'ZZ Integration Test', '--identifier', IDENTIFIER]);
    assert.equal(created.code, 0);
    assert.ok(JSON.parse(created.out).id);

    const states = await run(['state', 'list', IDENTIFIER]);
    assert.equal(states.code, 0);
    const stateNames = JSON.parse(states.out).map((s) => s.name);
    assert.ok(stateNames.includes('In Progress'), `expected default states, got ${stateNames}`);

    const item = await run(['item', 'create', IDENTIFIER, '--name', 'Integration item', '--priority', 'high']);
    assert.equal(item.code, 0);
    const ref = `${IDENTIFIER}-${JSON.parse(item.out).sequence_id}`;

    const listed = await run(['item', 'list', IDENTIFIER]);
    assert.equal(listed.code, 0);
    assert.ok(JSON.parse(listed.out).some((r) => r.ref === ref));

    const moved = await run(['item', 'move', ref, 'In Progress']);
    assert.equal(moved.code, 0);

    const shown = await run(['item', 'show', ref]);
    assert.equal(JSON.parse(shown.out).priority, 'high');

    const commented = await run(['comment', 'add', ref, 'integration comment']);
    assert.equal(commented.code, 0);

    const comments = await run(['comment', 'list', ref]);
    assert.ok(JSON.parse(comments.out).some((c) => /integration comment/.test(c.text)));

    const board = await run(['board', IDENTIFIER]);
    assert.equal(board.code, 0);
    assert.ok(JSON.parse(board.out)['In Progress'].some((r) => r.ref === ref));

    const refused = await run(['item', 'delete', ref]);
    assert.equal(refused.code, 2, 'delete without --yes must be refused');
    assert.equal(JSON.parse(refused.err).error.code, 2);

    const deleted = await run(['item', 'delete', ref, '--yes']);
    assert.equal(deleted.code, 0);
  } finally {
    await cleanup();
  }
});

test('an unresolvable state name fails with exit 3 and lists valid states', { skip: !ENABLED }, async () => {
  try {
    await run(['project', 'create', '--name', 'ZZ Integration Test', '--identifier', IDENTIFIER]);
    const bad = await run(['item', 'create', IDENTIFIER, '--name', 'x', '--state', 'Nonexistent']);
    assert.equal(bad.code, 3);
    assert.match(JSON.parse(bad.err).error.hint, /Backlog|In Progress/);
  } finally {
    await cleanup();
  }
});

test('an invalid priority is rejected locally with exit 1', { skip: !ENABLED }, async () => {
  const bad = await run(['item', 'create', 'ANY', '--name', 'x', '--priority', 'critical']);
  assert.equal(bad.code, 1);
  assert.match(JSON.parse(bad.err).error.message, /invalid priority/);
});
