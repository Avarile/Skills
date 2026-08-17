// board / my / search exist so that "what's the state of this project?" or
// "what's assigned to me?" costs one pass, not one request per resource.
// This instance allows 60 req/min and every other command surface here is
// per-resource, so these three are the primary defence of that budget — the
// request cost of each is a correctness property, not an optimisation.
import { emit, renderTable, truncationNotice, emitNotice } from '../format.mjs';
import { decorate, LIST_FIELDS, ITEM_COLUMNS, projectRef, limitOf } from './item.mjs';
import { CybError, EXIT } from '../errors.mjs';

const GROUP_ORDER = ['backlog', 'unstarted', 'started', 'completed', 'cancelled'];

// A hard cap on how many issues `search` will scan client-side. No
// server-side search endpoint is confirmed on this v2.6.3 fork, so matching
// happens locally over a fetched page window — this cap is what stops a
// large project from burning the 60 req/min budget on a single search.
// Deliberately fixed: don't raise it, and don't add a smaller/implicit cap
// either. Narrow with --project (already required) rather than widen it.
const SEARCH_SCAN_CAP = 500;

// A hard cap on how many projects `my` will fan out to. Without one, a
// workspace where the current user is assigned to few or no items (the
// sparse case — the one that actually stresses the budget, since the
// rows-accumulated bailout never fires) issues one issues-request per
// project with no upper bound: 1 (me) + 1 (project list) + P. Fixed
// independent of --limit, which governs how many *rows* come back, not how
// many *projects* get scanned.
export const MY_PROJECT_SCAN_CAP = 15;

export function groupByState(rows, states) {
  const ordered = [...states].sort(
    (a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group),
  );
  const byId = new Map(ordered.map((s) => [s.id, s.name]));

  // Every known state gets a bucket up front, including one with zero items.
  // Omitting an empty column would misrepresent the project — "nothing in
  // Cancelled" and "we don't know about Cancelled" are different facts, and
  // a board is exactly the place that distinction matters.
  const grouped = {};
  for (const state of ordered) grouped[state.name] = [];

  for (const row of rows) {
    const name = byId.get(row.state) ?? row.state;
    grouped[name] ??= [];
    grouped[name].push(row);
  }
  return grouped;
}

