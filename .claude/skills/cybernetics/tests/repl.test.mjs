import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Readable } from 'node:stream';
import { tokenize, translate, makeCompleter, REPL_HELP, startRepl } from '../src/repl.mjs';
import { emptyCache, loadCache } from '../src/cache.mjs';
import { main } from '../src/cli.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';

test('tokenize splits on whitespace', () => {
  assert.deepEqual(tokenize('ls --state todo'), ['ls', '--state', 'todo']);
});

test('tokenize keeps double-quoted phrases together', () => {
  assert.deepEqual(tokenize('mv 42 "In Progress"'), ['mv', '42', 'In Progress']);
});

test('tokenize keeps single-quoted phrases together', () => {
  assert.deepEqual(tokenize("new 'Fix the auth bug'"), ['new', 'Fix the auth bug']);
});

test('tokenize collapses repeated whitespace and trims', () => {
  assert.deepEqual(tokenize('  ls   --json  '), ['ls', '--json']);
});

test('tokenize returns an empty array for a blank line', () => {
  assert.deepEqual(tokenize('   '), []);
});

test('ls translates to item list for the current project', () => {
  assert.deepEqual(translate(['ls'], { project: 'CYB' }), { argv: ['item', 'list', 'CYB'] });
});

test('ls passes trailing flags through', () => {
  assert.deepEqual(translate(['ls', '--state', 'todo'], { project: 'CYB' }), {
    argv: ['item', 'list', 'CYB', '--state', 'todo'],
  });
});

test('open builds a CYB-42 reference', () => {
  assert.deepEqual(translate(['open', '42'], { project: 'CYB' }), {
    argv: ['item', 'show', 'CYB-42'],
  });
});

test('open accepts a full reference unchanged', () => {
  assert.deepEqual(translate(['open', 'OTHER-7'], { project: 'CYB' }), {
    argv: ['item', 'show', 'OTHER-7'],
  });
});

test('mv translates to item move', () => {
  assert.deepEqual(translate(['mv', '42', 'In Progress'], { project: 'CYB' }), {
    argv: ['item', 'move', 'CYB-42', 'In Progress'],
  });
});

test('new translates to item create with --name', () => {
  assert.deepEqual(translate(['new', 'Fix auth'], { project: 'CYB' }), {
    argv: ['item', 'create', 'CYB', '--name', 'Fix auth'],
  });
});

test('assign translates to item assign', () => {
  assert.deepEqual(translate(['assign', '42', 'avarile'], { project: 'CYB' }), {
    argv: ['item', 'assign', 'CYB-42', 'avarile'],
  });
});

test('board translates to the board command', () => {
  assert.deepEqual(translate(['board'], { project: 'CYB' }), { argv: ['board', 'CYB'] });
});

test('cd requests a project change without an argv', () => {
  assert.deepEqual(translate(['cd', 'OTHER'], { project: 'CYB' }), { setProject: 'OTHER' });
});

test('exit and quit both end the session', () => {
  assert.deepEqual(translate(['exit'], { project: 'CYB' }), { exit: true });
  assert.deepEqual(translate(['quit'], { project: 'CYB' }), { exit: true });
});

test('help returns the help marker', () => {
  assert.deepEqual(translate(['help'], { project: 'CYB' }), { help: true });
});

test('an unknown verb returns a descriptive error', () => {
  const result = translate(['frobnicate'], { project: 'CYB' });
  assert.match(result.error, /unknown command: frobnicate/);
});

test('a command needing a project errors when none is selected', () => {
  const result = translate(['ls'], { project: null });
  assert.match(result.error, /no project selected/);
});

test('open without an argument errors', () => {
  assert.match(translate(['open'], { project: 'CYB' }).error, /needs a work item/);
});

test('REPL_HELP documents every supported verb', () => {
  for (const verb of ['ls', 'open', 'new', 'mv', 'assign', 'cd', 'board', 'help', 'exit']) {
    assert.match(REPL_HELP, new RegExp(`\\b${verb}\\b`));
  }
});

test('completer suggests verbs at the start of a line', () => {
  const [hits] = makeCompleter({ project: 'CYB' }, emptyCache('cybernetics'))('bo');
  assert.ok(hits.includes('board'));
});

test('completer suggests state names from the cache after mv', () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: 'p1', name: 'Core', fetchedAt: new Date().toISOString() };
  cache.byProject.p1 = {
    states: { backlog: 's1', 'in progress': 's2' },
    stateList: [{ id: 's1', name: 'Backlog', group: 'backlog' }, { id: 's2', name: 'In Progress', group: 'started' }],
    labels: {}, members: {}, items: {}, statesFetchedAt: new Date().toISOString(),
  };
  const [hits] = makeCompleter({ project: 'CYB' }, cache)('mv 42 In');
  assert.ok(hits.some((h) => /In Progress/.test(h)));
});

test('completer returns no hits rather than throwing on a cold cache', () => {
  const [hits] = makeCompleter({ project: 'CYB' }, emptyCache('cybernetics'))('mv 42 In');
  assert.deepEqual(hits, []);
});

// --- Task 16 pre-work guarantees, exercised end-to-end through startRepl --
//
// The three tests below aren't in the brief's minimum set, but they pin the
// exact behaviour the "required pre-work" section called out as easy to get
// wrong: a session-lifetime Client (not a fresh one per line), cd's warm-up
// ruling (labels/items, not a sync-wide tax), and main()'s `ui` wiring.

