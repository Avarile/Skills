import { emit } from '../format.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const PROJECT_COLUMNS = [
  { key: 'identifier', label: 'KEY' },
  { key: 'name', label: 'NAME' },
  { key: 'id', label: 'ID' },
];

const IDENTIFIER_MAX = 10;

function requiredProject(ctx) {
  const ref = ctx.positionals[0] ?? ctx.values.project ?? ctx.config.defaultProject;
  if (!ref) {
    throw new CybError(EXIT.GENERAL, 'no project given', 'pass a project key, e.g. cyb project show CYB');
  }
  return ref;
}

export async function list(ctx) {
  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/projects/`, {
    fields: ctx.values.full ? undefined : ['id', 'identifier', 'name'],
  });
  const rows = data?.results ?? [];
  emit(rows, { mode: ctx.mode, columns: PROJECT_COLUMNS, stdout: ctx.streams.stdout });
}

export async function show(ctx) {
  const project = await ctx.resolver.project(requiredProject(ctx));
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/`);
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function create(ctx) {
  const name = ctx.values.name;
  const identifier = ctx.values.identifier;

  if (!name || !identifier) {
    throw new CybError(
      EXIT.GENERAL,
      'project create needs --name and --identifier',
      'example: cyb project create --name "Core" --identifier CYB',
    );
  }
  if (identifier.length > IDENTIFIER_MAX) {
    throw new CybError(
      EXIT.GENERAL,
      `identifier must be at most ${IDENTIFIER_MAX} characters`,
      `"${identifier}" is ${identifier.length}`,
    );
  }

  const body = { name, identifier: identifier.toUpperCase() };
  if (ctx.values.description) body.description = ctx.values.description;

  const { data } = await ctx.client.request('POST', `${ctx.client.wsPath}/projects/`, { body });

  ctx.cache.projects[body.identifier] = {
    id: data.id,
    name: data.name,
    fetchedAt: new Date().toISOString(),
  };
  ctx.save();

  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

// Cache.projects is keyed by uppercased identifier, but a UUID ref resolves
// to `{ identifier: null }` (resolve.mjs) — deleting `cache.projects[key]`
// for a null-derived key is a no-op and leaves a since-deleted project's
// identifier -> uuid mapping behind (Important 5). Key the cleanup off the
// id actually acted on instead, so it works regardless of which ref form
// was used to name the project.
function forgetProject(ctx, projectId) {
  for (const [key, entry] of Object.entries(ctx.cache.projects)) {
    if (entry?.id === projectId) delete ctx.cache.projects[key];
  }
}

export async function update(ctx) {
  const ref = requiredProject(ctx);
  const project = await ctx.resolver.project(ref);
  const body = {};
  if (ctx.values.name) body.name = ctx.values.name;
  if (ctx.values.description) body.description = ctx.values.description;

  if (!Object.keys(body).length) {
    throw new CybError(EXIT.GENERAL, 'nothing to update', 'pass --name or --description');
  }

  // A cached project uuid can be stale; route through the same
  // refresh-and-retry contract items already have (Important 5).
  const { data } = await ctx.resolver.withCachedRetry(
    () => ctx.resolver.project(ref),
    (resolved) => ctx.client.request('PATCH', `${ctx.client.projectPath(resolved.id)}/`, { body }),
    () => ctx.resolver.invalidate('project', null, ref),
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function remove(ctx) {
  const ref = requiredProject(ctx);
  const project = await ctx.resolver.project(ref);

  requireConfirmation(ctx, {
    action: 'delete project (this destroys all its work items)',
    targets: [project.identifier ?? project.id],
  });

  // Track the id the DELETE actually succeeds against — on a stale-uuid
  // retry (Important 5) that can differ from `project.id` above, and the
  // cache cleanup below must key off whichever id was really deleted.
  let deletedId = project.id;
  await ctx.resolver.withCachedRetry(
    () => ctx.resolver.project(ref),
    (resolved) => {
      deletedId = resolved.id;
      return ctx.client.request('DELETE', `${ctx.client.projectPath(resolved.id)}/`);
    },
    () => ctx.resolver.invalidate('project', null, ref),
  );

  forgetProject(ctx, deletedId);
  delete ctx.cache.byProject[deletedId];
  ctx.save();

  emit({ deleted: project.identifier ?? project.id }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
