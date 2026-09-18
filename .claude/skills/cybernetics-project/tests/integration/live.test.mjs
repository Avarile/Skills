import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { main } from '../../src/cli.mjs';
import { EXIT } from '../../src/errors.mjs';
import { captureStreams } from '../helpers/capture-streams.mjs';

const ENABLED = Boolean(process.env.CYB_TOKEN) && process.env.CYB_RUN_INTEGRATION === '1';
const IDENTIFIER = 'ZZITEST';

// Only created when the live suite can actually run: an offline run (the
// common case, including CI without CYB_TOKEN) must not touch the real
// filesystem at all.
const scratch = ENABLED ? mkdtempSync(join(tmpdir(), 'cyb-int-')) : null;
const deps = () => ({
  env: { CYB_TOKEN: process.env.CYB_TOKEN },
  cwd: scratch,
  configPath: join(scratch, 'config.json'),
  cachePath: join(scratch, 'cache.json'),
});

async function run(argv) {
  const streams = captureStreams();
  const code = await main([...argv, '--json'], { ...deps(), streams });
  return { code, out: streams.outText(), err: streams.errText() };
}

// main() always resolves to an exit code (it never rejects), so cleanup()
// can't swallow a failure by accident here. What it must not swallow is a
// *non-zero* exit: a delete that failed for a real reason (429, 500, auth)
// still leaves the scratch project on the live workspace, and the tests
// would report PASS regardless. 0 (deleted) and 3 (not found, i.e. already
// gone) are the only acceptable outcomes; anything else gets surfaced.
async function cleanup() {
  const { code, err } = await run(['project', 'delete', IDENTIFIER, '--yes']);
  if (code !== EXIT.OK && code !== EXIT.NOT_FOUND) {
    console.error(
      `[live.test] WARNING: cleanup of scratch project ${IDENTIFIER} exited with code ${code} ` +
        `(expected ${EXIT.OK} or ${EXIT.NOT_FOUND}); it may still exist on the live workspace. stderr: ${err}`,
    );
  }
}

before(async () => {
  if (!ENABLED) return;
  await cleanup();
});

after(async () => {
  if (!ENABLED) return;
  await cleanup();
  rmSync(scratch, { recursive: true, force: true });
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
    const created = await run(['project', 'create', '--name', 'ZZ Integration Test', '--identifier', IDENTIFIER]);
    assert.equal(created.code, 0);
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
