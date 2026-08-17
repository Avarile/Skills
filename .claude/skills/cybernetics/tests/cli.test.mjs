import { test } from 'node:test';
import assert from 'node:assert/strict';
import { main, GLOBAL_OPTIONS, renderHelp, REGISTRY } from '../src/cli.mjs';
import { EXIT } from '../src/errors.mjs';

function captureStreams() {
  const out = [];
  const err = [];
  return {
    stdout: { write: (s) => out.push(s), isTTY: false },
    stderr: { write: (s) => err.push(s) },
    outText: () => out.join(''),
    errText: () => err.join(''),
  };
}

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
