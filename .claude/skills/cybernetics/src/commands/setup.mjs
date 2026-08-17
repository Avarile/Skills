import { saveConfig, CONFIG_PATH, fingerprint } from '../config.mjs';
import { emptyCache, projectBucket } from '../cache.mjs';
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
// and workspace members. Mutates ctx.cache's fields in place rather than
// reassigning ctx.cache itself — the resolver was constructed against this
// same object, so replacing the reference here would leave it reading and
// writing a stale copy for the rest of the process.
//
// Every region written below is stamped fresh so the resolver's freshness
// checks (isFresh, gated on statesFetchedAt / membersFetchedAt) read the
// just-synced cache as fresh instead of immediately re-fetching on the next
// command. The stamp comes from ctx.resolver's injected clock, not wall-clock
// time, so it lines up with the fake clocks tests inject elsewhere.
export async function sync(ctx) {
  const fresh = emptyCache(ctx.config.workspace);
  ctx.cache.projects = fresh.projects;
  ctx.cache.byProject = fresh.byProject;
  ctx.cache.members = {};
  ctx.cache.membersFetchedAt = null;
  ctx.cache.me = null;

  const me = await ctx.resolver.me();

  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/projects/`, {
    fields: ['id', 'identifier', 'name'],
  });
  const projects = data?.results ?? [];
  const stamp = ctx.resolver.stamp();

  // One states request per project — see the request-cost note in the task
  // report: this scales linearly with project count and can exceed the
  // 60 req/min budget on its own for a large-enough workspace.
  for (const project of projects) {
    ctx.cache.projects[String(project.identifier).toUpperCase()] = {
      id: project.id,
      name: project.name,
      fetchedAt: stamp,
    };
    projectBucket(ctx.cache, project.id);
    await ctx.resolver.statesFor(project.id);
  }

  const members = await ctx.client.request('GET', `${ctx.client.wsPath}/members/`);
  const memberRows = members.data?.results ?? members.data ?? [];
  ctx.cache.members = {};
  for (const member of memberRows) {
    if (member.display_name) ctx.cache.members[member.display_name.toLowerCase()] = member.id;
    if (member.email) ctx.cache.members[member.email.toLowerCase()] = member.id;
  }
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
