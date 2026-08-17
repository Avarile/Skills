# Cybernetics Skill — Phase 1: Core Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the foundation modules — errors, config, HTTP client, cache, resolver, formatter, CLI router — culminating in a working `cyb doctor` that authenticates against the live instance and reports its capabilities.

**Architecture:** Seven small ES modules under `.claude/skills/cybernetics/src/`, each with one responsibility and no cross-dependencies beyond a strict downward chain: `errors` ← `config` ← `client` ← `cache` ← `resolve` ← `format` ← `cli`. Every module takes its collaborators via constructor/parameter injection so unit tests run with zero network access.

**Tech Stack:** Node 24 (verified v24.15.0), ESM, zero runtime dependencies. Built-ins only: `node:util` (`parseArgs`, `styleText`), `node:test`, `node:fs`, `node:os`, `node:path`, global `fetch`.

**Spec:** `docs/superpowers/specs/2026-08-17-cybernetics-skill-design.md`

## Global Constraints

- Zero runtime dependencies. No `npm install` of anything. Built-in modules only.
- Node >= 24. ESM only (`"type": "module"`). All source files use `.mjs`.
- Every file stays under 500 lines.
- The API token is never written into the repo, never logged, never printed in full. Only `fingerprint()` output may be displayed.
- API base is `/api/v1`. Auth header is `X-Api-Key` — never `Authorization: Bearer` (returns 401 on this instance).
- Rate limit is 60 req/min via `x-ratelimit-remaining` / `x-ratelimit-reset`.
- Work items live at `/issues/` (canonical on this v2.6.3 fork).
- Exit codes: `0` ok, `1` general, `2` refused, `3` not found, `4` auth, `5` rate limited.
- Tests run with `node --test` from `.claude/skills/cybernetics/`.
- All unit tests must pass with no network access and no `CYB_TOKEN` set.

### Deliberate deviation from the spec

The spec's architecture lists a single `resolve.mjs` holding both the cache and
the resolution logic. This plan splits it into `cache.mjs` (persistence, TTL,
versioning — Task 4) and `resolve.mjs` (name lookup, suggestions, fallback
scan — Task 5). They are separate responsibilities with separate failure modes,
and splitting them lets the cache be tested against the filesystem while the
resolver is tested entirely in memory. Everything else follows the spec layout.

---

### Task 1: Scaffold and Error Types

**Files:**
- Create: `.claude/skills/cybernetics/package.json`
- Create: `.claude/skills/cybernetics/bin/cyb`
- Create: `.claude/skills/cybernetics/src/errors.mjs`
- Test: `.claude/skills/cybernetics/tests/errors.test.mjs`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `EXIT` (frozen object with keys `OK`, `GENERAL`, `REFUSED`, `NOT_FOUND`, `AUTH`, `RATE_LIMIT`), `class CybError extends Error` with fields `code:number`, `message:string`, `hint:string|null` and method `toJSON()`, `class ApiError extends CybError` with additional fields `status:number`, `body:unknown`, `path:string`.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/errors.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EXIT, CybError, ApiError } from '../src/errors.mjs';

test('EXIT codes match the spec table', () => {
  assert.equal(EXIT.OK, 0);
  assert.equal(EXIT.GENERAL, 1);
  assert.equal(EXIT.REFUSED, 2);
  assert.equal(EXIT.NOT_FOUND, 3);
  assert.equal(EXIT.AUTH, 4);
  assert.equal(EXIT.RATE_LIMIT, 5);
});

test('CybError carries code, message and hint', () => {
  const err = new CybError(EXIT.REFUSED, 'needs --yes', 'pass --yes to confirm');
  assert.equal(err.code, 2);
  assert.equal(err.message, 'needs --yes');
  assert.equal(err.hint, 'pass --yes to confirm');
  assert.ok(err instanceof Error);
});

test('CybError.toJSON produces the agent-parseable envelope', () => {
  const err = new CybError(EXIT.NOT_FOUND, 'no such project: ZZZ', 'run: cyb project list');
  assert.deepEqual(err.toJSON(), {
    error: { code: 3, message: 'no such project: ZZZ', hint: 'run: cyb project list' },
  });
});

test('CybError hint defaults to null', () => {
  assert.equal(new CybError(EXIT.GENERAL, 'boom').hint, null);
});

test('ApiError maps 401 and 403 to the auth exit code', () => {
  assert.equal(new ApiError(401, {}, '/projects/').code, EXIT.AUTH);
  assert.equal(new ApiError(403, {}, '/initiatives/').code, EXIT.AUTH);
});

test('ApiError maps 404 to not-found and 429 to rate-limit', () => {
  assert.equal(new ApiError(404, {}, '/estimates/').code, EXIT.NOT_FOUND);
  assert.equal(new ApiError(429, {}, '/issues/').code, EXIT.RATE_LIMIT);
});

test('ApiError maps other failures to the general exit code', () => {
  assert.equal(new ApiError(400, {}, '/issues/').code, EXIT.GENERAL);
  assert.equal(new ApiError(500, {}, '/issues/').code, EXIT.GENERAL);
});

test('ApiError surfaces a hint for the 402 licensing wall', () => {
  const err = new ApiError(402, {}, '/issue-types/');
  assert.match(err.hint, /not licensed/i);
});

test('ApiError retains status, body and path', () => {
  const body = { priority: ['"__invalid__" is not a valid choice.'] };
  const err = new ApiError(400, body, '/issues/');
  assert.equal(err.status, 400);
  assert.deepEqual(err.body, body);
  assert.equal(err.path, '/issues/');
});