export async function board(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  const limit = limitOf(ctx);
  const perPage = Math.max(limit, 100);

  // One request for the entire project. This is the whole point of `board`:
  // an agent asking "what's the state of this project?" pays once, not once
  // per state and not once per item. That single-page fetch can still fall
  // short of the project's real size, though — same tradeoff `item.list()`
  // already makes for the same endpoint — so the incompleteness has to be
  // surfaced the same way `list()` does rather than silently dropped.
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/issues/`, {
    query: { per_page: perPage },
    fields: LIST_FIELDS,
  });

  const raw = data?.results ?? [];
  const total = data?.total_count ?? raw.length;
  const notice = truncationNotice(raw.length, total, perPage);
  const grouped = groupByState(raw, states);

  const decorated = {};
  for (const [name, items] of Object.entries(grouped)) {
    decorated[name] = decorate(items, { project, states });
  }

  if (ctx.mode === 'json') {
    emit(decorated, { mode: ctx.mode, stdout: ctx.streams.stdout });
    emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
    return;
  }

  const lines = [];
  for (const [name, items] of Object.entries(decorated)) {
    lines.push(`${name} (${items.length})`);
    for (const row of items) lines.push(`  ${row.ref}  ${row.name}`);
    lines.push('');
  }
  ctx.streams.stdout.write(`${lines.join('\n').trimEnd()}\n`);
  emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
}

export async function my(ctx) {
  const me = await ctx.resolver.me();
  const limit = limitOf(ctx);

  // No endpoint on this fork reports "issues assigned to me" across the
  // whole workspace in one shot, so the project list is the fan-out point:
  // one request to learn which projects exist, then one issues request per
  // project. That cost is bounded by project count, not by how many items
  // any one project holds.
  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/projects/`, {
    fields: ['id', 'identifier', 'name'],
  });
  const projects = data?.results ?? [];

  // Cap the fan-out at a fixed number of projects, independent of --limit.
  // --limit bounds how many *rows* come back, which only helps once matches
  // are found — in the sparse case (assigned to few or none of a large
  // workspace's projects) `rows.length` never reaches it, so that bailout
  // alone doesn't stop the loop from touching every project. This cap does.
  const scanned = projects.slice(0, MY_PROJECT_SCAN_CAP);
  const skipped = projects.length - scanned.length;

  const rows = [];
  for (const project of scanned) {
    if (rows.length >= limit) break;

    const page = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/issues/`, {
      query: { assignees: me.id, per_page: limit },
      fields: LIST_FIELDS,
    });
    // `assignees` above is an optimisation, not a guarantee of correctness —
    // if this fork ignores the query param the response comes back
    // unfiltered. The local filter on the returned `assignees` array is what
    // actually makes the result correct regardless of server behaviour, so
    // both stay even though that looks redundant.
    const mine = (page.data?.results ?? []).filter(
      (item) => Array.isArray(item.assignees) && item.assignees.includes(me.id),
    );

    // Deliberately not a `resolver.statesFor` call: that would cost one more
    // request per project just to turn a state UUID into its label. Read
    // from cache only if some earlier command already warmed it for this
    // project; otherwise `decorate` falls back to the raw UUID. A cosmetic
    // label is not worth a request in a command whose entire reason to
    // exist is minimising requests.
    const states = ctx.cache.byProject[project.id]?.stateList ?? [];
    rows.push(...decorate(mine, { project, states }));
  }

  const trimmed = rows.slice(0, limit);
  const notice = skipped > 0
    ? `… ${skipped} more project${skipped === 1 ? '' : 's'} not scanned (project cap ${MY_PROJECT_SCAN_CAP})`
    : null;

  if (ctx.mode === 'json') {
    emit(trimmed, { mode: ctx.mode, stdout: ctx.streams.stdout });
    emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
    return;
  }
  ctx.streams.stdout.write(`${renderTable(trimmed, ITEM_COLUMNS, { mode: ctx.mode })}\n`);
  emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
}

export async function search(ctx) {
  // Locally-checkable first, before any resolver or network call — a
  // missing query must fail with zero requests. Task 10's review found the
  // opposite ordering once already and it was fixed there; it must not come
  // back here.
  const query = ctx.positionals[0];
  if (!query) {
    throw new CybError(EXIT.GENERAL, 'no search query given', 'example: cyb search "auth" --project CYB');
  }

  // `ctx.positionals[0]` is the query text here, not the project — unlike
  // every other command, where positional[0] is the project ref that
  // `projectRef` reads directly. Shift it off before delegating, so the
  // project can only come from --project or the configured default.
  const project = await ctx.resolver.project(
    projectRef({ ...ctx, positionals: ctx.positionals.slice(1) }),
  );
  const states = await ctx.resolver.statesFor(project.id);
  const limit = limitOf(ctx);
  const needle = query.toLowerCase();

  // `scanned` tracks how many items were actually examined, separately from
  // how many matched — without it there's no way to tell "the cap was hit
  // with more of the project left unscanned" apart from "the project simply
  // has fewer than the cap", and a rare-term match past position 500 would
  // come back as zero results with no hint that only the first 500 were
  // ever looked at.
  //
  // The request asks for one item past the cap (`SEARCH_SCAN_CAP + 1`), same
  // over-fetch-by-one used by `resolve.mjs`'s sequence scan
  // (`SEQUENCE_SCAN_LIMIT + 1` / `scanned > SEQUENCE_SCAN_LIMIT`). A project
  // with exactly `SEARCH_SCAN_CAP` items then naturally exhausts its pages
  // before that extra item is ever requested, so `scanned` stays at or below
  // the cap — the "fully scanned, nothing left" case is distinguishable from
  // "cap hit, more left unscanned" instead of both looking identical.
  let scanned = 0;
  const matches = [];
  for await (const item of ctx.client.paginate(`${ctx.client.projectPath(project.id)}/issues/`, {
    fields: LIST_FIELDS,
    limit: SEARCH_SCAN_CAP + 1,
  })) {
    scanned++;
    if (String(item.name).toLowerCase().includes(needle)) matches.push(item);
    if (matches.length >= limit) break;
  }

  const rows = decorate(matches, { project, states });
  // `scanned` can only exceed the cap if the extra (cap + 1)th item was
  // actually fetched, which only happens when the project has more left
  // after the cap — a project that ends exactly at the cap never reaches it.
  const notice = scanned > SEARCH_SCAN_CAP
    ? `… scan cap of ${SEARCH_SCAN_CAP} items reached before the project was fully scanned`
    : null;

  if (ctx.mode === 'json') {
    emit(rows, { mode: ctx.mode, stdout: ctx.streams.stdout });
    emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
    return;
  }
  ctx.streams.stdout.write(`${renderTable(rows, ITEM_COLUMNS, { mode: ctx.mode })}\n`);
  emitNotice(notice, { mode: ctx.mode, stdout: ctx.streams.stdout, stderr: ctx.streams.stderr });
}
