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
  return `… ${more} more (--limit ${total})`;
}

// The one place that decides *where* a notice goes: stderr in JSON mode (so
// stdout stays a clean, parseable payload), inline on stdout otherwise. Every
// command that can silently withhold information — `item.list()`'s
// `--limit` truncation, `board`'s single-page fetch, `my`'s project-scan cap,
// `search`'s scan cap — must route through this instead of re-deciding the
// channel itself, so the convention can't drift between call sites.
export function emitNotice(notice, { mode = 'plain', stdout = process.stdout, stderr = process.stderr } = {}) {
  if (!notice) return;
  if (mode === 'json') stderr.write(`${notice}\n`);
  else stdout.write(`${notice}\n`);
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