test('startRepl reuses one Client across lines, so rate-limit budget state carries over', async () => {
  // Deliberately not black-box on output — the point being verified is
  // internal state (Client#remaining) that only manifests as a side effect
  // (whether the pre-request rate-limit gate's sleep fires). If startRepl
  // built a fresh Client per line the way a naive `main()`-per-line REPL
  // would, `remaining` would reset to null between lines and this gate
  // could never fire on the second line's very first (and only) request.
  const base = mkdtempSync(join(tmpdir(), 'cyb-repl-client-test-'));
  try {
    const { fetchImpl, calls } = makeFakeFetch([
      { status: 200, body: { results: [{ id: 'p1', identifier: 'CYB', name: 'Core' }] } }, // resolver.project (cold)
      { status: 200, body: { results: [] } }, // resolver.statesFor (cold)
      { status: 200, body: { results: [] }, headers: { 'x-ratelimit-remaining': '4' } }, // board's own fetch, line 1
      { status: 200, body: { results: [] } }, // board's own fetch, line 2 — project/states now cached, no extra requests
    ]);
    let sleepCalls = 0;
    // `board` (bare — no positional) is the REPL verb; the project comes
    // from `state.project`, seeded below via CYB_PROJECT so this test can
    // exercise two `board` lines without an intervening `cd` (which has its
    // own request cost, exercised separately below) muddying the count.
    const input = Readable.from(['board\n', 'board\n', 'exit\n']);
    const output = { write: () => {}, isTTY: false };

    const code = await startRepl({
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef', CYB_PROJECT: 'CYB' },
      cwd: base,
      configPath: join(base, 'config.json'),
      cachePath: join(base, 'cache.json'),
      fetchImpl,
      sleep: async () => { sleepCalls++; },
      input,
      output,
      streams: { stdout: output, stderr: output },
    });

    assert.equal(code, 0);
    assert.equal(calls.length, 4);
    assert.equal(sleepCalls, 1);
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});

test("cd warms the target project's labels and items (controller ruling: cd's job, not sync's)", async () => {
  const base = mkdtempSync(join(tmpdir(), 'cyb-repl-cd-test-'));
  try {
    const cachePath = join(base, 'cache.json');
    const { fetchImpl } = makeFakeFetch([
      { status: 200, body: { results: [{ id: 'p1', identifier: 'CYB', name: 'Core' }] } }, // resolver.project
      { status: 200, body: { results: [{ id: 'l1', name: 'bug' }] } }, // labels warm-up
      { status: 200, body: { results: [{ id: 'i1', sequence_id: 42 }] } }, // items warm-up
    ]);
    const input = Readable.from(['cd CYB\n', 'exit\n']);
    const output = { write: () => {}, isTTY: false };

    const code = await startRepl({
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
      cwd: base,
      configPath: join(base, 'config.json'),
      cachePath,
      fetchImpl,
      sleep: async () => {},
      input,
      output,
      streams: { stdout: output, stderr: output },
    });

    assert.equal(code, 0);
    const cache = loadCache({ path: cachePath, workspace: 'cybernetics' });
    const bucket = cache.byProject.p1;
    assert.ok(bucket, 'expected the CYB project bucket to exist after cd');
    assert.equal(bucket.labels.bug, 'l1');
    assert.equal(bucket.items[42], 'i1');
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});

test('cd leaves the current project unchanged when the target project does not exist', async () => {
  const base = mkdtempSync(join(tmpdir(), 'cyb-repl-cd-missing-test-'));
  try {
    const { fetchImpl, calls } = makeFakeFetch([
      { status: 200, body: { results: [] } }, // resolver.project('NOPE') — no match
      { status: 200, body: { results: [{ id: 'p1', identifier: 'CYB', name: 'Core' }] } }, // resolver.project('CYB'), for `board`
      { status: 200, body: { results: [] } }, // resolver.statesFor
      { status: 200, body: { results: [] } }, // board's own fetch
    ]);
    // `board` (bare) only reaches all 3 of its own requests if state.project
    // is still the seeded 'CYB' — if `cd NOPE`'s failure had cleared or
    // corrupted state.project, `board` would fail closed on "no project
    // selected" without ever calling fetchImpl a second, third or fourth
    // time.
    const input = Readable.from(['cd NOPE\n', 'board\n', 'exit\n']);
    const written = [];
    const output = { write: (s) => written.push(s), isTTY: false };

    const code = await startRepl({
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef', CYB_PROJECT: 'CYB' },
      cwd: base,
      configPath: join(base, 'config.json'),
      cachePath: join(base, 'cache.json'),
      fetchImpl,
      sleep: async () => {},
      input,
      output,
      streams: { stdout: output, stderr: output },
    });

    assert.equal(code, 0);
    assert.match(written.join(''), /no such project: NOPE/);
    assert.doesNotMatch(written.join(''), /no project selected/);
    assert.equal(calls.length, 4);
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});

test('cyb ui launches the interactive REPL via main()', async () => {
  const base = mkdtempSync(join(tmpdir(), 'cyb-ui-test-'));
  try {
    const input = Readable.from([]); // ends immediately: no lines typed
    const output = { write: () => {}, isTTY: false };

    const code = await main(['ui'], {
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
      cwd: base,
      configPath: join(base, 'config.json'),
      cachePath: join(base, 'cache.json'),
      input,
      output,
      streams: { stdout: output, stderr: output },
    });

    assert.equal(code, 0);
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});
