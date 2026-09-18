import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, statSync, chmodSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  emptyCache, loadCache, saveCache, isFresh, projectBucket,
  CACHE_VERSION, METADATA_TTL_MS,
} from '../src/cache.mjs';

function tmpPath() {
  return join(mkdtempSync(join(tmpdir(), 'cyb-cache-')), 'cache.json');
}

test('emptyCache has the documented shape', () => {
  const cache = emptyCache('cybernetics');
  assert.equal(cache.version, CACHE_VERSION);
  assert.equal(cache.workspace, 'cybernetics');
  assert.deepEqual(cache.projects, {});
  assert.deepEqual(cache.byProject, {});
  assert.equal(cache.me, null);
});

test('loadCache returns an empty cache when the file is absent', () => {
  const cache = loadCache({ path: tmpPath(), workspace: 'cybernetics' });
  assert.equal(cache.version, CACHE_VERSION);
  assert.deepEqual(cache.projects, {});
});

test('saveCache then loadCache round-trips', () => {
  const path = tmpPath();
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: 'uuid-1', name: 'Core', fetchedAt: '2026-08-17T00:00:00Z' };
  saveCache(cache, { path });
  assert.equal(loadCache({ path, workspace: 'cybernetics' }).projects.CYB.id, 'uuid-1');
});

test('a cache from a different version is discarded', () => {
  const path = tmpPath();
  writeFileSync(path, JSON.stringify({ version: 99, workspace: 'cybernetics', projects: { X: {} } }));
  assert.deepEqual(loadCache({ path, workspace: 'cybernetics' }).projects, {});
});

test('a cache for a different workspace is discarded', () => {
  const path = tmpPath();
  writeFileSync(path, JSON.stringify({ version: CACHE_VERSION, workspace: 'other', projects: { X: {} } }));
  assert.deepEqual(loadCache({ path, workspace: 'cybernetics' }).projects, {});
});

test('a corrupt cache file is discarded rather than throwing', () => {
  const path = tmpPath();
  writeFileSync(path, 'not json at all');
  assert.deepEqual(loadCache({ path, workspace: 'cybernetics' }).projects, {});
});

test('saveCache writes the file 0600', () => {
  const path = tmpPath();
  saveCache(emptyCache('cybernetics'), { path });
  assert.equal(statSync(path).mode & 0o777, 0o600);
});

test('saveCache tightens permissions on a pre-existing directory and file', () => {
  const dir = mkdtempSync(join(tmpdir(), 'cyb-cache-'));
  const nested = join(dir, 'nested');
  const path = join(nested, 'cache.json');
  mkdirSync(nested, { mode: 0o755 });
  writeFileSync(path, JSON.stringify({ stale: true }), { mode: 0o644 });
  chmodSync(nested, 0o755);
  chmodSync(path, 0o644);

  saveCache(emptyCache('cybernetics'), { path });

  assert.equal(statSync(nested).mode & 0o777, 0o700);
  assert.equal(statSync(path).mode & 0o777, 0o600);
});

test('isFresh is true inside the TTL and false outside it', () => {
  const now = () => 1_000_000;
  const recent = new Date(1_000_000 - 60_000).toISOString();
  const stale = new Date(1_000_000 - METADATA_TTL_MS - 1000).toISOString();
  assert.equal(isFresh(recent, { now }), true);
  assert.equal(isFresh(stale, { now }), false);
});

test('isFresh is false for missing or unparseable timestamps', () => {
  const now = () => 1_000_000;
  assert.equal(isFresh(null, { now }), false);
  assert.equal(isFresh('nonsense', { now }), false);
});

test('a wrong-typed byProject (string) is discarded and projectBucket does not throw', () => {
  const path = tmpPath();
  writeFileSync(path, JSON.stringify({ version: CACHE_VERSION, workspace: 'cybernetics', byProject: 'oops-a-string' }));
  const cache = loadCache({ path, workspace: 'cybernetics' });
  assert.deepEqual(cache.byProject, {});
  assert.doesNotThrow(() => projectBucket(cache, 'uuid-1'));
});

test('a wrong-typed projects (array) is discarded', () => {
  const path = tmpPath();
  writeFileSync(path, JSON.stringify({ version: CACHE_VERSION, workspace: 'cybernetics', projects: ['oops-an-array'] }));
  const cache = loadCache({ path, workspace: 'cybernetics' });
  assert.deepEqual(cache.projects, {});
});

test('a wrong-typed capabilities (array) is discarded', () => {
  const path = tmpPath();
  writeFileSync(path, JSON.stringify({ version: CACHE_VERSION, workspace: 'cybernetics', capabilities: ['oops-an-array'] }));
  const cache = loadCache({ path, workspace: 'cybernetics' });
  assert.deepEqual(cache.capabilities, {});
});

test('projectBucket creates the bucket on first access and reuses it after', () => {
  const cache = emptyCache('cybernetics');
  const bucket = projectBucket(cache, 'uuid-1');
  assert.deepEqual(bucket.states, {});
  bucket.states.todo = 'state-uuid';
  assert.equal(projectBucket(cache, 'uuid-1').states.todo, 'state-uuid');
});
