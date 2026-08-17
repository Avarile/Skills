import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, statSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadConfig, saveConfig, fingerprint, parseDotEnv, DEFAULTS } from '../src/config.mjs';

function tmp() {
  return mkdtempSync(join(tmpdir(), 'cyb-config-'));
}

test('env CYB_TOKEN wins over the config file', () => {
  const dir = tmp();
  const cfgPath = join(dir, 'config.json');
  writeFileSync(cfgPath, JSON.stringify({ token: 'from-file' }));
  const cfg = loadConfig({ env: { CYB_TOKEN: 'from-env' }, cwd: dir, configPath: cfgPath });
  assert.equal(cfg.token, 'from-env');
});

test('config file is used when env is absent', () => {
  const dir = tmp();
  const cfgPath = join(dir, 'config.json');
  writeFileSync(cfgPath, JSON.stringify({ token: 'from-file' }));
  const cfg = loadConfig({ env: {}, cwd: dir, configPath: cfgPath });
  assert.equal(cfg.token, 'from-file');
});

test('.env in cwd is the lowest-precedence token source', () => {
  const dir = tmp();
  writeFileSync(join(dir, '.env'), 'CYB_TOKEN=from-dotenv\n');
  const cfg = loadConfig({ env: {}, cwd: dir, configPath: join(dir, 'missing.json') });
  assert.equal(cfg.token, 'from-dotenv');
});

test('config file outranks .env', () => {
  const dir = tmp();
  const cfgPath = join(dir, 'config.json');
  writeFileSync(cfgPath, JSON.stringify({ token: 'from-file' }));
  writeFileSync(join(dir, '.env'), 'CYB_TOKEN=from-dotenv\n');
  const cfg = loadConfig({ env: {}, cwd: dir, configPath: cfgPath });
  assert.equal(cfg.token, 'from-file');
});

test('missing token yields null rather than throwing', () => {
  const dir = tmp();
  const cfg = loadConfig({ env: {}, cwd: dir, configPath: join(dir, 'missing.json') });
  assert.equal(cfg.token, null);
});

test('CYB_BASE_URL and CYB_WORKSPACE override config values', () => {
  const dir = tmp();
  const cfgPath = join(dir, 'config.json');
  writeFileSync(cfgPath, JSON.stringify({ baseUrl: 'https://file.example', workspace: 'wsfile' }));
  const cfg = loadConfig({
    env: { CYB_BASE_URL: 'https://env.example', CYB_WORKSPACE: 'wsenv' },
    cwd: dir,
    configPath: cfgPath,
  });
  assert.equal(cfg.baseUrl, 'https://env.example');
  assert.equal(cfg.workspace, 'wsenv');
});

test('defaults fill in when nothing is configured', () => {
  const dir = tmp();
  const cfg = loadConfig({ env: {}, cwd: dir, configPath: join(dir, 'missing.json') });
  assert.equal(cfg.baseUrl, DEFAULTS.baseUrl);
  assert.equal(cfg.workspace, DEFAULTS.workspace);
  assert.equal(cfg.defaults.limit, 30);
});

test('trailing slash is stripped from baseUrl', () => {
  const dir = tmp();
  const cfg = loadConfig({
    env: { CYB_BASE_URL: 'https://env.example/' },
    cwd: dir,
    configPath: join(dir, 'missing.json'),
  });
  assert.equal(cfg.baseUrl, 'https://env.example');
});

test('malformed config file is reported as a CybError, not a crash', () => {
  const dir = tmp();
  const cfgPath = join(dir, 'config.json');
  writeFileSync(cfgPath, '{ not json');
  assert.throws(
    () => loadConfig({ env: {}, cwd: dir, configPath: cfgPath }),
    (err) => err.name === 'CybError' && err.code === 1,
  );
});

test('saveConfig writes the file 0600 and the directory 0700', () => {
  const dir = tmp();
  const cfgPath = join(dir, 'nested', 'config.json');
  saveConfig({ token: 'secret', workspace: 'cybernetics' }, { configPath: cfgPath });
  assert.equal(statSync(cfgPath).mode & 0o777, 0o600);
  assert.equal(statSync(join(dir, 'nested')).mode & 0o777, 0o700);
  assert.equal(JSON.parse(readFileSync(cfgPath, 'utf8')).token, 'secret');
});

test('fingerprint reveals only the prefix and last four characters', () => {
  const fp = fingerprint('plane_api_ffffffffffffffffffffffffffffbeef');
  assert.equal(fp, 'plane_api_…beef');
  assert.ok(!fp.includes('ffffffffffff'));
});

test('fingerprint handles an absent token', () => {
  assert.equal(fingerprint(null), '(none)');
});

test('parseDotEnv ignores comments and blanks, and strips quotes', () => {
  const parsed = parseDotEnv('# comment\n\nA=1\nB="two"\nC=\'three\'\nBAD_LINE\n');
  assert.deepEqual(parsed, { A: '1', B: 'two', C: 'three' });
});
