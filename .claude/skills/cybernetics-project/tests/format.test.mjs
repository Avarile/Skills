import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pickMode, renderTable, truncationNotice, renderError, emit } from '../src/format.mjs';
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
  assert.ok(!/\[/.test(out));
});

test('renderTable handles an empty row set', () => {
  assert.equal(renderTable([], COLUMNS, { mode: 'plain' }), '(no results)');
});

test('renderTable renders missing values as a dash', () => {
  const out = renderTable([{ ref: 'CYB-1' }], COLUMNS, { mode: 'plain' });
  assert.match(out, /CYB-1\s+-\s+-/);
});

test('truncationNotice appears only when results were withheld', () => {
  assert.equal(truncationNotice(30, 77, 30), '… 47 more (--limit 77)');
  assert.equal(truncationNotice(12, 12, 30), null);
  assert.equal(truncationNotice(30, 30, 30), null);
});

test('truncationNotice suggests a limit that reveals every withheld row', () => {
  assert.equal(truncationNotice(30, 500, 30), '… 470 more (--limit 500)');
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

function fakeStdout() {
  const writes = [];
  return { writes, write: (s) => writes.push(s) };
}

test('emit writes valid JSON of the value to stdout in json mode, and nothing else', () => {
  const stdout = fakeStdout();
  const value = { ref: 'CYB-1', state: 'Todo', nested: { count: 2 }, items: [1, 2, 3] };
  emit(value, { mode: 'json', stdout });
  assert.equal(stdout.writes.length, 1);
  assert.deepEqual(JSON.parse(stdout.writes[0]), value);
});

test('emit writes a rendered table with headers and row values in plain mode', () => {
  const stdout = fakeStdout();
  const rows = [{ ref: 'CYB-1', state: 'Todo', name: 'Short' }];
  emit(rows, { mode: 'plain', columns: COLUMNS, stdout });
  assert.equal(stdout.writes.length, 1);
  const out = stdout.writes.join('');
  assert.match(out, /REF\s+STATE\s+NAME/);
  assert.match(out, /CYB-1\s+Todo\s+Short/);
});
