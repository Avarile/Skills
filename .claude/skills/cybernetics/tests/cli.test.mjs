import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, chmodSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { main, buildContext, parseInvocation, dispatch, GLOBAL_OPTIONS, renderHelp, REGISTRY } from '../src/cli.mjs';
import { EXIT } from '../src/errors.mjs';
import { captureStreams } from './helpers/capture-streams.mjs';

test('GLOBAL_OPTIONS declares every documented global flag', () => {
  for (const flag of ['json', 'full', 'limit', 'yes', 'project', 'no-cache', 'verbose', 'help']) {
    assert.ok(GLOBAL_OPTIONS[flag], `missing global flag: ${flag}`);
  }
});

test('no arguments prints top-level help and exits 0', async () => {
  const s = captureStreams();
  const code = await main([], { streams: s, env: {} });
  assert.equal(code, EXIT.OK);
  assert.match(s.outText(), /Usage: cyb/);
});

test('an unknown group exits with the general error code', async () => {
  const s = captureStreams();
  const code = await main(['nonsense'], { streams: s, env: {} });
  assert.equal(code, EXIT.GENERAL);
  assert.match(s.errText(), /unknown command group: nonsense/);
});

test('an unknown action names the valid actions for that group', async () => {
  const s = captureStreams();
  const code = await main(['doctor', 'bogus'], { streams: s, env: {} });
  assert.equal(code, EXIT.GENERAL);
  assert.match(s.errText(), /unknown action/);
});

test('--help on a group prints that group help without running it', async () => {
  const s = captureStreams();
  const code = await main(['doctor', '--help'], { streams: s, env: {} });
  assert.equal(code, EXIT.OK);
  assert.match(s.outText(), /doctor/);
});

test('a missing token exits with the auth code before any request', async () => {
  const s = captureStreams();
  const code = await main(['doctor'], {
    streams: s,
    env: {},
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
  });
  assert.equal(code, EXIT.AUTH);
  assert.match(s.errText(), /no API token/i);
});

test('errors are emitted as JSON on stderr under --json', async () => {
  const s = captureStreams();
  await main(['doctor', '--json'], {
    streams: s,
    env: {},
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
  });
  const parsed = JSON.parse(s.errText());
  assert.equal(parsed.error.code, EXIT.AUTH);
});

test('renderHelp lists every registered group', () => {
  const help = renderHelp();
  for (const group of Object.keys(REGISTRY)) assert.match(help, new RegExp(group));
});

test('--json=true still produces a parseable JSON error envelope', async () => {
  const s = captureStreams();
  const code = await main(['doctor', '--json=true'], { streams: s, env: {} });
  assert.notEqual(code, EXIT.OK);
  const parsed = JSON.parse(s.errText());
  assert.ok(parsed.error);
});

test('cyb doctor --help lists the --probe option', async () => {
  const s = captureStreams();
  const code = await main(['doctor', '--help'], { streams: s, env: {} });
  assert.equal(code, EXIT.OK);
  assert.match(s.outText(), /--probe/);
});

test('board dispatches its positional through __default instead of treating it as an unknown action', async () => {
  // board/search take a real leading positional (project ref / search
  // query) that is never a subcommand name — unlike doctor, whose __default
  // takes no positional args at all. Confirms the `takesPositional` opt-in
  // in cli.mjs's REGISTRY actually reaches the handler rather than being
  // misread as `cyb board CYB` attempting an unknown action named "CYB".
  const s = captureStreams();
  const code = await main(['board', 'CYB'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl: async () => { throw new Error('sentinel: reached the network layer'); },
  });
  assert.notEqual(code, EXIT.OK);
  assert.doesNotMatch(s.errText(), /unknown action/);
  assert.match(s.errText(), /sentinel: reached the network layer/);
});

test('search dispatches its query positional through __default instead of treating it as an unknown action', async () => {
  const s = captureStreams();
  const code = await main(['search', 'auth', '--project', 'CYB'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl: async () => { throw new Error('sentinel: reached the network layer'); },
  });
  assert.notEqual(code, EXIT.OK);
  assert.doesNotMatch(s.errText(), /unknown action/);
  assert.match(s.errText(), /sentinel: reached the network layer/);
});

test('my still rejects an unknown action rather than silently treating it as positional data', async () => {
  // my's __default has no `takesPositional` — it takes no positional
  // grammar at all, so a stray bare word after it should behave like
  // doctor's "unknown action", not be swallowed as data.
  const s = captureStreams();
  const code = await main(['my', 'bogus'], { streams: s, env: {} });
  assert.equal(code, EXIT.GENERAL);
  assert.match(s.errText(), /unknown action/);
});

test('a group invoked with no action token gives a clear error, not a literal undefined', async () => {
  const s = captureStreams();
  REGISTRY.__no_default_test__ = {
    list: { summary: 'list things', handler: async () => {} },
  };
  try {
    const code = await main(['__no_default_test__'], { streams: s, env: {} });
    assert.equal(code, EXIT.GENERAL);
    assert.match(s.errText(), /no action specified/);
    assert.doesNotMatch(s.errText(), /undefined/);
  } finally {
    delete REGISTRY.__no_default_test__;
  }
});

