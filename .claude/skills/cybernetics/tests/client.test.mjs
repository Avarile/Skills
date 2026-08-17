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

test('callCount increments once per fetch attempt, including retries', async () => {
  const { client } = makeClient([
    { status: 500, body: {} },
    { status: 200, body: { ok: true } },
  ]);
  await client.request('GET', '/issues/');
  assert.equal(client.callCount, 2);
});

test('paginate stops when a page returns empty results despite next_page_results being true', async () => {
  const { client, calls } = makeClient([
    { status: 200, body: { results: [], next_page_results: true, next_cursor: 'c2' } },
  ]);
  const seen = [];
  for await (const item of client.paginate('/issues/')) seen.push(item.id);
  assert.deepEqual(seen, []);
  assert.equal(calls.length, 1);
});

test('paginate stops when next_cursor does not advance between pages', async () => {
  const { client, calls } = makeClient([
    { status: 200, body: { results: [{ id: 1 }], next_page_results: true, next_cursor: 'c2' } },
    { status: 200, body: { results: [{ id: 2 }], next_page_results: true, next_cursor: 'c2' } },
  ]);
  const seen = [];
  for await (const item of client.paginate('/issues/')) seen.push(item.id);
  assert.deepEqual(seen, [1, 2]);
  assert.equal(calls.length, 2);
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

test('a request that times out throws a CybError, not a raw AbortError', async () => {
  // A real AbortController driven by a short `timeout` — not a 30s wait —
  // so this stays fast. fetchImpl never resolves on its own; it only
  // rejects once the internal timer aborts the signal.
  const fetchImpl = (url, init) => new Promise((resolve, reject) => {
    init.signal.addEventListener('abort', () => {
      reject(new DOMException('This operation was aborted', 'AbortError'));
    });
  });
  const client = new Client({
    baseUrl: 'https://example.test',
    workspace: 'cybernetics',
    token: 'tok',
    fetchImpl,
    sleep: async () => {},
    now: () => 1_000_000,
  });
  await assert.rejects(
    () => client.request('GET', '/issues/', { timeout: 5 }),
    (err) =>
      err.name === 'CybError' &&
      err.code === 1 &&
      /timed out after 5ms on \/issues\//.test(err.message) &&
      /cyb doctor/.test(err.hint),
  );
});
