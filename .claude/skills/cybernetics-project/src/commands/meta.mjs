import { emit, truncationNotice, emitNotice } from '../format.mjs';
import { projectRef, limitOf } from './item.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const STATE_COLUMNS = [
  { key: 'name', label: 'NAME' },
  { key: 'group', label: 'GROUP' },
  { key: 'id', label: 'ID' },
];

export const LABEL_COLUMNS = [
  { key: 'name', label: 'NAME' },
  { key: 'color', label: 'COLOR' },
  { key: 'id', label: 'ID' },
];

export const MEMBER_COLUMNS = [
  { key: 'display_name', label: 'NAME' },
  { key: 'role', label: 'ROLE' },
  { key: 'id', label: 'ID' },
];

// Not bounded by --limit (Important 1): `statesFor` caches and hands back
// the *complete* state list, and other resolution — `resolver.state()`'s
// name matching, its "valid: ..." not-found hint — depends on that list
// being the whole set, not a page of it. There is no server-side total to
// compare against here either; the resolver treats whatever it fetched as
// authoritative. A real work-management project's states are also a small,
// bounded set in practice, unlike labels/items/members.
export async function stateList(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  emit(states, { mode: ctx.mode, columns: STATE_COLUMNS, stdout: ctx.streams.stdout });
}

export async function labelList(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const limit = limitOf(ctx);
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/labels/`, {
    query: { per_page: limit },
    fields: ctx.values.full ? undefined : ['id', 'name', 'color'],
  });
  const rows = data?.results ?? [];
  const total = data?.total_count ?? rows.length;

  emit(rows, { mode: ctx.mode, columns: LABEL_COLUMNS, stdout: ctx.streams.stdout });
  emitNotice(truncationNotice(rows.length, total, limit), {
    mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr,
  });
}

export async function labelCreate(ctx) {
  // Purely local check, hoisted above the resolver's `project()` call below
  // (a real GET on a cold cache) — see item.mjs's `create()` and
  // task-10-review.md's Important finding. Invalid input must be rejected
  // client-side before any request is issued.
  if (!ctx.values.name) {
    throw new CybError(
      EXIT.GENERAL,
      'label needs a name',
      'pass --name, e.g. cyb label create CYB --name bug --color "#ff0000"',
    );
  }

  const project = await ctx.resolver.project(projectRef(ctx));

  const body = { name: ctx.values.name };
  if (ctx.values.color) body.color = ctx.values.color;

  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/labels/`,
    { body },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function labelRemove(ctx) {
  // Local positional check first, same reasoning as labelCreate above.
  const name = ctx.positionals[1];
  if (!name) {
    throw new CybError(EXIT.GENERAL, 'no label given', 'example: cyb label delete CYB bug --yes');
  }

  const project = await ctx.resolver.project(projectRef(ctx));
  // Resolves (or throws a proper not-found) before the confirmation gate, so
  // a bad label name never gets as far as "are you sure?".
  await ctx.resolver.label(project.id, name);
  requireConfirmation(ctx, { action: 'delete label', targets: [name] });

  // A cached label uuid can be stale (edited or deleted elsewhere inside the
  // TTL); route the DELETE through the same refresh-and-retry contract items
  // already have (Important 5) — on a 404, drop the mapping, re-resolve the
  // name, and retry exactly once before failing.
  await ctx.resolver.withCachedRetry(
    () => ctx.resolver.label(project.id, name),
    (labelId) => ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/labels/${labelId}/`),
    () => ctx.resolver.invalidate('label', project.id, name),
  );

  // The delete is also self-inflicted staleness: it just deleted the label
  // server-side, so the mapping resolved above (fresh a moment ago) is now
  // stale too. Drop it immediately rather than leaving it for the next
  // command to discover via a 400.
  ctx.resolver.invalidate('label', project.id, name);

  emit({ deleted: name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function memberList(ctx) {
  const limit = limitOf(ctx);
  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/members/`, {
    query: { per_page: limit },
  });
  const members = data?.results ?? data ?? [];
  const total = data?.total_count ?? members.length;

  emit(members, { mode: ctx.mode, columns: MEMBER_COLUMNS, stdout: ctx.streams.stdout });
  emitNotice(truncationNotice(members.length, total, limit), {
    mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr,
  });
}
