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
  404: 'record may be gone (try: cyb sync, or --no-cache) or the endpoint may not exist on this instance (try: cyb doctor)',
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
