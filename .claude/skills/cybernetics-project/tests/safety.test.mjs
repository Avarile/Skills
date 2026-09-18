import { test } from 'node:test';
import assert from 'node:assert/strict';
import { requireConfirmation, BULK_THRESHOLD } from '../src/safety.mjs';
import { EXIT } from '../src/errors.mjs';

test('BULK_THRESHOLD matches the spec', () => {
  assert.equal(BULK_THRESHOLD, 10);
});

test('requireConfirmation throws REFUSED when --yes is absent', () => {
  assert.throws(
    () => requireConfirmation({ values: {} }, { action: 'delete project', targets: ['CYB'] }),
    (err) => err.code === EXIT.REFUSED,
  );
});

test('the refusal names the action and the targets', () => {
  try {
    requireConfirmation({ values: {} }, { action: 'delete work item', targets: ['CYB-42', 'CYB-43'] });
    assert.fail('should have thrown');
  } catch (err) {
    assert.match(err.message, /delete work item/);
    assert.match(err.message, /CYB-42/);
    assert.match(err.hint, /--yes/);
  }
});

test('requireConfirmation is a no-op when --yes is present', () => {
  assert.doesNotThrow(() =>
    requireConfirmation({ values: { yes: true } }, { action: 'delete', targets: ['CYB'] }),
  );
});
