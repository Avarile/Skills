import { emit, truncationNotice, renderTable } from '../format.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';
import { projectBucket } from '../cache.mjs';

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
  const { data } = await ctx.client.request('GET', path, {
    query: { ...query, per_page: limit },
    fields: ctx.values.full ? undefined : LIST_FIELDS,
  });

  const raw = data?.results ?? [];
  const total = data?.total_count ?? raw.length;

  const bucket = projectBucket(ctx.cache, project.id);
  for (const item of raw) bucket.items[item.sequence_id] = item.id;
  ctx.save();

  if (ctx.mode === 'json') {
    emit(decorate(raw, { project, states }), { mode: ctx.mode, stdout: ctx.streams.stdout });
    return;
  }

  const rows = decorate(raw, { project, states });
  ctx.streams.stdout.write(`${renderTable(rows, ITEM_COLUMNS, { mode: ctx.mode })}\n`);
  const notice = truncationNotice(rows.length, total, limit);
  if (notice) ctx.streams.stdout.write(`${notice}\n`);
}

export async function show(ctx) {
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb item show CYB-42');

  const item = await ctx.resolver.item(ref);
  const { data } = await ctx.client.request(
    'GET',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/`,
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
