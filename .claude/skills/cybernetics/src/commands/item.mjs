import { emit, truncationNotice, emitNotice, renderTable } from '../format.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';
import { projectBucket } from '../cache.mjs';
import { parseItemRef } from '../resolve.mjs';
import { escapeHtml } from '../html.mjs';

export const PRIORITIES = Object.freeze(['urgent', 'high', 'medium', 'low', 'none']);

export const LIST_FIELDS = ['id', 'sequence_id', 'name', 'state', 'priority', 'assignees'];

export const ITEM_COLUMNS = [
  { key: 'ref', label: 'REF' },
  { key: 'state', label: 'STATE' },
  { key: 'priority', label: 'PRIO' },
  { key: 'name', label: 'NAME' },
];

export function decorate(items, { project, states }) {
  const byId = new Map(states.map((s) => [s.id, s.name]));
  return items.map((item) => ({
    ref: project.identifier ? `${project.identifier}-${item.sequence_id}` : String(item.sequence_id),
    state: byId.get(item.state) ?? item.state,
    priority: item.priority,
    name: item.name,
    id: item.id,
    sequence_id: item.sequence_id,
    assignees: item.assignees,
  }));
}

export function projectRef(ctx) {
  const ref = ctx.positionals[0] ?? ctx.values.project ?? ctx.config.defaultProject;
  if (!ref) {
    throw new CybError(EXIT.GENERAL, 'no project given', 'pass a project key, e.g. cyb item list CYB');
  }
  return ref;
}

export function limitOf(ctx) {
  const raw = ctx.values.limit ?? ctx.config.defaults.limit;
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    throw new CybError(EXIT.GENERAL, `invalid --limit: ${raw}`, 'pass a positive integer');
  }
  return value;
}

export function validatePriority(priority) {
  if (priority === undefined) return undefined;
  if (!PRIORITIES.includes(priority)) {
    throw new CybError(
      EXIT.GENERAL,
      `invalid priority: ${priority}`,
      `valid: ${PRIORITIES.join(', ')}`,
    );
  }
  return priority;
}

export async function list(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  const limit = limitOf(ctx);

  const query = {};
  if (ctx.values.state) query.state = await ctx.resolver.state(project.id, ctx.values.state);
  if (ctx.values.priority) query.priority = validatePriority(ctx.values.priority);
  if (ctx.values.assignee) query.assignees = await ctx.resolver.member(ctx.values.assignee);

  const path = `${ctx.client.projectPath(project.id)}/issues/`;
  // Page up to `limit` rather than sending it as a single `per_page` — the
  // client's own paginate() clamps each request to PAGE_CEILING, so a
  // single request can silently return fewer rows than --limit asked for
  // even when more exist. Paging costs more requests for a large --limit,
  // but it's the only way the result can actually reach it (Important 7).
  let total = null;
  const raw = [];
  for await (const item of ctx.client.paginate(path, {
    query,
    fields: ctx.values.full ? undefined : LIST_FIELDS,
    limit,
    onPage: (data) => { if (data?.total_count !== undefined) total = data.total_count; },
  })) {
    raw.push(item);
  }
  total = total ?? raw.length;

  const bucket = projectBucket(ctx.cache, project.id);
  for (const item of raw) bucket.items[item.sequence_id] = item.id;
  // Stamp freshness alongside the mapping write, matching how the resolver
  // stamps its own regions (resolve.mjs). Without this, `bucket.items` is
  // populated but `resolver.item()`'s cache-hit check — gated on
  // `isFresh(bucket.itemsFetchedAt, ...)` — reads every entry as stale, so
  // a `list()` immediately followed by `show()` on a listed item would
  // still hit the network. The mapping only pays for itself if freshness
  // is recorded.
  bucket.itemsFetchedAt = ctx.resolver.stamp();
  ctx.save();

  const rows = decorate(raw, { project, states });
  const notice = truncationNotice(rows.length, total, limit);

  if (ctx.mode === 'json') {
    // Stdout stays a bare, parseable array — every other command and every
    // existing test depends on that uniform shape. The truncation signal
    // goes to stderr instead, so an agent piping `--json` output straight
    // into a parser still gets a clean array, but withheld rows are never
    // silent: they're on stderr, not swallowed.
    emit(rows, { mode: ctx.mode, stdout: ctx.streams.stdout });
    emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
    return;
  }

  ctx.streams.stdout.write(`${renderTable(rows, ITEM_COLUMNS, { mode: ctx.mode })}\n`);
  emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
}

// `resolver.item()` returns `projectId: null` for a raw UUID ref — it can't
// know an item's project without an extra request (resolve.mjs). Building
// `client.projectPath(null)` from that would silently produce a
// `/projects/null/issues/...` URL, so fall back to an explicit project
// (`--project` or the configured default) and resolve it, or fail with a
// clear hint rather than sending a request that can't succeed.
export async function resolveItemProjectId(ctx, item) {
  if (item.projectId) return item.projectId;
  const ref = ctx.values.project ?? ctx.config.defaultProject;
  if (!ref) {
    throw new CybError(
      EXIT.GENERAL,
      'cannot determine the project for a raw work item UUID',
      'pass --project — the API is project-scoped and cannot be inferred from a UUID alone',
    );
  }
  const project = await ctx.resolver.project(ref);
  return project.id;
}

function itemRef(ctx, index = 0) {
  const ref = ctx.positionals[index];
  if (!ref) {
    throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb item show CYB-42');
  }
  return ref;
}

