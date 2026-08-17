import { emit } from '../format.mjs';
import { projectRef } from './item.mjs';
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

export async function stateList(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  emit(states, { mode: ctx.mode, columns: STATE_COLUMNS, stdout: ctx.streams.stdout });
}

export async function labelList(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/labels/`, {
    fields: ctx.values.full ? undefined : ['id', 'name', 'color'],
  });
  emit(data?.results ?? [], { mode: ctx.mode, columns: LABEL_COLUMNS, stdout: ctx.streams.stdout });
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
  const labelId = await ctx.resolver.label(project.id, name);
  requireConfirmation(ctx, { action: 'delete label', targets: [name] });

  await ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/labels/${labelId}/`);
  emit({ deleted: name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function memberList(ctx) {
  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/members/`);
  const members = data?.results ?? data ?? [];
  emit(members, { mode: ctx.mode, columns: MEMBER_COLUMNS, stdout: ctx.streams.stdout });
}