test('ApiError renders field validation errors into the message', () => {
  const err = new ApiError(400, { priority: ['"x" is not a valid choice.'] }, '/issues/');
  assert.match(err.message, /priority/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/errors.test.mjs`
Expected: FAIL — `Cannot find module '../src/errors.mjs'`

- [ ] **Step 3: Write the scaffold and implementation**

Create `.claude/skills/cybernetics/package.json`:

```json
{
  "name": "cybernetics-cli",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "description": "Zero-dependency CLI for the Cybernetics Plane instance",
  "bin": { "cyb": "./bin/cyb" },
  "engines": { "node": ">=24" },
  "scripts": {
    "test": "node --test",
    "test:integration": "CYB_RUN_INTEGRATION=1 node --test tests/integration/*.test.mjs"
  }
}
```

Create `.claude/skills/cybernetics/bin/cyb`:

```js
#!/usr/bin/env node
import { main } from '../src/cli.mjs';

process.exitCode = await main(process.argv.slice(2));
```

Create `.claude/skills/cybernetics/src/errors.mjs`:

```js
export const EXIT = Object.freeze({
  OK: 0,
  GENERAL: 1,
  REFUSED: 2,
  NOT_FOUND: 3,
  AUTH: 4,
  RATE_LIMIT: 5,
});

export class CybError extends Error {
  constructor(code, message, hint = null) {
    super(message);
    this.name = 'CybError';
    this.code = code;
    this.hint = hint;
  }

  toJSON() {
    return { error: { code: this.code, message: this.message, hint: this.hint } };
  }
}

const HINTS = {
  401: 'token rejected — check CYB_TOKEN or run: cyb doctor',
  402: 'this feature is not licensed on this instance',
  403: 'not permitted for this token, or the feature is gated on this instance',
  404: 'endpoint or record not found — run: cyb doctor to refresh capabilities',
  429: 'rate limited (60 req/min) — retry shortly or reduce --limit',
};

function describeBody(body) {
  if (!body || typeof body !== 'object') return '';
  const parts = [];
  for (const [field, detail] of Object.entries(body)) {
    const text = Array.isArray(detail) ? detail.join(' ') : String(detail);
    parts.push(`${field}: ${text}`);
  }
  return parts.length ? ` (${parts.join('; ')})` : '';
}

function exitCodeFor(status) {
  if (status === 401 || status === 403) return EXIT.AUTH;
  if (status === 404) return EXIT.NOT_FOUND;
  if (status === 429) return EXIT.RATE_LIMIT;
  return EXIT.GENERAL;
}

export class ApiError extends CybError {
  constructor(status, body, path) {
    super(
      exitCodeFor(status),
      `API ${status} on ${path}${describeBody(body)}`,
      HINTS[status] ?? null,
    );
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
    this.path = path;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/errors.test.mjs`
Expected: PASS — 10 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/package.json \
        .claude/skills/cybernetics/bin/cyb \
        .claude/skills/cybernetics/src/errors.mjs \
        .claude/skills/cybernetics/tests/errors.test.mjs
git commit -m "feat(cyb): scaffold CLI package and error types with exit-code mapping"
```

---

### Task 2: Configuration and Credential Precedence

**Files:**
- Create: `.claude/skills/cybernetics/src/config.mjs`
- Test: `.claude/skills/cybernetics/tests/config.test.mjs`

**Interfaces:**
- Consumes: `CybError`, `EXIT` from `src/errors.mjs`
- Produces:
  - `CONFIG_DIR: string`, `CONFIG_PATH: string`
  - `DEFAULTS: { baseUrl, workspace, limit }`
  - `loadConfig({ env, cwd, configPath }) -> { baseUrl, workspace, token, defaultProject, defaults: { limit } }`
  - `saveConfig(config, { configPath }) -> void`
  - `fingerprint(token) -> string`
  - `parseDotEnv(text) -> Record<string,string>`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/config.test.mjs`:

```js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/config.test.mjs`
Expected: FAIL — `Cannot find module '../src/config.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/config.mjs`:

```js
import { readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { CybError, EXIT } from './errors.mjs';

export const CONFIG_DIR = join(homedir(), '.cybernetics');
export const CONFIG_PATH = join(CONFIG_DIR, 'config.json');

export const DEFAULTS = Object.freeze({
  baseUrl: 'https://projects.avarile.com',
  workspace: 'cybernetics',
  limit: 30,
});

export function parseDotEnv(text) {
  const out = {};
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    const quoted =
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"));
    if (quoted && value.length >= 2) value = value.slice(1, -1);
    out[key] = value;
  }
  return out;
}

function readJson(path) {
  if (!existsSync(path)) return {};
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (err) {
    throw new CybError(
      EXIT.GENERAL,
      `config file is not valid JSON: ${path}`,
      'fix the file by hand, or delete it and run: cyb init',
    );
  }
}

function stripSlash(url) {
  return typeof url === 'string' ? url.replace(/\/+$/, '') : url;
}

export function loadConfig({ env = process.env, cwd = process.cwd(), configPath = CONFIG_PATH } = {}) {
  const file = readJson(configPath);

  const dotEnvPath = join(cwd, '.env');
  const dotEnv = existsSync(dotEnvPath) ? parseDotEnv(readFileSync(dotEnvPath, 'utf8')) : {};

  const token = env.CYB_TOKEN ?? file.token ?? dotEnv.CYB_TOKEN ?? null;

  return {
    baseUrl: stripSlash(env.CYB_BASE_URL ?? file.baseUrl ?? dotEnv.CYB_BASE_URL ?? DEFAULTS.baseUrl),
    workspace: env.CYB_WORKSPACE ?? file.workspace ?? dotEnv.CYB_WORKSPACE ?? DEFAULTS.workspace,
    token,
    defaultProject: env.CYB_PROJECT ?? file.defaultProject ?? null,
    defaults: { limit: Number(file.defaults?.limit ?? DEFAULTS.limit) },
  };
}

export function saveConfig(config, { configPath = CONFIG_PATH } = {}) {
  const dir = dirname(configPath);
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
}

export function fingerprint(token) {
  if (!token) return '(none)';
  if (token.length <= 14) return '…';
  return `${token.slice(0, 10)}…${token.slice(-4)}`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/config.test.mjs`
Expected: PASS — 13 tests

Note: `mkdirSync` honours `mode` only on the directories it creates. If the assertion on `0o700` fails because the temp parent already existed, that is a test-environment artifact — the nested directory is the one being asserted and it is always freshly created.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/config.mjs \
        .claude/skills/cybernetics/tests/config.test.mjs
git commit -m "feat(cyb): add config loader with token precedence and 0600 storage"
```

---

### Task 3: HTTP Client with Rate-Limit Awareness

**Files:**
- Create: `.claude/skills/cybernetics/src/client.mjs`
- Create: `.claude/skills/cybernetics/tests/helpers/fake-fetch.mjs`
- Test: `.claude/skills/cybernetics/tests/client.test.mjs`

**Interfaces:**
- Consumes: `ApiError` from `src/errors.mjs`
- Produces:
  - `class Client` constructed as `new Client({ baseUrl, workspace, token, fetchImpl, sleep, now })`
  - `client.wsPath -> string` (getter, e.g. `/workspaces/cybernetics`)
  - `client.projectPath(projectId) -> string`
  - `client.request(method, path, { body, query, fields, expand, timeout }) -> Promise<{ status, data, headers }>`
  - `client.paginate(path, { query, fields, limit }) -> AsyncIterable<object>`
  - `client.callCount -> number`
- Test helper produces: `makeFakeFetch(responses) -> { fetchImpl, calls }` where `responses` is an array of `{ status, body, headers }` consumed in order.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/helpers/fake-fetch.mjs`:

```js
export function makeFakeFetch(responses) {
  const queue = [...responses];
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    const next = queue.shift();
    if (!next) throw new Error(`fake-fetch: no queued response for ${url}`);
    return {
      status: next.status,
      headers: { get: (k) => (next.headers ?? {})[k.toLowerCase()] ?? null },
      text: async () => (next.body === undefined ? '' : JSON.stringify(next.body)),
    };
  };
  return { fetchImpl, calls };
}
```

Create `.claude/skills/cybernetics/tests/client.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '../src/client.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';

function makeClient(responses, overrides = {}) {
  const { fetchImpl, calls } = makeFakeFetch(responses);
  const slept = [];
  const client = new Client({
    baseUrl: 'https://example.test',
    workspace: 'cybernetics',
    token: 'tok',
    fetchImpl,
    sleep: async (ms) => { slept.push(ms); },
    now: () => 1_000_000,
    ...overrides,
  });
  return { client, calls, slept };
}

test('request sends X-Api-Key and never a Bearer header', async () => {
  const { client, calls } = makeClient([{ status: 200, body: { ok: true } }]);
  await client.request('GET', '/workspaces/cybernetics/projects/');
  assert.equal(calls[0].init.headers['X-Api-Key'], 'tok');
  assert.equal(calls[0].init.headers.Authorization, undefined);
});

test('request builds the /api/v1 URL from baseUrl and path', async () => {
  const { client, calls } = makeClient([{ status: 200, body: {} }]);
  await client.request('GET', '/workspaces/cybernetics/projects/');
  assert.equal(calls[0].url, 'https://example.test/api/v1/workspaces/cybernetics/projects/');
});

test('fields and expand are serialised as comma-joined query params', async () => {
  const { client, calls } = makeClient([{ status: 200, body: {} }]);
  await client.request('GET', '/issues/', { fields: ['id', 'name'], expand: ['state'] });
  const url = new URL(calls[0].url);
  assert.equal(url.searchParams.get('fields'), 'id,name');
  assert.equal(url.searchParams.get('expand'), 'state');
});

test('undefined query values are omitted', async () => {
  const { client, calls } = makeClient([{ status: 200, body: {} }]);
  await client.request('GET', '/issues/', { query: { a: 1, b: undefined, c: null } });
  const url = new URL(calls[0].url);
  assert.equal(url.searchParams.get('a'), '1');
  assert.ok(!url.searchParams.has('b'));
  assert.ok(!url.searchParams.has('c'));
});

test('Content-Type is set only when a body is present', async () => {
  const { client, calls } = makeClient([
    { status: 200, body: {} },
    { status: 201, body: {} },
  ]);
  await client.request('GET', '/issues/');
  assert.equal(calls[0].init.headers['Content-Type'], undefined);
  await client.request('POST', '/issues/', { body: { name: 'x' } });
  assert.equal(calls[1].init.headers['Content-Type'], 'application/json');
  assert.equal(calls[1].init.body, JSON.stringify({ name: 'x' }));
});

test('wsPath and projectPath compose the documented shapes', () => {
  const { client } = makeClient([]);
  assert.equal(client.wsPath, '/workspaces/cybernetics');
  assert.equal(client.projectPath('abc'), '/workspaces/cybernetics/projects/abc');
});

test('non-2xx responses throw ApiError carrying status and path', async () => {
  const { client } = makeClient([{ status: 400, body: { priority: ['bad'] } }]);
  await assert.rejects(
    () => client.request('POST', '/issues/', { body: {} }),
    (err) => err.name === 'ApiError' && err.status === 400 && err.path === '/issues/',
  );
});

test('a 429 is retried after waiting for the reset window', async () => {
  const { client, slept } = makeClient([
    { status: 429, body: {}, headers: { 'x-ratelimit-reset': '1005' } },
    { status: 200, body: { ok: true } },
  ]);
  const res = await client.request('GET', '/issues/');
  assert.equal(res.status, 200);
  assert.equal(slept.length, 1);
  assert.ok(slept[0] > 0);
});

test('5xx is retried with backoff then succeeds', async () => {
  const { client, slept } = makeClient([
    { status: 500, body: {} },
    { status: 200, body: { ok: true } },
  ]);
  const res = await client.request('GET', '/issues/');
  assert.equal(res.status, 200);
  assert.deepEqual(slept, [500]);
});

test('retries give up after 3 attempts and throw', async () => {
  const { client } = makeClient([
    { status: 500, body: {} },
    { status: 500, body: {} },
    { status: 500, body: {} },
  ]);
  await assert.rejects(() => client.request('GET', '/issues/'), (err) => err.status === 500);
});

test('4xx other than 429 is never retried', async () => {
  const { client, calls } = makeClient([{ status: 404, body: {} }]);
  await assert.rejects(() => client.request('GET', '/estimates/'));
  assert.equal(calls.length, 1);
});

test('a low remaining budget triggers a wait before the next request', async () => {
  const { client, slept } = makeClient([
    { status: 200, body: {}, headers: { 'x-ratelimit-remaining': '2', 'x-ratelimit-reset': '1030' } },
    { status: 200, body: {} },
  ]);
  await client.request('GET', '/issues/');
  await client.request('GET', '/issues/');
  assert.equal(slept.length, 1);
});

test('paginate follows next_cursor and stops when results are exhausted', async () => {
  const { client } = makeClient([
    { status: 200, body: { results: [{ id: 1 }, { id: 2 }], next_page_results: true, next_cursor: 'c2' } },
    { status: 200, body: { results: [{ id: 3 }], next_page_results: false, next_cursor: null } },
  ]);
  const seen = [];
  for await (const item of client.paginate('/issues/')) seen.push(item.id);
  assert.deepEqual(seen, [1, 2, 3]);
});

test('paginate stops at the requested limit without fetching further pages', async () => {
  const { client, calls } = makeClient([
    { status: 200, body: { results: [{ id: 1 }, { id: 2 }], next_page_results: true, next_cursor: 'c2' } },
  ]);
  const seen = [];
  for await (const item of client.paginate('/issues/', { limit: 2 })) seen.push(item.id);
  assert.deepEqual(seen, [1, 2]);
  assert.equal(calls.length, 1);
});

test('callCount tracks total requests issued', async () => {
  const { client } = makeClient([{ status: 200, body: {} }, { status: 200, body: {} }]);
  await client.request('GET', '/a/');
  await client.request('GET', '/b/');
  assert.equal(client.callCount, 2);
});

test('verbose logs a request line to the supplied stream', async () => {
  const logged = [];
  const { client } = makeClient([{ status: 200, body: {} }], {
    verbose: true,
    logStream: { write: (s) => logged.push(s) },
  });
  await client.request('GET', '/issues/');
  assert.deepEqual(logged, ['GET /issues/ -> 200\n']);
});

test('verbose is silent when not enabled', async () => {
  const logged = [];
  const { client } = makeClient([{ status: 200, body: {} }], {
    logStream: { write: (s) => logged.push(s) },
  });
  await client.request('GET', '/issues/');
  assert.deepEqual(logged, []);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/client.test.mjs`
Expected: FAIL — `Cannot find module '../src/client.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/client.mjs`:

```js
import { ApiError } from './errors.mjs';

const MAX_ATTEMPTS = 3;
const BACKOFF_MS = [500, 1000, 2000];
const LOW_BUDGET = 5;

const defaultSleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export class Client {
  constructor({
    baseUrl,
    workspace,
    token,
    fetchImpl = globalThis.fetch,
    sleep = defaultSleep,
    now = Date.now,
    verbose = false,
    logStream = null,
  }) {
    this.baseUrl = baseUrl;
    this.workspace = workspace;
    this.token = token;
    this.fetchImpl = fetchImpl;
    this.sleep = sleep;
    this.now = now;
    this.verbose = verbose;
    this.logStream = logStream;
    this.callCount = 0;
    this.remaining = null;
    this.resetAt = null;
  }

  get wsPath() {
    return `/workspaces/${this.workspace}`;
  }

  projectPath(projectId) {
    return `${this.wsPath}/projects/${projectId}`;
  }

  buildUrl(path, { query, fields, expand } = {}) {
    const url = new URL(`${this.baseUrl}/api/v1${path}`);
    if (fields?.length) url.searchParams.set('fields', fields.join(','));
    if (expand?.length) url.searchParams.set('expand', expand.join(','));
    for (const [key, value] of Object.entries(query ?? {})) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
    return url.toString();
  }

  msUntilReset() {
    if (!this.resetAt) return 1000;
    const delta = this.resetAt * 1000 - this.now();
    return delta > 0 ? delta : 1000;
  }

  noteRateLimit(headers) {
    const remaining = headers.get('x-ratelimit-remaining');
    const reset = headers.get('x-ratelimit-reset');
    if (remaining !== null) this.remaining = Number(remaining);
    if (reset !== null) this.resetAt = Number(reset);
  }

  async request(method, path, { body, query, fields, expand, timeout = 30_000 } = {}) {
    if (this.remaining !== null && this.remaining < LOW_BUDGET) {
      await this.sleep(this.msUntilReset());
      this.remaining = null;
    }

    const url = this.buildUrl(path, { query, fields, expand });
    const headers = { 'X-Api-Key': this.token };
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    let lastError = null;
    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);
      this.callCount++;
      let res;
      try {
        res = await this.fetchImpl(url, {
          method,
          headers,
          signal: controller.signal,
          ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
        });
      } finally {
        clearTimeout(timer);
      }

      this.noteRateLimit(res.headers);

      if (this.verbose && this.logStream) {
        this.logStream.write(`${method} ${path} -> ${res.status}\n`);
      }

      const text = await res.text();
      let data = null;
      if (text) {
        try {
          data = JSON.parse(text);
        } catch {
          data = text.slice(0, 500);
        }
      }

      if (res.status >= 200 && res.status < 300) {
        return { status: res.status, data, headers: res.headers };
      }

      lastError = new ApiError(res.status, data, path);

      const retryable = res.status === 429 || res.status >= 500;
      if (!retryable || attempt === MAX_ATTEMPTS - 1) throw lastError;

      await this.sleep(res.status === 429 ? this.msUntilReset() : BACKOFF_MS[attempt]);
    }

    throw lastError;
  }

  async *paginate(path, { query = {}, fields, limit = Infinity } = {}) {
    let cursor = null;
    let yielded = 0;

    while (yielded < limit) {
      const perPage = Math.max(1, Math.min(100, limit - yielded));
      const pageQuery = { ...query, per_page: perPage };
      if (cursor) pageQuery.cursor = cursor;

      const { data } = await this.request('GET', path, { query: pageQuery, fields });
      const results = data?.results ?? [];

      // No forward progress is possible from an empty page, whatever
      // next_page_results claims. Without this, limit=Infinity spins forever.
      if (results.length === 0) return;

      for (const item of results) {
        if (yielded >= limit) return;
        yield item;
        yielded++;
      }

      if (!data?.next_page_results || !data?.next_cursor) return;
      // A repeated cursor means the server is not advancing; stop rather than refetch.
      if (data.next_cursor === cursor) return;
      cursor = data.next_cursor;
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/client.test.mjs`
Expected: PASS — 17 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/client.mjs \
        .claude/skills/cybernetics/tests/client.test.mjs \
        .claude/skills/cybernetics/tests/helpers/fake-fetch.mjs
git commit -m "feat(cyb): add HTTP client with retry, rate-limit budget and cursor pagination"
```

---

### Task 4: Cache Persistence

**Files:**
- Create: `.claude/skills/cybernetics/src/cache.mjs`
- Test: `.claude/skills/cybernetics/tests/cache.test.mjs`

**Interfaces:**
- Consumes: `CONFIG_DIR` from `src/config.mjs`
- Produces:
  - `CACHE_PATH: string`, `CACHE_VERSION = 1`, `METADATA_TTL_MS = 900000`
  - `emptyCache(workspace) -> cache`
  - `loadCache({ path, workspace }) -> cache`
  - `saveCache(cache, { path }) -> void`
  - `isFresh(fetchedAt, { now, ttl }) -> boolean`
  - `projectBucket(cache, projectId) -> { states, labels, members, items, fetchedAt }` (creates the bucket in place when absent)

Cache shape (matches the spec):

```jsonc
{
  "version": 1,
  "workspace": "cybernetics",
  "me": { "id": "uuid", "display_name": "avarile" },
  "capabilities": { "issues": true, "estimates": false, "issueTypes": 402 },
  "projects": { "CYB": { "id": "uuid", "name": "…", "fetchedAt": "…" } },
  "byProject": {
    "<uuid>": { "states": {}, "labels": {}, "members": {}, "items": {}, "fetchedAt": "…" }
  }
}
```

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/cache.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, statSync } from 'node:fs';
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

test('projectBucket creates the bucket on first access and reuses it after', () => {
  const cache = emptyCache('cybernetics');
  const bucket = projectBucket(cache, 'uuid-1');
  assert.deepEqual(bucket.states, {});
  bucket.states.todo = 'state-uuid';
  assert.equal(projectBucket(cache, 'uuid-1').states.todo, 'state-uuid');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/cache.test.mjs`
Expected: FAIL — `Cannot find module '../src/cache.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/cache.mjs`:

```js
import { readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { CONFIG_DIR } from './config.mjs';

export const CACHE_PATH = join(CONFIG_DIR, 'cache.json');
export const CACHE_VERSION = 1;
export const METADATA_TTL_MS = 15 * 60 * 1000;

export function emptyCache(workspace) {
  return {
    version: CACHE_VERSION,
    workspace,
    me: null,
    capabilities: {},
    projects: {},
    byProject: {},
  };
}

const isPlainObject = (v) => typeof v === 'object' && v !== null && !Array.isArray(v);

export function loadCache({ path = CACHE_PATH, workspace } = {}) {
  if (!existsSync(path)) return emptyCache(workspace);
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8'));
    if (!isPlainObject(parsed)) return emptyCache(workspace);
    if (parsed.version !== CACHE_VERSION) return emptyCache(workspace);
    if (parsed.workspace !== workspace) return emptyCache(workspace);
    // Validate the TYPE of each sub-key, not just its presence: `??` lets a
    // wrong-typed value (e.g. byProject: "oops") through, and projectBucket
    // then throws when it assigns a property to a primitive.
    return {
      ...emptyCache(workspace),
      ...parsed,
      projects: isPlainObject(parsed.projects) ? parsed.projects : {},
      byProject: isPlainObject(parsed.byProject) ? parsed.byProject : {},
      capabilities: isPlainObject(parsed.capabilities) ? parsed.capabilities : {},
    };
  } catch {
    return emptyCache(workspace);
  }
}

export function saveCache(cache, { path = CACHE_PATH } = {}) {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  writeFileSync(path, `${JSON.stringify(cache, null, 2)}\n`, { mode: 0o600 });
}

export function isFresh(fetchedAt, { now = Date.now, ttl = METADATA_TTL_MS } = {}) {
  if (!fetchedAt) return false;
  const at = Date.parse(fetchedAt);
  if (Number.isNaN(at)) return false;
  return now() - at < ttl;
}

export function projectBucket(cache, projectId) {
  cache.byProject[projectId] ??= {
    states: {},
    labels: {},
    members: {},
    items: {},
    fetchedAt: null,
  };
  return cache.byProject[projectId];
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/cache.test.mjs`
Expected: PASS — 10 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/cache.mjs \
        .claude/skills/cybernetics/tests/cache.test.mjs
git commit -m "feat(cyb): add versioned cache persistence with TTL freshness checks"
```

---

### Task 5: Name-to-UUID Resolver

**Files:**
- Create: `.claude/skills/cybernetics/src/resolve.mjs`
- Test: `.claude/skills/cybernetics/tests/resolve.test.mjs`

**Interfaces:**
- Consumes: `Client` from `src/client.mjs`; `emptyCache`, `projectBucket`, `isFresh` from `src/cache.mjs`; `CybError`, `EXIT` from `src/errors.mjs`
- Produces:
  - `class Resolver` constructed as `new Resolver({ client, cache, persist, now, noCache })` where `persist` is a `(cache) => void` callback
  - `resolver.me() -> Promise<{ id, display_name }>`
  - `resolver.project(ref) -> Promise<{ id, identifier, name }>`
  - `resolver.item(ref) -> Promise<{ id, projectId, sequence_id }>`
  - `resolver.statesFor(projectId) -> Promise<Array<{ id, name, group }>>`
  - `resolver.state(projectId, name) -> Promise<string>`
  - `resolver.label(projectId, name) -> Promise<string>`
  - `resolver.member(name) -> Promise<string>`
  - `isUuid(value) -> boolean`
  - `parseItemRef(ref) -> { identifier, sequence } | null`
  - `suggest(input, candidates) -> string | null`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/resolve.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Resolver, isUuid, parseItemRef, suggest } from '../src/resolve.mjs';
import { emptyCache } from '../src/cache.mjs';
import { Client } from '../src/client.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';

const UUID_A = '50fc7f95-db38-4fe8-850b-41643c1ca2f5';
const UUID_B = '8c3d7fcf-662c-44db-8d50-ccb556664063';

function makeResolver(responses, { cache } = {}) {
  const { fetchImpl, calls } = makeFakeFetch(responses);
  const client = new Client({
    baseUrl: 'https://example.test',
    workspace: 'cybernetics',
    token: 'tok',
    fetchImpl,
    sleep: async () => {},
    now: () => 1_000_000,
  });
  const saved = [];
  const resolver = new Resolver({
    client,
    cache: cache ?? emptyCache('cybernetics'),
    persist: (c) => saved.push(c),
    now: () => 1_000_000,
  });
  return { resolver, calls, saved };
}

test('isUuid distinguishes UUIDs from identifiers', () => {
  assert.equal(isUuid(UUID_A), true);
  assert.equal(isUuid('CYB'), false);
  assert.equal(isUuid('CYB-42'), false);
});

test('parseItemRef splits identifier and sequence', () => {
  assert.deepEqual(parseItemRef('CYB-42'), { identifier: 'CYB', sequence: 42 });
  assert.deepEqual(parseItemRef('cyb-7'), { identifier: 'CYB', sequence: 7 });
  assert.equal(parseItemRef('CYB'), null);
  assert.equal(parseItemRef(UUID_A), null);
});

test('suggest finds the nearest candidate', () => {
  assert.equal(suggest('in progres', ['Backlog', 'In Progress', 'Done']), 'In Progress');
  assert.equal(suggest('zzzzzzzzzz', ['Backlog', 'Done']), null);
});

test('project resolves an identifier and caches the result', async () => {
  const { resolver, calls, saved } = makeResolver([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ]);
  const project = await resolver.project('CYB');
  assert.deepEqual(project, { id: UUID_A, identifier: 'CYB', name: 'Core' });
  assert.equal(calls.length, 1);
  assert.equal(saved.at(-1).projects.CYB.id, UUID_A);
});

test('a cached project costs no request', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000 - 1000).toISOString() };
  const { resolver, calls } = makeResolver([], { cache });
  const project = await resolver.project('CYB');
  assert.equal(project.id, UUID_A);
  assert.equal(calls.length, 0);
});

test('a UUID passed as a project ref is returned without a lookup', async () => {
  const { resolver, calls } = makeResolver([]);
  const project = await resolver.project(UUID_A);
  assert.equal(project.id, UUID_A);
  assert.equal(calls.length, 0);
});

test('an unknown project raises a not-found CybError naming the ref', async () => {
  const { resolver } = makeResolver([{ status: 200, body: { results: [] } }]);
  await assert.rejects(
    () => resolver.project('ZZZ'),
    (err) => err.name === 'CybError' && err.code === 3 && /ZZZ/.test(err.message),
  );
});

test('state resolves case-insensitively from the project state list', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: {
        results: [
          { id: UUID_B, name: 'In Progress', group: 'started' },
          { id: 'other', name: 'Done', group: 'completed' },
        ],
      },
    },
  ]);
  assert.equal(await resolver.state(UUID_A, 'in progress'), UUID_B);
});

test('an unknown state error lists the valid states and suggests the nearest', async () => {
  const { resolver } = makeResolver([
    {
      status: 200,
      body: { results: [{ id: UUID_B, name: 'In Progress', group: 'started' }] },
    },
  ]);
  await assert.rejects(
    () => resolver.state(UUID_A, 'in progres'),
    (err) => err.code === 3 && /In Progress/.test(err.hint),
  );
});

test('item resolves CYB-42 via the sequence_id filter when it narrows to one', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  const { resolver, calls } = makeResolver(
    [{ status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } }],
    { cache },
  );
  const item = await resolver.item('CYB-42');
  assert.deepEqual(item, { id: 'item-uuid', projectId: UUID_A, sequence_id: 42 });
  assert.equal(calls.length, 1);
});

test('item falls back to a projected scan when the filter fails to narrow', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  const { resolver } = makeResolver(
    [
      { status: 200, body: { results: [{ id: 'a', sequence_id: 1 }, { id: 'b', sequence_id: 42 }] } },
      {
        status: 200,
        body: {
          results: [{ id: 'a', sequence_id: 1 }, { id: 'b', sequence_id: 42 }],
          next_page_results: false,
          next_cursor: null,
        },
      },
    ],
    { cache },
  );
  const item = await resolver.item('CYB-42');
  assert.equal(item.id, 'b');
});

test('a cached item sequence costs no request', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  cache.byProject[UUID_A] = { states: {}, labels: {}, members: {}, items: { 42: 'item-uuid' }, fetchedAt: null };
  const { resolver, calls } = makeResolver([], { cache });
  assert.equal((await resolver.item('CYB-42')).id, 'item-uuid');
  assert.equal(calls.length, 0);
});

test('an unparseable item ref is rejected with guidance', async () => {
  const { resolver } = makeResolver([]);
  await assert.rejects(
    () => resolver.item('nonsense'),
    (err) => err.code === 3 && /CYB-42/.test(err.hint),
  );
});

test('noCache forces a refetch even when the cache is warm', async () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: UUID_A, name: 'Core', fetchedAt: new Date(1_000_000).toISOString() };
  const { fetchImpl, calls } = makeFakeFetch([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ]);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const resolver = new Resolver({ client, cache, persist: () => {}, now: () => 1_000_000, noCache: true });
  await resolver.project('CYB');
  assert.equal(calls.length, 1);
});

test('me is fetched once and cached', async () => {
  const { resolver, calls } = makeResolver([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
  ]);
  assert.equal((await resolver.me()).id, 'me-uuid');
  assert.equal((await resolver.me()).id, 'me-uuid');
  assert.equal(calls.length, 1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/resolve.test.mjs`
Expected: FAIL — `Cannot find module '../src/resolve.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/resolve.mjs`:

```js
import { projectBucket, isFresh } from './cache.mjs';
import { CybError, EXIT } from './errors.mjs';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ITEM_REF_RE = /^([A-Za-z][A-Za-z0-9]*)-(\d+)$/;

export function isUuid(value) {
  return typeof value === 'string' && UUID_RE.test(value);
}

export function parseItemRef(ref) {
  if (typeof ref !== 'string' || isUuid(ref)) return null;
  const match = ITEM_REF_RE.exec(ref.trim());
  if (!match) return null;
  return { identifier: match[1].toUpperCase(), sequence: Number(match[2]) };
}

function distance(a, b) {
  const rows = a.length + 1;
  const cols = b.length + 1;
  let prev = Array.from({ length: cols }, (_, i) => i);
  for (let i = 1; i < rows; i++) {
    const curr = [i];
    for (let j = 1; j < cols; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost);
    }
    prev = curr;
  }
  return prev[cols - 1];
}

export function suggest(input, candidates) {
  const needle = String(input).toLowerCase();
  let best = null;
  let bestScore = Infinity;
  for (const candidate of candidates) {
    const score = distance(needle, String(candidate).toLowerCase());
    if (score < bestScore) {
      bestScore = score;
      best = candidate;
    }
  }
  const threshold = Math.max(2, Math.ceil(needle.length / 2));
  return bestScore <= threshold ? best : null;
}

function notFound(message, hint) {
  return new CybError(EXIT.NOT_FOUND, message, hint);
}

function nameHint(input, names) {
  const guess = suggest(input, names);
  const list = names.join(', ');
  return guess ? `did you mean "${guess}"? valid: ${list}` : `valid: ${list}`;
}

export class Resolver {
  constructor({ client, cache, persist, now = Date.now, noCache = false }) {
    this.client = client;
    this.cache = cache;
    this.persist = persist;
    this.now = now;
    this.noCache = noCache;
  }

  stamp() {
    return new Date(this.now()).toISOString();
  }

  save() {
    this.persist?.(this.cache);
  }

  async me() {
    if (!this.noCache && this.cache.me) return this.cache.me;
    const { data } = await this.client.request('GET', '/users/me/');
    this.cache.me = { id: data.id, display_name: data.display_name };
    this.save();
    return this.cache.me;
  }

  async project(ref) {
    if (isUuid(ref)) return { id: ref, identifier: null, name: null };
    if (!ref) throw notFound('no project specified', 'pass a project or set defaultProject');

    const key = String(ref).toUpperCase();
    const cached = this.cache.projects[key];
    if (!this.noCache && cached && isFresh(cached.fetchedAt, { now: this.now })) {
      return { id: cached.id, identifier: key, name: cached.name };
    }

    const { data } = await this.client.request('GET', `${this.client.wsPath}/projects/`, {
      fields: ['id', 'identifier', 'name'],
    });
    const results = data?.results ?? [];

    for (const project of results) {
      this.cache.projects[String(project.identifier).toUpperCase()] = {
        id: project.id,
        name: project.name,
        fetchedAt: this.stamp(),
      };
    }
    this.save();

    const match = results.find((p) => String(p.identifier).toUpperCase() === key);
    if (!match) {
      const identifiers = results.map((p) => p.identifier);
      throw notFound(
        `no such project: ${ref}`,
        identifiers.length ? nameHint(ref, identifiers) : 'no projects exist yet — run: cyb project create',
      );
    }
    return { id: match.id, identifier: match.identifier, name: match.name };
  }

  async statesFor(projectId) {
    const bucket = projectBucket(this.cache, projectId);
    if (!this.noCache && bucket.stateList && isFresh(bucket.fetchedAt, { now: this.now })) {
      return bucket.stateList;
    }
    const { data } = await this.client.request('GET', `${this.client.projectPath(projectId)}/states/`, {
      fields: ['id', 'name', 'group'],
    });
    const states = data?.results ?? [];
    bucket.stateList = states;
    bucket.states = {};
    for (const state of states) bucket.states[state.name.toLowerCase()] = state.id;
    bucket.fetchedAt = this.stamp();
    this.save();
    return states;
  }

  async state(projectId, name) {
    const states = await this.statesFor(projectId);
    const hit = states.find((s) => s.name.toLowerCase() === String(name).toLowerCase());
    if (!hit) {
      throw notFound(`no such state: ${name}`, nameHint(name, states.map((s) => s.name)));
    }
    return hit.id;
  }

  async label(projectId, name) {
    const bucket = projectBucket(this.cache, projectId);
    const key = String(name).toLowerCase();
    if (!this.noCache && bucket.labels[key]) return bucket.labels[key];

    const { data } = await this.client.request('GET', `${this.client.projectPath(projectId)}/labels/`, {
      fields: ['id', 'name'],
    });
    const labels = data?.results ?? [];
    bucket.labels = {};
    for (const label of labels) bucket.labels[label.name.toLowerCase()] = label.id;
    this.save();

    if (!bucket.labels[key]) {
      throw notFound(`no such label: ${name}`, nameHint(name, labels.map((l) => l.name)));
    }
    return bucket.labels[key];
  }

  async member(name) {
    const key = String(name).toLowerCase();
    this.cache.members ??= {};
    if (!this.noCache && this.cache.members[key]) return this.cache.members[key];

    const { data } = await this.client.request('GET', `${this.client.wsPath}/members/`);
    const members = data?.results ?? data ?? [];
    this.cache.members = {};
    for (const member of members) {
      if (member.display_name) this.cache.members[member.display_name.toLowerCase()] = member.id;
      if (member.email) this.cache.members[member.email.toLowerCase()] = member.id;
    }
    this.save();

    if (!this.cache.members[key]) {
      const names = members.map((m) => m.display_name).filter(Boolean);
      throw notFound(`no such member: ${name}`, nameHint(name, names));
    }
    return this.cache.members[key];
  }

  async item(ref) {
    if (isUuid(ref)) return { id: ref, projectId: null, sequence_id: null };

    const parsed = parseItemRef(ref);
    if (!parsed) {
      throw notFound(`unrecognised work item: ${ref}`, 'use the CYB-42 form, or a UUID');
    }

    const project = await this.project(parsed.identifier);
    const bucket = projectBucket(this.cache, project.id);

    if (!this.noCache && bucket.items[parsed.sequence]) {
      return { id: bucket.items[parsed.sequence], projectId: project.id, sequence_id: parsed.sequence };
    }

    const path = `${this.client.projectPath(project.id)}/issues/`;

    const filtered = await this.client.request('GET', path, {
      query: { sequence_id: parsed.sequence },
      fields: ['id', 'sequence_id'],
    });
    const narrowed = filtered.data?.results ?? [];
    if (narrowed.length === 1 && narrowed[0].sequence_id === parsed.sequence) {
      bucket.items[parsed.sequence] = narrowed[0].id;
      this.save();
      return { id: narrowed[0].id, projectId: project.id, sequence_id: parsed.sequence };
    }

    for await (const item of this.client.paginate(path, { fields: ['id', 'sequence_id'] })) {
      bucket.items[item.sequence_id] = item.id;
    }
    this.save();

    const found = bucket.items[parsed.sequence];
    if (!found) throw notFound(`no such work item: ${ref}`, `run: cyb item list ${parsed.identifier}`);
    return { id: found, projectId: project.id, sequence_id: parsed.sequence };
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/resolve.test.mjs`
Expected: PASS — 15 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/resolve.mjs \
        .claude/skills/cybernetics/tests/resolve.test.mjs
git commit -m "feat(cyb): add name-to-UUID resolver with caching and suggestion hints"
```

---

### Task 6: Output Formatter

**Files:**
- Create: `.claude/skills/cybernetics/src/format.mjs`
- Test: `.claude/skills/cybernetics/tests/format.test.mjs`

**Interfaces:**
- Consumes: `CybError` from `src/errors.mjs`
- Produces:
  - `pickMode({ json, isTTY }) -> 'json' | 'table' | 'plain'`
  - `renderTable(rows, columns, { mode }) -> string` where `columns` is `Array<{ key, label, width? }>`
  - `truncationNotice(shown, total, limit) -> string | null`
  - `renderError(err, { mode }) -> string`
  - `emit(value, { mode, columns, stdout }) -> void`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/format.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pickMode, renderTable, truncationNotice, renderError } from '../src/format.mjs';
import { CybError, EXIT } from '../src/errors.mjs';

const COLUMNS = [
  { key: 'ref', label: 'REF' },
  { key: 'state', label: 'STATE' },
  { key: 'name', label: 'NAME' },
];

test('pickMode prefers json whenever --json is set', () => {
  assert.equal(pickMode({ json: true, isTTY: true }), 'json');
  assert.equal(pickMode({ json: true, isTTY: false }), 'json');
});

test('pickMode selects table on a TTY and plain otherwise', () => {
  assert.equal(pickMode({ json: false, isTTY: true }), 'table');
  assert.equal(pickMode({ json: false, isTTY: false }), 'plain');
});

test('renderTable aligns columns in plain mode', () => {
  const out = renderTable(
    [
      { ref: 'CYB-1', state: 'Todo', name: 'Short' },
      { ref: 'CYB-42', state: 'In Progress', name: 'Longer name' },
    ],
    COLUMNS,
    { mode: 'plain' },
  );
  const lines = out.split('\n');
  assert.match(lines[0], /^REF\s+STATE\s+NAME$/);
  assert.equal(lines[1].indexOf('Todo'), lines[2].indexOf('In Progress'));
});

test('renderTable emits no ANSI escapes in plain mode', () => {
  const out = renderTable([{ ref: 'CYB-1', state: 'Todo', name: 'x' }], COLUMNS, { mode: 'plain' });
  // eslint-disable-next-line no-control-regex
  assert.ok(!/\[/.test(out));
});

test('renderTable handles an empty row set', () => {
  assert.equal(renderTable([], COLUMNS, { mode: 'plain' }), '(no results)');
});

test('renderTable renders missing values as a dash', () => {
  const out = renderTable([{ ref: 'CYB-1' }], COLUMNS, { mode: 'plain' });
  assert.match(out, /CYB-1\s+-\s+-/);
});

test('truncationNotice appears only when results were withheld', () => {
  assert.equal(truncationNotice(30, 77, 30), '… 47 more (--limit 100)');
  assert.equal(truncationNotice(12, 12, 30), null);
  assert.equal(truncationNotice(30, 30, 30), null);
});

test('renderError yields the JSON envelope in json mode', () => {
  const err = new CybError(EXIT.NOT_FOUND, 'no such project: ZZZ', 'run: cyb project list');
  assert.deepEqual(JSON.parse(renderError(err, { mode: 'json' })), {
    error: { code: 3, message: 'no such project: ZZZ', hint: 'run: cyb project list' },
  });
});

test('renderError yields a human line with the hint in plain mode', () => {
  const err = new CybError(EXIT.NOT_FOUND, 'no such project: ZZZ', 'run: cyb project list');
  const out = renderError(err, { mode: 'plain' });
  assert.match(out, /no such project: ZZZ/);
  assert.match(out, /run: cyb project list/);
});

test('renderError copes with a plain Error', () => {
  const out = renderError(new Error('boom'), { mode: 'plain' });
  assert.match(out, /boom/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/format.test.mjs`
Expected: FAIL — `Cannot find module '../src/format.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/format.mjs`:

```js
import { styleText } from 'node:util';

export function pickMode({ json = false, isTTY = false } = {}) {
  if (json) return 'json';
  return isTTY ? 'table' : 'plain';
}

function cell(row, column) {
  const value = row[column.key];
  if (value === undefined || value === null || value === '') return '-';
  return String(value);
}

export function renderTable(rows, columns, { mode = 'plain' } = {}) {
  if (!rows.length) return '(no results)';

  const widths = columns.map((column) =>
    Math.max(column.label.length, ...rows.map((row) => cell(row, column).length)),
  );

  const pad = (text, width, isLast) => (isLast ? text : text.padEnd(width));

  const header = columns
    .map((column, i) => pad(column.label, widths[i], i === columns.length - 1))
    .join('  ');

  const body = rows.map((row) =>
    columns.map((column, i) => pad(cell(row, column), widths[i], i === columns.length - 1)).join('  '),
  );

  const headerLine = mode === 'table' ? styleText('bold', header) : header;
  return [headerLine, ...body].join('\n');
}

export function truncationNotice(shown, total, limit) {
  if (total <= shown) return null;
  const more = total - shown;
  return `… ${more} more (--limit ${Math.max(limit * 2, 100)})`;
}

export function renderError(err, { mode = 'plain' } = {}) {
  const payload =
    typeof err?.toJSON === 'function'
      ? err.toJSON()
      : { error: { code: 1, message: String(err?.message ?? err), hint: null } };

  if (mode === 'json') return JSON.stringify(payload);

  const { message, hint } = payload.error;
  const label = mode === 'table' ? styleText('red', 'error:') : 'error:';
  return hint ? `${label} ${message}\n  hint: ${hint}` : `${label} ${message}`;
}

export function emit(value, { mode = 'plain', columns, stdout = process.stdout } = {}) {
  if (mode === 'json') {
    stdout.write(`${JSON.stringify(value, null, 2)}\n`);
    return;
  }
  if (Array.isArray(value) && columns) {
    stdout.write(`${renderTable(value, columns, { mode })}\n`);
    return;
  }
  stdout.write(`${typeof value === 'string' ? value : JSON.stringify(value, null, 2)}\n`);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/format.test.mjs`
Expected: PASS — 10 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/format.mjs \
        .claude/skills/cybernetics/tests/format.test.mjs
git commit -m "feat(cyb): add three-mode output formatter with truncation notices"
```

---

### Task 7: CLI Router and `doctor`

**Files:**
- Create: `.claude/skills/cybernetics/src/cli.mjs`
- Create: `.claude/skills/cybernetics/src/commands/doctor.mjs`
- Test: `.claude/skills/cybernetics/tests/cli.test.mjs`
- Test: `.claude/skills/cybernetics/tests/doctor.test.mjs`

**Interfaces:**
- Consumes: everything from Tasks 1–6
- Produces:
  - `GLOBAL_OPTIONS` — the `parseArgs` option schema shared by every command
  - `REGISTRY` — `{ [group]: { [action]: { options, positionals, summary, handler } } }`
  - `buildContext({ argv, env, cwd, deps }) -> ctx` where `ctx = { config, client, resolver, cache, mode, values, positionals, save }`
  - `main(argv, deps) -> Promise<number>` returning the process exit code
  - `renderHelp(group, action) -> string`
  - `doctor(ctx) -> Promise<void>` and `PROBE_TARGETS` from `commands/doctor.mjs`

Phase 2 registers additional groups by adding entries to `REGISTRY`; the router itself needs no change.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/cli.test.mjs`:

```js
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
```

Create `.claude/skills/cybernetics/tests/doctor.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { main } from '../src/cli.mjs';
import { PROBE_TARGETS, probeCapabilities } from '../src/commands/doctor.mjs';
import { Client } from '../src/client.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';

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

test('PROBE_TARGETS covers the endpoints recorded in the spec', () => {
  const names = PROBE_TARGETS.map((t) => t.name);
  for (const expected of ['issues', 'states', 'labels', 'cycles', 'modules', 'members']) {
    assert.ok(names.includes(expected), `missing probe target: ${expected}`);
  }
});

test('every probe target declares a workspace or project scope', () => {
  for (const target of PROBE_TARGETS) {
    assert.ok(['workspace', 'project'].includes(target.scope), `bad scope on ${target.name}`);
  }
});

test('probeCapabilities skips project-scoped targets when no project exists', async () => {
  const workspaceTargets = PROBE_TARGETS.filter((t) => t.scope === 'workspace');
  const { fetchImpl, calls } = makeFakeFetch(
    workspaceTargets.map(() => ({ status: 200, body: { results: [] } })),
  );
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const observed = await probeCapabilities(client, null);
  assert.equal(calls.length, workspaceTargets.length);
  assert.equal(observed.members, 200);
  assert.equal(observed.issues, undefined);
});

test('probeCapabilities records the failing status instead of throwing', async () => {
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { results: [] } },
    { status: 404, body: {} },
  ]);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const observed = await probeCapabilities(client, null);
  assert.equal(observed.members, 200);
  assert.equal(observed.pages, 404);
});

test('doctor --probe reports observed capability statuses', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
    { status: 200, body: { results: [] } },
    { status: 200, body: { results: [] } },
  ]);
  await main(['doctor', '--probe', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  const report = JSON.parse(s.outText());
  assert.equal(report.capabilities.members, 200);
});

test('doctor reports identity, workspace and a token fingerprint only', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ]);
  const code = await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  assert.equal(code, 0);
  const report = JSON.parse(s.outText());
  assert.equal(report.workspace, 'cybernetics');
  assert.equal(report.user.display_name, 'avarile');
  assert.equal(report.token, 'plane_api_…beef');
  assert.ok(!s.outText().includes('ffffffffffff'));
});

test('doctor reports the project count it observed', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 3, results: [] } },
  ]);
  await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_ffffffffffffffffffffffffffffbeef' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  assert.equal(JSON.parse(s.outText()).projects, 3);
});

test('doctor surfaces an auth failure as exit code 4', async () => {
  const s = captureStreams();
  const { fetchImpl } = makeFakeFetch([{ status: 401, body: { detail: 'bad token' } }]);
  const code = await main(['doctor', '--json'], {
    streams: s,
    env: { CYB_TOKEN: 'plane_api_wrong' },
    cwd: '/nonexistent-cyb-dir',
    configPath: '/nonexistent-cyb-dir/config.json',
    fetchImpl,
    cachePath: '/nonexistent-cyb-dir/cache.json',
    sleep: async () => {},
  });
  assert.equal(code, 4);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/cli.test.mjs tests/doctor.test.mjs`
Expected: FAIL — `Cannot find module '../src/cli.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/commands/doctor.mjs`:

```js
import { fingerprint } from '../config.mjs';
import { emit } from '../format.mjs';

export const PROBE_TARGETS = [
  { name: 'members', scope: 'workspace', path: (c) => `${c.wsPath}/members/` },
  { name: 'pages', scope: 'workspace', path: (c) => `${c.wsPath}/pages/` },
  { name: 'issues', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/issues/` },
  { name: 'states', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/states/` },
  { name: 'labels', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/labels/` },
  { name: 'cycles', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/cycles/` },
  { name: 'modules', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/modules/` },
];

// Records the observed HTTP status per endpoint so the agent never spends calls
// on a resource this fork does not serve. Project-scoped targets are skipped
// when the workspace has no project to probe against.
export async function probeCapabilities(client, projectId) {
  const observed = {};
  for (const target of PROBE_TARGETS) {
    if (target.scope === 'project' && !projectId) continue;
    try {
      const { status } = await client.request('GET', target.path(client, projectId), {
        query: { per_page: 1 },
      });
      observed[target.name] = status;
    } catch (err) {
      observed[target.name] = err.status ?? 0;
    }
  }
  return observed;
}

export async function doctor(ctx) {
  const { client, resolver, config, mode, streams, values } = ctx;

  const user = await resolver.me();
  const { data } = await client.request('GET', `${client.wsPath}/projects/`, {
    fields: ['id', 'identifier'],
  });

  const report = {
    baseUrl: config.baseUrl,
    workspace: config.workspace,
    token: fingerprint(config.token),
    user: { id: user.id, display_name: user.display_name },
    projects: data?.total_count ?? 0,
    rateLimit: { remaining: client.remaining, resetAt: client.resetAt },
    calls: client.callCount,
  };

  if (values?.probe) {
    const firstProject = data?.results?.[0]?.id ?? null;
    report.capabilities = await probeCapabilities(client, firstProject);
    ctx.cache.capabilities = report.capabilities;
    report.calls = client.callCount;
  }

  ctx.cache.capabilities = {
    ...ctx.cache.capabilities,
    checkedAt: new Date().toISOString(),
  };
  ctx.save();

  if (mode === 'json') {
    emit(report, { mode, stdout: streams.stdout });
    return;
  }

  const lines = [
    `instance   ${report.baseUrl}`,
    `workspace  ${report.workspace}`,
    `token      ${report.token}`,
    `user       ${report.user.display_name}`,
    `projects   ${report.projects}`,
    `rate       ${report.rateLimit.remaining ?? '?'} remaining`,
  ];
  if (report.capabilities) {
    lines.push('capabilities');
    for (const [name, status] of Object.entries(report.capabilities)) {
      lines.push(`  ${name.padEnd(10)} ${status}`);
    }
  }
  streams.stdout.write(`${lines.join('\n')}\n`);
}
```

Create `.claude/skills/cybernetics/src/cli.mjs`:

```js
import { parseArgs } from 'node:util';
import { loadConfig, CONFIG_PATH } from './config.mjs';
import { loadCache, saveCache, CACHE_PATH } from './cache.mjs';
import { Client } from './client.mjs';
import { Resolver } from './resolve.mjs';
import { pickMode, renderError } from './format.mjs';
import { CybError, EXIT } from './errors.mjs';
import { doctor } from './commands/doctor.mjs';

export const GLOBAL_OPTIONS = {
  json: { type: 'boolean', default: false },
  full: { type: 'boolean', default: false },
  limit: { type: 'string' },
  yes: { type: 'boolean', default: false },
  project: { type: 'string' },
  'no-cache': { type: 'boolean', default: false },
  verbose: { type: 'boolean', default: false },
  help: { type: 'boolean', default: false },
};

export const REGISTRY = {
  doctor: {
    __default: {
      summary: 'Check auth, workspace access and rate-limit budget',
      options: { probe: { type: 'boolean', default: false } },
      handler: doctor,
    },
  },
};

export function renderHelp(group, action) {
  if (!group) {
    const lines = ['Usage: cyb <group> <action> [options]', '', 'Groups:'];
    for (const [name, actions] of Object.entries(REGISTRY)) {
      const summary = actions.__default?.summary ?? Object.keys(actions).join(', ');
      lines.push(`  ${name.padEnd(10)} ${summary}`);
    }
    lines.push('', 'Global options:');
    for (const flag of Object.keys(GLOBAL_OPTIONS)) lines.push(`  --${flag}`);
    lines.push('', 'Run `cyb <group> --help` for actions.');
    return lines.join('\n');
  }

  const actions = REGISTRY[group];
  if (!actions) return `unknown command group: ${group}`;

  const lines = [`Usage: cyb ${group} <action> [options]`, '', 'Actions:'];
  for (const [name, def] of Object.entries(actions)) {
    const label = name === '__default' ? '(default)' : name;
    lines.push(`  ${label.padEnd(12)} ${def.summary ?? ''}`);
  }
  if (action && actions[action]?.options) {
    lines.push('', `Options for ${group} ${action}:`);
    for (const flag of Object.keys(actions[action].options)) lines.push(`  --${flag}`);
  }
  return lines.join('\n');
}

export function buildContext({ values, positionals, deps }) {
  const env = deps.env ?? process.env;
  const cwd = deps.cwd ?? process.cwd();
  const streams = deps.streams ?? { stdout: process.stdout, stderr: process.stderr };

  const config = loadConfig({ env, cwd, configPath: deps.configPath ?? CONFIG_PATH });
  if (values.project) config.defaultProject = values.project;

  if (!config.token) {
    throw new CybError(
      EXIT.AUTH,
      'no API token configured',
      'set CYB_TOKEN, or run: cyb init',
    );
  }

  const client = new Client({
    baseUrl: config.baseUrl,
    workspace: config.workspace,
    token: config.token,
    fetchImpl: deps.fetchImpl ?? globalThis.fetch,
    verbose: Boolean(values.verbose),
    logStream: streams.stderr,
    ...(deps.sleep ? { sleep: deps.sleep } : {}),
  });

  const cachePath = deps.cachePath ?? CACHE_PATH;
  const cache = loadCache({ path: cachePath, workspace: config.workspace });
  const save = () => {
    try {
      saveCache(cache, { path: cachePath });
    } catch {
      // A read-only cache location must never fail a command.
    }
  };

  const resolver = new Resolver({ client, cache, persist: save, noCache: values['no-cache'] });

  const mode = pickMode({ json: values.json, isTTY: Boolean(streams.stdout.isTTY) });

  return { config, client, cache, resolver, save, mode, streams, values, positionals };
}

export async function main(argv, deps = {}) {
  const streams = deps.streams ?? { stdout: process.stdout, stderr: process.stderr };
  const jsonFlag = argv.includes('--json');

  try {
    const [group, ...rest] = argv;

    if (!group || group === '--help' || group === 'help') {
      streams.stdout.write(`${renderHelp()}\n`);
      return EXIT.OK;
    }

    const actions = REGISTRY[group];
    if (!actions) {
      throw new CybError(
        EXIT.GENERAL,
        `unknown command group: ${group}`,
        `valid groups: ${Object.keys(REGISTRY).join(', ')}`,
      );
    }

    const maybeAction = rest[0];
    const usesDefault = Boolean(actions.__default) && (!maybeAction || maybeAction.startsWith('-'));
    const actionName = usesDefault ? '__default' : maybeAction;
    const argsForParse = usesDefault ? rest : rest.slice(1);

    const definition = actions[actionName];
    if (!definition) {
      throw new CybError(
        EXIT.GENERAL,
        `unknown action: ${group} ${maybeAction}`,
        `valid actions: ${Object.keys(actions).filter((k) => k !== '__default').join(', ') || '(none)'}`,
      );
    }

    const { values, positionals } = parseArgs({
      args: argsForParse,
      options: { ...GLOBAL_OPTIONS, ...(definition.options ?? {}) },
      allowPositionals: true,
    });

    if (values.help) {
      streams.stdout.write(`${renderHelp(group, usesDefault ? undefined : actionName)}\n`);
      return EXIT.OK;
    }

    const ctx = buildContext({ values, positionals, deps: { ...deps, streams } });
    await definition.handler(ctx);
    return EXIT.OK;
  } catch (err) {
    const mode = jsonFlag ? 'json' : 'plain';
    streams.stderr.write(`${renderError(err, { mode })}\n`);
    return typeof err?.code === 'number' ? err.code : EXIT.GENERAL;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/cli.test.mjs tests/doctor.test.mjs`
Expected: PASS — 16 tests

- [ ] **Step 5: Run the whole Phase 1 suite**

Run: `cd .claude/skills/cybernetics && node --test`
Expected: PASS — 91 tests across 8 files, no network access required

- [ ] **Step 6: Verify `doctor` against the live instance**

Run:
```bash
cd .claude/skills/cybernetics
CYB_TOKEN='<the real token>' node bin/cyb doctor
```
Expected output shape (project count may differ):
```
instance   https://projects.avarile.com
workspace  cybernetics
token      plane_api_…ab76
user       avarile
projects   0
rate       58 remaining
```
Confirm the full token never appears. If this fails with exit 4, the token is wrong or expired; if it fails with exit 3, the workspace slug is wrong.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/src/commands/doctor.mjs \
        .claude/skills/cybernetics/tests/cli.test.mjs \
        .claude/skills/cybernetics/tests/doctor.test.mjs
git commit -m "feat(cyb): add CLI router with global flags and working doctor command"
```

---

## Phase 1 Exit Criteria

- `node --test` passes with no network and no `CYB_TOKEN`.
- `cyb doctor` authenticates against the live instance and prints identity, workspace, project count and rate budget.
- The token appears nowhere in output except as a fingerprint.
- `REGISTRY` is ready for Phase 2 to extend with no router changes.

Phase 2 (`docs/superpowers/plans/2026-08-17-cybernetics-phase-2-commands.md`) builds the command surface on these interfaces.
