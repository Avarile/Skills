import { projectBucket, isFresh } from './cache.mjs';
import { ApiError, CybError, EXIT } from './errors.mjs';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ITEM_REF_RE = /^([A-Za-z][A-Za-z0-9]*)-(\d+)$/;
const SEQUENCE_SCAN_LIMIT = 2000;

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
    if (!this.noCache && bucket.stateList && isFresh(bucket.statesFetchedAt, { now: this.now })) {
      return bucket.stateList;
    }
    const { data } = await this.client.request('GET', `${this.client.projectPath(projectId)}/states/`, {
      fields: ['id', 'name', 'group'],
    });
    const states = data?.results ?? [];
    bucket.stateList = states;
    bucket.states = {};
    for (const state of states) bucket.states[state.name.toLowerCase()] = state.id;
    bucket.statesFetchedAt = this.stamp();
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
    if (!this.noCache && bucket.labels[key] && isFresh(bucket.labelsFetchedAt, { now: this.now })) {
      return bucket.labels[key];
    }

    const { data } = await this.client.request('GET', `${this.client.projectPath(projectId)}/labels/`, {
      fields: ['id', 'name'],
    });
    const labels = data?.results ?? [];
    bucket.labels = {};
    for (const label of labels) bucket.labels[label.name.toLowerCase()] = label.id;
    bucket.labelsFetchedAt = this.stamp();
    this.save();

    if (!bucket.labels[key]) {
      throw notFound(`no such label: ${name}`, nameHint(name, labels.map((l) => l.name)));
    }
    return bucket.labels[key];
  }

  async member(name) {
    const key = String(name).toLowerCase();
    this.cache.members ??= {};
    if (!this.noCache && this.cache.members[key] && isFresh(this.cache.membersFetchedAt, { now: this.now })) {
      return this.cache.members[key];
    }

    const { data } = await this.client.request('GET', `${this.client.wsPath}/members/`);
    const members = data?.results ?? data ?? [];
    this.cache.members = {};
    for (const member of members) {
      if (member.display_name) this.cache.members[member.display_name.toLowerCase()] = member.id;
      if (member.email) this.cache.members[member.email.toLowerCase()] = member.id;
    }
    this.cache.membersFetchedAt = this.stamp();
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

    if (
      !this.noCache &&
      bucket.items[parsed.sequence] &&
      isFresh(bucket.itemsFetchedAt, { now: this.now })
    ) {
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
      bucket.itemsFetchedAt = this.stamp();
      this.save();
      return { id: narrowed[0].id, projectId: project.id, sequence_id: parsed.sequence };
    }

    // The filter didn't narrow to exactly one match — either the server
    // ignored `?sequence_id=` (the reason the scan fallback below exists at
    // all), or the item genuinely doesn't exist. Before paying for a full
    // paginated scan, reject an obviously-impossible sequence id using the
    // cheapest signal available: the project's highest sequence id.
    const maxSequence = await this.maxSequenceFor(project.id, bucket);
    if (maxSequence !== null && parsed.sequence > maxSequence) {
      throw notFound(
        `no such work item: ${ref}`,
        `${parsed.identifier}-${maxSequence} is the highest work item in ${parsed.identifier}`,
      );
    }

    let scanned = 0;
    for await (const item of this.client.paginate(path, {
      fields: ['id', 'sequence_id'],
      limit: SEQUENCE_SCAN_LIMIT + 1,
    })) {
      bucket.items[item.sequence_id] = item.id;
      scanned++;
    }
    bucket.itemsFetchedAt = this.stamp();
    this.save();

    const found = bucket.items[parsed.sequence];
    if (!found) {
      if (scanned > SEQUENCE_SCAN_LIMIT) {
        throw notFound(
          `no such work item: ${ref}`,
          `project too large for a sequence scan (scanned ${SEQUENCE_SCAN_LIMIT} items) — pass the item's UUID directly`,
        );
      }
      throw notFound(`no such work item: ${ref}`, `run: cyb item list ${parsed.identifier}`);
    }
    return { id: found, projectId: project.id, sequence_id: parsed.sequence };
  }

  // Learns the project's highest sequence id via the cheapest possible
  // request — one page, ordered descending, projected to a single field —
  // so a plausible-looking but wrong reference (CYB-142 for a project whose
  // highest item is CYB-42) fails in one request instead of a full scan.
  // Cached per project bucket, gated by the same freshness contract as
  // states/labels/members, so repeated typos cost nothing until the TTL
  // expires.
  async maxSequenceFor(projectId, bucket) {
    if (
      !this.noCache &&
      bucket.maxSequence !== null &&
      bucket.maxSequence !== undefined &&
      isFresh(bucket.maxSequenceFetchedAt, { now: this.now })
    ) {
      return bucket.maxSequence;
    }
    const { data } = await this.client.request('GET', `${this.client.projectPath(projectId)}/issues/`, {
      query: { order_by: '-sequence_id', per_page: 1 },
      fields: ['sequence_id'],
    });
    const top = data?.results?.[0]?.sequence_id ?? null;
    bucket.maxSequence = top;
    bucket.maxSequenceFetchedAt = this.stamp();
    this.save();
    return top;
  }

  // Drops a single cached mapping so the next lookup is forced to refetch.
  // `kind` identifies which cache region owns `key`:
  //   'project' — cache.projects[key], key = uppercased identifier
  //   'item'    — byProject[projectId].items[key], key = sequence number
  //   'state'   — states are fetched and cached as one list, not a per-name
  //               slot, so there is nothing finer-grained to drop than the
  //               whole unit's freshness
  //   'label'   — byProject[projectId].labels[key], key = lowercased name
  //   'member'  — cache.members[key], key = lowercased name or email
  invalidate(kind, projectId, key) {
    switch (kind) {
      case 'project': {
        if (key !== undefined) delete this.cache.projects[String(key).toUpperCase()];
        break;
      }
      case 'item': {
        const bucket = projectBucket(this.cache, projectId);
        if (key !== undefined) delete bucket.items[key];
        break;
      }
      case 'state': {
        const bucket = projectBucket(this.cache, projectId);
        bucket.stateList = null;
        bucket.states = {};
        bucket.statesFetchedAt = null;
        break;
      }
      case 'label': {
        const bucket = projectBucket(this.cache, projectId);
        if (key !== undefined) delete bucket.labels[String(key).toLowerCase()];
        break;
      }
      case 'member': {
        this.cache.members ??= {};
        if (key !== undefined) delete this.cache.members[String(key).toLowerCase()];
        break;
      }
      default:
        throw new Error(`unknown invalidate kind: ${kind}`);
    }
    this.save();
  }

  // Runs `fn`, and if it fails with a 404 — the shape of "the cached UUID no
  // longer refers to anything" — invalidates via `onInvalidate` and retries
  // `fn` exactly once. A second failure, 404 or otherwise, propagates. Per
  // spec: "a 404 against a cached UUID triggers exactly one
  // refresh-and-retry, then fails."
  async withRefresh(fn, onInvalidate) {
    try {
      return await fn();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        await onInvalidate();
        return await fn();
      }
      throw err;
    }
  }

  // Generalises `withRefresh` to the "resolve a cached id, then act on it"
  // shape used everywhere a resolved label/state/member/project/item UUID
  // ends up in a request path. item.mjs's `mutateItem` was the original,
  // item-specific instance of exactly this pattern (resolve the item, then
  // act on it); this is that shape with the item-specific parts pulled out,
  // so labels/states/members/projects get the same refresh-and-retry
  // contract without five near-copies of `mutateItem`. `resolve()` produces
  // whatever `act()` needs; if `act()` throws a 404 (the resolved id no
  // longer refers to anything), `invalidate()` drops the stale cache entry
  // and the whole resolve+act cycle runs exactly once more before the error
  // propagates.
  async withCachedRetry(resolve, act, invalidate) {
    return this.withRefresh(async () => act(await resolve()), invalidate);
  }
}
