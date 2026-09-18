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
