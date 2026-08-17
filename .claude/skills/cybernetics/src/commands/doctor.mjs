import { fingerprint } from '../config.mjs';
import { emit } from '../format.mjs';

export const PROBE_TARGETS = [
  { name: 'members', scope: 'workspace', path: (c) => `${c.wsPath}/members/` },
  { name: 'pages', scope: 'workspace', path: (c) => `${c.wsPath}/pages/` },
  { name: 'issues', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/issues/` },
  { name: 'states', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/states/` },
  { name: 'labels', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/labels/` },
  { name: 'cycles', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/cycles/` },
  { name: 'modules', scope: 'project', path: (c, pid) => `${c.projectPath(pid)}/modules/` },
];

// Records the observed HTTP status per endpoint so the agent never spends calls
// on a resource this fork does not serve. Project-scoped targets are skipped
// when the workspace has no project to probe against.
export async function probeCapabilities(client, projectId) {
  const observed = {};
  for (const target of PROBE_TARGETS) {
    if (target.scope === 'project' && !projectId) continue;
    try {
      const { status } = await client.request('GET', target.path(client, projectId), {
        query: { per_page: 1 },
      });
      observed[target.name] = status;
    } catch (err) {
      observed[target.name] = err.status ?? 0;
    }
  }
  return observed;
}

export async function doctor(ctx) {
  const { client, resolver, config, mode, streams, values } = ctx;

  const user = await resolver.me();
  const { data } = await client.request('GET', `${client.wsPath}/projects/`, {
    fields: ['id', 'identifier'],
  });

  const report = {
    baseUrl: config.baseUrl,
    workspace: config.workspace,
    token: fingerprint(config.token),
    user: { id: user.id, display_name: user.display_name },
    projects: data?.total_count ?? 0,
    rateLimit: { remaining: client.remaining, resetAt: client.resetAt },
    calls: client.callCount,
  };

  if (values?.probe) {
    const firstProject = data?.results?.[0]?.id ?? null;
    report.capabilities = await probeCapabilities(client, firstProject);
    ctx.cache.capabilities = report.capabilities;
    report.calls = client.callCount;
  }

  ctx.cache.capabilities = {
    ...ctx.cache.capabilities,
    checkedAt: new Date().toISOString(),
  };
  ctx.save();

  if (mode === 'json') {
    emit(report, { mode, stdout: streams.stdout });
    return;
  }

  const lines = [
    `instance   ${report.baseUrl}`,
    `workspace  ${report.workspace}`,
    `token      ${report.token}`,
    `user       ${report.user.display_name}`,
    `projects   ${report.projects}`,
    `rate       ${report.rateLimit.remaining ?? '?'} remaining`,
  ];
  if (report.capabilities) {
    lines.push('capabilities');
    for (const [name, status] of Object.entries(report.capabilities)) {
      lines.push(`  ${name.padEnd(10)} ${status}`);
    }
  }
  streams.stdout.write(`${lines.join('\n')}\n`);
}
