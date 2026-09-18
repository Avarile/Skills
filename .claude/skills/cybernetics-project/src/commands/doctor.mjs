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

// Only these statuses are a genuine, durable answer about whether an
// endpoint exists: 200 (present), 402/403 (present but gated), 404 (absent).
// Everything else — 429, 5xx, a network error, a missing status — is
// transient noise about the *request*, not a fact about the endpoint, and
// must never be written into the durable capability manifest.
const RECORDABLE_STATUSES = new Set([200, 402, 403, 404]);

// Records the observed HTTP status per endpoint so the agent never spends calls
// on a resource this fork does not serve. Project-scoped targets are skipped
// when the workspace has no project to probe against. Returns the durable
// observations separately from the set of targets whose answer was
// inconclusive, so a caller can merge `observed` without clobbering a
// previously-recorded good value for a target that just happened to blip.
export async function probeCapabilities(client, projectId) {
  const observed = {};
  const unknown = [];
  for (const target of PROBE_TARGETS) {
    if (target.scope === 'project' && !projectId) continue;
    let status;
    try {
      ({ status } = await client.request('GET', target.path(client, projectId), {
        query: { per_page: 1 },
      }));
    } catch (err) {
      status = err.status;
    }
    if (RECORDABLE_STATUSES.has(status)) {
      observed[target.name] = status;
    } else {
      unknown.push(target.name);
    }
  }
  return { observed, unknown };
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
    const { observed, unknown } = await probeCapabilities(client, firstProject);
    report.capabilities = observed;
    if (unknown.length) report.capabilitiesUnknown = unknown;
    // Merge, never replace: a probe against a workspace with no project skips
    // project-scoped targets entirely, and `observed` itself omits any
    // target whose answer was inconclusive (429/5xx/network error) — so a
    // full replace would wipe out issues/states/labels/cycles/modules
    // statuses recorded by an earlier, more conclusive probe. checkedAt only
    // moves when we actually probed — a bare `doctor` must not claim
    // freshness it didn't earn.
    ctx.cache.capabilities = {
      ...ctx.cache.capabilities,
      ...observed,
      checkedAt: new Date().toISOString(),
    };
    report.calls = client.callCount;
  }

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
    for (const name of report.capabilitiesUnknown ?? []) {
      lines.push(`  ${name.padEnd(10)} unknown/skipped`);
    }
  }
  streams.stdout.write(`${lines.join('\n')}\n`);
}
