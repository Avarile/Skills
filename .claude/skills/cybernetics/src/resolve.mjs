import { projectBucket, isFresh } from './cache.mjs';
import { CybError, EXIT } from './errors.mjs';

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

    let scanned = 0;
    for await (const item of this.client.paginate(path, {
      fields: ['id', 'sequence_id'],
      limit: SEQUENCE_SCAN_LIMIT + 1,
    })) {
      bucket.items[item.sequence_id] = item.id;
      scanned++;
    }
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
}