// A cached item UUID can be stale — the work item may have been deleted in the
// web UI since we cached it. Resolve, act, and on a 404 drop the mapping and
// retry exactly once against a freshly-resolved UUID. Every mutating command
// (and `show`) routes through this so the spec's "a 404 against a cached UUID
// triggers exactly one refresh-and-retry, then fails" holds everywhere a
// cached item id is used, not just in the resolver primitives.
export async function mutateItem(ctx, ref, act) {
  return ctx.resolver.withCachedRetry(
    () => ctx.resolver.item(ref),
    act,
    () => {
      const parsed = parseItemRef(ref);
      if (parsed) {
        const project = ctx.cache.projects[parsed.identifier];
        if (project) ctx.resolver.invalidate('item', project.id, parsed.sequence);
      }
    },
  );
}

export async function show(ctx) {
  const ref = itemRef(ctx);
  return mutateItem(ctx, ref, async (item) => {
    const projectId = await resolveItemProjectId(ctx, item);
    const { data } = await ctx.client.request(
      'GET',
      `${ctx.client.projectPath(projectId)}/issues/${item.id}/`,
    );
    emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
    return data;
  });
}

export async function buildItemBody(ctx, { project }) {
  const body = {};

  if (ctx.values.name) body.name = ctx.values.name;
  if (ctx.values.description) body.description_html = `<p>${escapeHtml(ctx.values.description)}</p>`;

  const priority = validatePriority(ctx.values.priority);
  if (priority !== undefined) body.priority = priority;

  if (ctx.values.state) body.state = await ctx.resolver.state(project.id, ctx.values.state);

  if (ctx.values.assignee) {
    body.assignees = [await ctx.resolver.member(ctx.values.assignee)];
  }
  if (ctx.values.label) {
    body.labels = [await ctx.resolver.label(project.id, ctx.values.label)];
  }
  if (ctx.values.parent) {
    body.parent = (await ctx.resolver.item(ctx.values.parent)).id;
  }
  if (ctx.values['target-date']) body.target_date = ctx.values['target-date'];
  if (ctx.values['start-date']) body.start_date = ctx.values['start-date'];

  return body;
}

export async function create(ctx) {
  // Both checks are purely local (no project/item context needed), so they
  // must run before the resolver's `project()` call below, which is a real
  // GET on a cold cache. Invalid input has to be rejected client-side before
  // any request is issued — see task-10-review.md's Important finding.
  if (!ctx.values.name) {
    throw new CybError(
      EXIT.GENERAL,
      'work item needs a name',
      'pass --name, e.g. cyb item create CYB --name "Fix auth"',
    );
  }
  validatePriority(ctx.values.priority);

  const project = await ctx.resolver.project(projectRef(ctx));

  const body = await buildItemBody(ctx, { project });
  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/issues/`,
    { body },
  );

  const bucket = projectBucket(ctx.cache, project.id);
  bucket.items[data.sequence_id] = data.id;
  ctx.save();

  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function update(ctx) {
  const ref = itemRef(ctx);
  // Purely local check, hoisted above `mutateItem` so a bad --priority is
  // rejected before the item-resolution GET it would otherwise trigger on a
  // cold cache. `buildItemBody`'s own call below stays — it's not just
  // validation, it also produces the body's `priority` field.
  validatePriority(ctx.values.priority);
  return mutateItem(ctx, ref, async (item) => {
    const projectId = await resolveItemProjectId(ctx, item);
    const body = await buildItemBody(ctx, { project: { id: projectId } });
    if (!Object.keys(body).length) {
      throw new CybError(
        EXIT.GENERAL,
        'nothing to update',
        'pass at least one of --name --state --priority --assignee --label --description',
      );
    }

    const { data } = await ctx.client.request(
      'PATCH',
      `${ctx.client.projectPath(projectId)}/issues/${item.id}/`,
      { body },
    );
    emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
    return data;
  });
}

export async function move(ctx) {
  const stateName = ctx.positionals[1];
  if (!stateName) {
    throw new CybError(
      EXIT.GENERAL,
      'no target state given',
      'example: cyb item move CYB-42 "In Progress"',
    );
  }
  const ref = itemRef(ctx);
  return mutateItem(ctx, ref, async (item) => {
    const projectId = await resolveItemProjectId(ctx, item);
    const state = await ctx.resolver.state(projectId, stateName);

    const { data } = await ctx.client.request(
      'PATCH',
      `${ctx.client.projectPath(projectId)}/issues/${item.id}/`,
      { body: { state } },
    );
    emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
    return data;
  });
}

export async function assign(ctx) {
  const who = ctx.positionals[1];
  if (!who) {
    throw new CybError(EXIT.GENERAL, 'no assignee given', 'example: cyb item assign CYB-42 avarile');
  }
  const ref = itemRef(ctx);
  return mutateItem(ctx, ref, async (item) => {
    const projectId = await resolveItemProjectId(ctx, item);
    const member = await ctx.resolver.member(who);

    const { data } = await ctx.client.request(
      'PATCH',
      `${ctx.client.projectPath(projectId)}/issues/${item.id}/`,
      { body: { assignees: [member] } },
    );
    emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
    return data;
  });
}

export async function remove(ctx) {
  const ref = itemRef(ctx);
  return mutateItem(ctx, ref, async (item) => {
    const projectId = await resolveItemProjectId(ctx, item);
    requireConfirmation(ctx, { action: 'delete work item', targets: [ref] });

    await ctx.client.request(
      'DELETE',
      `${ctx.client.projectPath(projectId)}/issues/${item.id}/`,
    );

    const bucket = projectBucket(ctx.cache, projectId);
    delete bucket.items[item.sequence_id];
    ctx.save();

    emit({ deleted: ref }, { mode: ctx.mode, stdout: ctx.streams.stdout });
  });
}
