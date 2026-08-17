import { emit } from '../format.mjs';
import { projectRef } from './item.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const PLANNING_COLUMNS = [
  { key: 'name', label: 'NAME' },
  { key: 'start_date', label: 'START' },
  { key: 'end_date', label: 'END' },
  { key: 'id', label: 'ID' },
];

async function collectionList(ctx, kind) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/${kind}/`);
  return { project, rows: data?.results ?? [] };
}

async function findByName(ctx, projectId, kind, name) {
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(projectId)}/${kind}/`, {
    fields: ['id', 'name'],
  });
  const rows = data?.results ?? [];
  const hit = rows.find((r) => String(r.name).toLowerCase() === String(name).toLowerCase());
  if (!hit) {
    throw new CybError(
      EXIT.NOT_FOUND,
      `no such ${kind.replace(/s$/, '')}: ${name}`,
      rows.length ? `valid: ${rows.map((r) => r.name).join(', ')}` : `no ${kind} exist yet`,
    );
  }
  return hit;
}

export async function cycleList(ctx) {
  const { rows } = await collectionList(ctx, 'cycles');
  emit(rows, { mode: ctx.mode, columns: PLANNING_COLUMNS, stdout: ctx.streams.stdout });
}

export async function cycleCreate(ctx) {
  // Purely local check, hoisted above the resolver's `project()` call below
  // (a real GET on a cold cache) — see item.mjs's `create()` and
  // task-10-review.md's Important finding. Invalid input must be rejected
  // client-side before any request is issued.
  if (!ctx.values.name) {
    throw new CybError(
      EXIT.GENERAL,
      'cycle needs a name',
      'pass --name, e.g. cyb cycle create CYB --name "Sprint 1" --start 2026-08-01 --end 2026-08-14',
    );
  }

  const project = await ctx.resolver.project(projectRef(ctx));

  const body = { name: ctx.values.name };
  if (ctx.values.start) body.start_date = ctx.values.start;
  if (ctx.values.end) body.end_date = ctx.values.end;

  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/cycles/`,
    { body },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function cycleAddItem(ctx) {
  if (!ctx.values.cycle) {
    throw new CybError(
      EXIT.GENERAL,
      'no cycle given',
      'pass --cycle, e.g. cyb cycle add-item CYB-42 --cycle "Sprint 1"',
    );
  }
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb cycle add-item CYB-42 --cycle "Sprint 1"');

  const item = await ctx.resolver.item(ref);
  const cycle = await findByName(ctx, item.projectId, 'cycles', ctx.values.cycle);

  await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(item.projectId)}/cycles/${cycle.id}/cycle-issues/`,
    { body: { issues: [item.id] } },
  );
  emit({ added: ref, cycle: cycle.name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function cycleRemove(ctx) {
  // Local positional check first, same reasoning as cycleCreate above.
  const name = ctx.positionals[1];
  if (!name) throw new CybError(EXIT.GENERAL, 'no cycle given', 'example: cyb cycle delete CYB "Sprint 1" --yes');

  const project = await ctx.resolver.project(projectRef(ctx));
  const cycle = await findByName(ctx, project.id, 'cycles', name);
  requireConfirmation(ctx, { action: 'delete cycle', targets: [name] });

  await ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/cycles/${cycle.id}/`);
  emit({ deleted: name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function moduleList(ctx) {
  const { rows } = await collectionList(ctx, 'modules');
  emit(rows, { mode: ctx.mode, columns: PLANNING_COLUMNS, stdout: ctx.streams.stdout });
}

export async function moduleCreate(ctx) {
  // Purely local check, hoisted above the resolver call — see cycleCreate.
  if (!ctx.values.name) {
    throw new CybError(EXIT.GENERAL, 'module needs a name', 'pass --name, e.g. cyb module create CYB --name Auth');
  }

  const project = await ctx.resolver.project(projectRef(ctx));

  const body = { name: ctx.values.name };
  if (ctx.values.description) body.description = ctx.values.description;

  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/modules/`,
    { body },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function moduleAddItem(ctx) {
  if (!ctx.values.module) {
    throw new CybError(
      EXIT.GENERAL,
      'no module given',
      'pass --module, e.g. cyb module add-item CYB-42 --module Auth',
    );
  }
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb module add-item CYB-42 --module Auth');

  const item = await ctx.resolver.item(ref);
  const mod = await findByName(ctx, item.projectId, 'modules', ctx.values.module);

  await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(item.projectId)}/modules/${mod.id}/module-issues/`,
    { body: { issues: [item.id] } },
  );
  emit({ added: ref, module: mod.name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function moduleRemove(ctx) {
  // Local positional check first, same reasoning as moduleCreate above.
  const name = ctx.positionals[1];
  if (!name) throw new CybError(EXIT.GENERAL, 'no module given', 'example: cyb module delete CYB Auth --yes');

  const project = await ctx.resolver.project(projectRef(ctx));
  const mod = await findByName(ctx, project.id, 'modules', name);
  requireConfirmation(ctx, { action: 'delete module', targets: [name] });

  await ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/modules/${mod.id}/`);
  emit({ deleted: name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