test('save() swallows a recognised filesystem error from an unwritable cache location', (t) => {
  // Root ignores directory mode bits, so chmod 0500 would not actually make
  // the directory unwritable — mkdirSync/writeFileSync would succeed, and
  // the "note:" assertion below would fail. Root is the default user in
  // most CI images, so this must be skipped rather than assumed away.
  if (process.getuid?.() === 0) {
    t.skip('root ignores directory mode bits');
    return;
  }
  const base = mkdtempSync(join(tmpdir(), 'cyb-cli-test-'));
  chmodSync(base, 0o500);
  const s = captureStreams();
  try {
    const ctx = buildContext({
      values: { verbose: true },
      positionals: [],
      deps: {
        streams: s,
        env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
        cwd: '/nonexistent-cyb-dir',
        configPath: '/nonexistent-cyb-dir/config.json',
        cachePath: join(base, 'nested', 'cache.json'),
      },
    });
    assert.doesNotThrow(() => ctx.save());
    assert.match(s.errText(), /note:/);
  } finally {
    chmodSync(base, 0o700);
    rmSync(base, { recursive: true, force: true });
  }
});

test('a request timeout exits 1, and the envelope code matches the exit code', async (t) => {
  const base = mkdtempSync(join(tmpdir(), 'cyb-cli-test-timeout-'));
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const s = captureStreams();
  // Never resolves on its own — only rejects once the real (mocked)
  // AbortController timer fires and aborts the signal, exactly like a slow
  // or unreachable instance would behave under the 30s default timeout.
  const fetchImpl = (url, init) => new Promise((resolve, reject) => {
    init.signal.addEventListener('abort', () => {
      reject(new DOMException('This operation was aborted', 'AbortError'));
    });
  });
  try {
    const pending = main(['doctor', '--json'], {
      streams: s,
      env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
      cwd: base,
      configPath: join(base, 'config.json'),
      cachePath: join(base, 'cache.json'),
      fetchImpl,
    });
    t.mock.timers.tick(30_000);
    const code = await pending;
    assert.equal(code, 1);
    const envelope = JSON.parse(s.errText());
    assert.equal(envelope.error.code, code);
    assert.match(envelope.error.message, /timed out/);
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});

// --- dispatch seam (Task 16 pre-work) -------------------------------------
//
// main() used to parse argv, build a context, and dispatch in one function.
// A REPL calling main() once per typed line would reload config.json and
// cache.json and rebuild Client/Resolver on every line, discarding the very
// rate-limit state (Client#remaining/#resetAt) a session needs to track
// across commands. These tests pin the new seam — parseInvocation() does
// pure argv -> invocation translation (including every error/help path
// main() used to own), dispatch() just runs a resolved invocation against a
// caller-supplied ctx, and main() becomes parseInvocation -> buildContext ->
// dispatch with no behaviour of its own. The rest of this file (unchanged)
// is what proves main()'s external behaviour didn't move.

test('parseInvocation resolves a normal command to its REGISTRY definition, values and positionals', () => {
  const invocation = parseInvocation(['item', 'list', 'CYB', '--state', 'todo']);
  assert.equal(invocation.group, 'item');
  assert.equal(invocation.action, 'list');
  assert.equal(invocation.definition, REGISTRY.item.list);
  assert.equal(invocation.values.state, 'todo');
  assert.deepEqual(invocation.positionals, ['CYB']);
});

test('parseInvocation resolves a __default action that takes a leading positional', () => {
  const invocation = parseInvocation(['board', 'CYB']);
  assert.equal(invocation.group, 'board');
  assert.equal(invocation.action, '__default');
  assert.equal(invocation.definition, REGISTRY.board.__default);
  assert.deepEqual(invocation.positionals, ['CYB']);
});

test('parseInvocation reports no-group and top-level --help alike as a help invocation', () => {
  assert.deepEqual(parseInvocation([]), { help: true, group: null, action: null });
  assert.deepEqual(parseInvocation(['--help']), { help: true, group: null, action: null });
  assert.deepEqual(parseInvocation(['help']), { help: true, group: null, action: null });
});

test('parseInvocation reports a group/action --help as a help invocation naming that group and action', () => {
  const invocation = parseInvocation(['doctor', '--help']);
  assert.deepEqual(invocation, { help: true, group: 'doctor', action: '__default' });
});

test('parseInvocation throws the same CybErrors main() used to throw directly', () => {
  assert.throws(() => parseInvocation(['nonsense']), /unknown command group: nonsense/);
  assert.throws(() => parseInvocation(['doctor', 'bogus']), /unknown action/);
  assert.throws(() => parseInvocation(['my', 'bogus']), /unknown action/);
  REGISTRY.__no_default_test__ = { list: { summary: 'list things', handler: async () => {} } };
  try {
    assert.throws(() => parseInvocation(['__no_default_test__']), /no action specified/);
  } finally {
    delete REGISTRY.__no_default_test__;
  }
});

test('dispatch runs the invocation definition\'s handler against the given ctx and returns EXIT.OK', async () => {
  const seen = [];
  const invocation = { definition: { handler: async (ctx) => { seen.push(ctx); } } };
  const ctx = { marker: 'session-ctx' };
  const code = await dispatch(invocation, ctx);
  assert.equal(code, EXIT.OK);
  assert.deepEqual(seen, [ctx]);
});

test('dispatch propagates a handler rejection rather than swallowing it', async () => {
  const invocation = { definition: { handler: async () => { throw new Error('boom'); } } };
  await assert.rejects(() => dispatch(invocation, {}), /boom/);
});

test('dispatch does not itself touch buildContext, config or cache — it only runs the handler it is given', async () => {
  // This is the property the REPL depends on: dispatch must accept a ctx the
  // caller already built (and intends to reuse across lines) without ever
  // reaching back into loadConfig/loadCache/new Client itself.
  let handlerRan = false;
  const invocation = { definition: { handler: async (ctx) => { handlerRan = true; assert.equal(ctx.reused, true); } } };
  await dispatch(invocation, { reused: true });
  assert.ok(handlerRan);
});

test('main is now a one-shot wrapper: parseInvocation -> buildContext -> dispatch, same observable result as before', async () => {
  // Cross-check against the direct-call path: building the invocation and
  // ctx by hand and dispatching manually must match what main() itself
  // returns and writes, for both a plain and a --json invocation.
  const s1 = captureStreams();
  const code1 = await main(['doctor'], { streams: s1, env: {} });

  const s2 = captureStreams();
  const invocation = parseInvocation(['doctor']);
  let code2;
  try {
    const ctx = buildContext({ values: invocation.values, positionals: invocation.positionals, deps: { streams: s2, env: {} } });
    code2 = await dispatch(invocation, ctx);
  } catch (err) {
    s2.stderr.write(`error: ${err.message}\n`);
    code2 = err.code ?? EXIT.GENERAL;
  }

  assert.equal(code1, code2);
  assert.equal(code1, EXIT.AUTH);
  assert.match(s1.errText(), /no API token/i);
  assert.match(s2.errText(), /no API token/i);
});

// --- positionals metadata (Task 16 pre-work) -------------------------------
//
// renderHelp emitted prose with no argument syntax, so a REPL completer (or
// any other caller) would have to re-derive each action's positional shape
// by reading the handler. `search` is the one action whose first positional
// is a query, not a project ref — a REPL that always injects the current
// project as positional[0] must be able to tell that apart from the
// metadata alone, not by special-casing the word "search".

test('REGISTRY declares positionals metadata for every action', () => {
  for (const [group, actions] of Object.entries(REGISTRY)) {
    for (const [name, def] of Object.entries(actions)) {
      assert.ok(Array.isArray(def.positionals), `${group} ${name} is missing positionals metadata`);
    }
  }
});

test('positionals metadata matches each handler\'s actual positional reads', () => {
  assert.deepEqual(REGISTRY.item.list.positionals, ['project']);
  assert.deepEqual(REGISTRY.item.show.positionals, ['itemRef']);
  assert.deepEqual(REGISTRY.item.move.positionals, ['itemRef', 'state']);
  assert.deepEqual(REGISTRY.item.assign.positionals, ['itemRef', 'member']);
  assert.deepEqual(REGISTRY.board.__default.positionals, ['project']);
  assert.deepEqual(REGISTRY.my.__default.positionals, []);
});

test('search is flagged as the one action whose first positional is not a project ref', () => {
  // Everywhere else, positionals[0] is a project ref a REPL could inject
  // from its current `cd` context. search's is a search query — the '?'
  // on the second slot also says the project there is optional (falls back
  // to --project / the configured default).
  assert.deepEqual(REGISTRY.search.__default.positionals, ['query', 'project?']);
  assert.notEqual(REGISTRY.search.__default.positionals[0], 'project');
});

test('renderHelp renders each action\'s positional syntax', () => {
  const help = renderHelp('item');
  assert.match(help, /move\s+<itemRef>\s+<state>/);
  const boardHelp = renderHelp('board');
  assert.match(boardHelp, /<project>/);
});

test('save() rethrows an error that is not a recognised filesystem error', () => {
  const base = mkdtempSync(join(tmpdir(), 'cyb-cli-test-nonfs-'));
  const s = captureStreams();
  try {
    const ctx = buildContext({
      values: {},
      positionals: [],
      deps: {
        streams: s,
        env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
        cwd: '/nonexistent-cyb-dir',
        configPath: '/nonexistent-cyb-dir/config.json',
        cachePath: join(base, 'cache.json'),
      },
    });
    const circular = {};
    circular.self = circular;
    ctx.cache.circular = circular;
    assert.throws(() => ctx.save());
  } finally {
    rmSync(base, { recursive: true, force: true });
  }
});
