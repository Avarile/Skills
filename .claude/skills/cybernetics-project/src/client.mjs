import { ApiError, CybError, EXIT } from './errors.mjs';

const MAX_ATTEMPTS = 3;
const BACKOFF_MS = [500, 1000, 2000];
const LOW_BUDGET = 5;

// The page size this API actually honours per request. `paginate` already
// clamps to it; anything that fetches a single page directly (item.mjs's
// `list`, composite.mjs's `board`) must clamp to the same value instead of
// passing --limit straight through, or it ends up sending a per_page the
// server can't satisfy and then recommending that same unusable value back
// in a truncation notice (Important 7).
export const PAGE_CEILING = 100;

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
      let timedOut = false;
      const timer = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, timeout);
      this.callCount++;
      let res;
      try {
        res = await this.fetchImpl(url, {
          method,
          headers,
          signal: controller.signal,
          ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
        });
      } catch (err) {
        // A DOMException named AbortError carries a legacy numeric `.code`
        // (20) that main's exit-code selector would otherwise mistake for a
        // CybError's own exit code. Give it a real identity here, and only
        // when *our* timer is what fired the abort — not some other cause.
        if (timedOut && err?.name === 'AbortError') {
          throw new CybError(
            EXIT.GENERAL,
            `request timed out after ${timeout}ms on ${path}`,
            'the instance may be slow or unreachable — run: cyb doctor',
          );
        }
        throw err;
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

  async *paginate(path, { query = {}, fields, limit = Infinity, onPage } = {}) {
    let cursor = null;
    let yielded = 0;

    while (yielded < limit) {
      const perPage = Math.max(1, Math.min(PAGE_CEILING, limit - yielded));
      const pageQuery = { ...query, per_page: perPage };
      if (cursor) pageQuery.cursor = cursor;

      const { data } = await this.request('GET', path, { query: pageQuery, fields });
      onPage?.(data);
      const results = data?.results ?? [];

      if (results.length === 0) return;

      for (const item of results) {
        if (yielded >= limit) return;
        yield item;
        yielded++;
      }

      if (!data?.next_page_results || !data?.next_cursor) return;
      if (data.next_cursor === cursor) return;
      cursor = data.next_cursor;
    }
  }
}
