import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { main } from '../src/cli.mjs';
import { fingerprint } from '../src/config.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';
import { captureStreams } from './helpers/capture-streams.mjs';

// This is the highest-stakes property in a public repository: the token
// must never reach stdout, stderr, the verbose request log, or the cache
// file written to disk — only its fingerprint may. A recognisable sentinel,
// distinct from the tokens used elsewhere in the suite, means a leak here
// can't be dismissed as coincidental substring overlap.
const TOKEN = 'plane_api_containment_sentinel_0123456789';
const EXPECTED_FINGERPRINT = fingerprint(TOKEN);

function tmpPaths(prefix) {
  const dir = mkdtempSync(join(tmpdir(), `cyb-token-${prefix}-`));
  return { cwd: dir, configPath: join(dir, 'config.json'), cachePath: join(dir, 'cache.json') };
}

function assertTokenAbsent(text, label) {
  assert.ok(!text.includes(TOKEN), `token leaked into ${label}`);
}

test('a successful doctor run never leaks the token into stdout, stderr or the cache file', async () => {
  const s = captureStreams();
  const paths = tmpPaths('ok');
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ]);
  const code = await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: TOKEN },
    ...paths,
    fetchImpl,
    sleep: async () => {},
  });
  assert.equal(code, 0);
  assertTokenAbsent(s.outText(), 'stdout');
  assertTokenAbsent(s.errText(), 'stderr');

  // The fingerprint form is not merely absent-of-the-raw-token — it's
  // actually present where the report promises it.
  const report = JSON.parse(s.outText());
  assert.equal(report.token, EXPECTED_FINGERPRINT);
  assert.ok(s.outText().includes(EXPECTED_FINGERPRINT), 'fingerprint should be present in stdout');

  const cacheBytes = readFileSync(paths.cachePath, 'utf8');
  assertTokenAbsent(cacheBytes, 'the cache file');
});

test('a failing doctor run (bad token) never leaks the token into stdout or stderr', async () => {
  const s = captureStreams();
  const paths = tmpPaths('bad');
  const { fetchImpl } = makeFakeFetch([{ status: 401, body: { detail: 'bad token' } }]);
  const code = await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: TOKEN },
    ...paths,
    fetchImpl,
    sleep: async () => {},
  });
  assert.equal(code, 4);
  assertTokenAbsent(s.outText(), 'stdout');
  assertTokenAbsent(s.errText(), 'stderr');
});

test('doctor --verbose never leaks the token into the request log', async () => {
  const s = captureStreams();
  const paths = tmpPaths('verbose');
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ]);
  const code = await main(['doctor', '--verbose', '--json'], {
    streams: s,
    env: { CYB_TOKEN: TOKEN },
    ...paths,
    fetchImpl,
    sleep: async () => {},
  });
  assert.equal(code, 0);
  assertTokenAbsent(s.outText(), 'stdout');
  assertTokenAbsent(s.errText(), 'the verbose request log (stderr)');
  // The log line itself is still there — method, path, status — just never the token.
  assert.match(s.errText(), /GET \/users\/me\/ -> 200/);

  const report = JSON.parse(s.outText());
  assert.equal(report.token, EXPECTED_FINGERPRINT);

  const cacheBytes = readFileSync(paths.cachePath, 'utf8');
  assertTokenAbsent(cacheBytes, 'the cache file');
});
