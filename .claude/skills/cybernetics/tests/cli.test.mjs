import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, chmodSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { main, buildContext, GLOBAL_OPTIONS, renderHelp, REGISTRY } from '../src/cli.mjs';
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
