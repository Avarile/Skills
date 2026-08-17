import { saveConfig, CONFIG_PATH, fingerprint } from '../config.mjs';
import { projectBucket } from '../cache.mjs';
import { emit } from '../format.mjs';

// Non-interactive: writes whatever buildContext already resolved (env,
// .env, or a pre-existing config file) back out to disk. It never prompts
// and never prints the raw token — only saveConfig (0700 dir / 0600 file,
// chmod'd unconditionally on every write) ever sees it in full.
export async function init(ctx) {
  const configPath = ctx.configPath ?? CONFIG_PATH;

  const record = {
    baseUrl: ctx.config.baseUrl,
    workspace: ctx.config.workspace,
    token: ctx.config.token,
    defaults: { limit: ctx.config.defaults.limit },
  };
  if (ctx.config.defaultProject) record.defaultProject = ctx.config.defaultProject;

  saveConfig(record, { configPath });

  emit(
    {
      wrote: configPath,
      workspace: record.workspace,
      baseUrl: record.baseUrl,
      token: fingerprint(record.token),
      defaultProject: record.defaultProject ?? null,
    },
    { mode: ctx.mode, stdout: ctx.streams.stdout },
  );
}

// Discards and rebuilds the resolver cache: projects, per-project states,
// and workspace members. The rebuild is assembled entirely in local
// variables — nothing is written onto ctx.cache, and ctx.save() is called
// exactly once, after every fetch below has succeeded. That's why this goes
// straight through ctx.client rather than ctx.resolver: Resolver.me() and
// Resolver.statesFor() write through to the shared ctx.cache and call
// save() as a side effect of their own success, which would commit a
// half-rebuilt cache the moment the first sub-request succeeded — and if a
// later request then failed (a 404, a rate limit, a network blip), the
// on-disk cache would be left wiped for reasons unconnected to whether the
// rebuild as a whole succeeded. Building locally and committing once makes
// the operation atomic by construction: if sync throws partway, ctx.cache
// and the on-disk cache are exactly what they were before it was called.
//
// Once committed, ctx.cache's fields are mutated in place rather than
// reassigning ctx.cache itself — the resolver was constructed against this
// same object, so replacing the reference here would leave it reading and
// writing a stale copy for the rest of the process.
//
// Every region written below is stamped with the same instant so the
// resolver's freshness checks (isFresh, gated on statesFetchedAt /
// membersFetchedAt) read the just-synced cache as fresh instead of
// immediately re-fetching on the next command. The stamp comes from
// ctx.resolver's injected clock, not wall-clock time, so it lines up with
// the fake clocks tests inject elsewhere.
export async function sync(ctx) {
  const stamp = ctx.resolver.stamp();

  const { data: meData } = await ctx.client.request('GET', '/users/me/');
  const me = { id: meData.id, display_name: meData.display_name };

  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/projects/`, {
    fields: ['id', 'identifier', 'name'],
  });
  const projects = data?.results ?? [];

  const newProjects = {};
  const newByProject = {};

  // One states request per project — see the request-cost note in the task
  // report: this scales linearly with project count and can exceed the
  // 60 req/min budget on its own for a large-enough workspace.
  for (const project of projects) {
    newProjects[String(project.identifier).toUpperCase()] = {
      id: project.id,
      name: project.name,
      fetchedAt: stamp,
    };

    // projectBucket only touches the `byProject` field of whatever it's
    // given, so handing it a scratch object here gives each project the
    // same full bucket shape (labels/items/maxSequence included) that
    // resolve.mjs expects, without writing through to ctx.cache.
    const bucket = projectBucket({ byProject: newByProject }, project.id);
    const { data: statesData } = await ctx.client.request(
      'GET',
      `${ctx.client.projectPath(project.id)}/states/`,
      { fields: ['id', 'name', 'group'] },
    );
    const states = statesData?.results ?? [];
    bucket.stateList = states;
    for (const state of states) bucket.states[state.name.toLowerCase()] = state.id;
    bucket.statesFetchedAt = stamp;
  }

  const members = await ctx.client.request('GET', `${ctx.client.wsPath}/members/`);
  const memberRows = members.data?.results ?? members.data ?? [];
  const newMembers = {};
  for (const member of memberRows) {
    if (member.display_name) newMembers[member.display_name.toLowerCase()] = member.id;
    if (member.email) newMembers[member.email.toLowerCase()] = member.id;
  }

  // Every fetch above succeeded — commit the rebuild in one shot.
  ctx.cache.me = me;
  ctx.cache.projects = newProjects;
  ctx.cache.byProject = newByProject;
  ctx.cache.members = newMembers;
  ctx.cache.membersFetchedAt = stamp;
  ctx.save();

  emit(
    {
      user: me.display_name,
      projects: projects.map((p) => p.identifier),
      members: memberRows.length,
      calls: ctx.client.callCount,
    },
    { mode: ctx.mode, stdout: ctx.streams.stdout },
  );
}
