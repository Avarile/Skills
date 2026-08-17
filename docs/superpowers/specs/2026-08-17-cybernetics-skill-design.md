# Cybernetics Project Skill — Design

**Date:** 2026-08-17
**Status:** Approved for planning
**Target:** `https://projects.avarile.com` (Plane fork, workspace `cybernetics`)

## Goal

One zero-dependency Node CLI (`cyb`) that is the sole interface to the remote
Cybernetics instance, wrapped by a Claude Code skill. Two audiences share one
tested code path: the agent invokes `cyb` with `--json`, the human types `cyb`
interactively.

## Why not MCP

Plane's MCP server exposes 28 tools / 183 actions, loading roughly 50k tokens of
schema into every request. A CLI plus `SKILL.md` costs ~3KB, and only when
triggered. MCP also cannot serve the human-facing requirement.

---

## Verified environment

Probed 2026-08-17 by creating a scratch project, introspecting, and deleting it
(delete returned 204; workspace verified back to 0 projects).

| Property | Value |
|---|---|
| Version | v2.6.3 (upstream latest v3.1.0), `PLANE_COMMERCIAL`, self-managed |
| API base | `/api/v1` — `/api` is internal session auth, returns 401 for API keys |
| Auth | `X-Api-Key` header only; `Authorization: Bearer` returns 401 |
| Rate limit | 60 req/min, via `x-ratelimit-remaining` / `x-ratelimit-reset` |
| Workspace | `cybernetics` (not discoverable via API — must be configured) |
| Projects | 0 at design time; greenfield |
| Members | 2, both role 20 (admin) |

### Endpoint availability

Present: `states`, `labels`, `members`, `cycles`, `modules`, `intake-issues`,
`pages`, and per-item `comments`, `links`, `activities`.

Absent (404): `estimates`, `views`, `issue-properties`, `archived-issues`,
`attachments`, `sub-issues`, `issue-relation`, `inbox-issues`.

Gated: `issue-types` → 402 (unlicensed); `initiatives`, `teamspaces` → 403.

### Behavioural findings

- `/issues/` and `/work-items/` both return 200. `/issues/` is canonical here;
  `/work-items/` is a documented alias.
- **`?fields=id,name` works** — returns exactly 2 keys instead of 31. Field
  projection is load-bearing, not an optimisation.
- `?expand=`, `?per_page=`, `?order_by=` all accepted.
- `sequence_id` exists on work items, enabling `CYB-42` references.
- Default states: Backlog (`backlog`, default), Todo (`unstarted`),
  In Progress (`started`), Done (`completed`), Cancelled (`cancelled`).
- `priority` is a strict enum; invalid values return 400.
- Sub-items are expressed via the `parent` field, not a `/sub-issues/` endpoint.

---

## Architecture

```
.claude/skills/cybernetics/
├── SKILL.md              # agent entry (~3KB)
├── README.md             # human docs
├── package.json          # {"type":"module"}, zero deps, bin: cyb
├── bin/cyb               # #!/usr/bin/env node shim
├── src/
│   ├── cli.mjs           # subcommand router + parseArgs
│   ├── client.mjs        # auth · retry · rate-limit · pagination
│   ├── resolve.mjs       # name→UUID resolver + cache
│   ├── config.mjs        # credential precedence
│   ├── format.mjs        # table / json / compact renderers
│   ├── repl.mjs          # `cyb ui`
│   └── commands/*.mjs    # one file per resource group
├── references/
│   ├── api-surface.md
│   ├── recipes.md
│   └── troubleshooting.md
└── tests/
```

Every file stays under 500 lines. `src/commands/*` depend on `client`,
`resolve`, and `format`; nothing else reaches the network.

---

## Components

### `config.mjs`

Token precedence, highest first:

1. `CYB_TOKEN` environment variable
2. `~/.cybernetics/config.json` (mode 0600, **outside the repo**)
3. `.env` in cwd (already gitignored)

`CYB_BASE_URL` and `CYB_WORKSPACE` override their config counterparts.

```jsonc
// ~/.cybernetics/config.json
{
  "baseUrl": "https://projects.avarile.com",
  "workspace": "cybernetics",
  "token": "plane_api_…",
  "defaultProject": "CYB",
  "defaults": { "limit": 30 }
}
```

The token is never written to the repo, never logged, and never printed.
`cyb doctor` displays a fingerprint only (`plane_api_…ab76`). Writing
`config.json` creates the directory 0700 and the file 0600.

### `client.mjs`

```js
client.request(method, path, { body, query, fields, expand, timeout })
  → { status, data, headers }
client.paginate(path, { query, fields, limit })
  → AsyncIterable<item>   // follows next_cursor, stops at limit
```

- Injects `X-Api-Key`; sets `Content-Type` only when a body is present.
- Tracks `x-ratelimit-remaining`. Below 5, waits until `x-ratelimit-reset`.
- Retries 429 (honouring reset) and 5xx (exponential backoff, max 3 attempts).
  4xx other than 429 never retries.
- 30s timeout via `AbortController`.
- Throws `ApiError { status, body, path }` on non-2xx.

### `resolve.mjs` — the centrepiece

Plane is UUID-only, so a naive status change costs four round trips against a
60/min budget. The resolver collapses that to one.

```js
resolveProject(ref)        // "CYB" | uuid  → { id, identifier, name }
resolveItem(ref)           // "CYB-42" | uuid → { id, projectId, sequence_id }
resolveState(projectId, name)   // "In Progress" (case-insensitive) → uuid
resolveLabel(projectId, name)
resolveMember(name)        // display_name | email → uuid
```

Cache at `~/.cybernetics/cache.json`:

```jsonc
{
  "version": 1,
  "workspace": "cybernetics",
  "me": { "id": "uuid", "display_name": "avarile" },
  "capabilities": { "estimates": false, "issueTypes": 402, "issues": true },
  "projects": { "CYB": { "id": "uuid", "name": "…", "fetchedAt": "…" } },
  "byProject": {
    "<project-uuid>": {
      "states":  { "in progress": "uuid" },
      "labels":  { "bug": "uuid" },
      "members": { "avarile": "uuid" },
      "items":   { "42": "uuid" },
      "fetchedAt": "…"
    }
  }
}
```

Rules:

- Metadata (states, labels, members) TTL 15 minutes. Items cached opportunistically
  from any list call.
- Miss → fetch with `?fields=` projection → cache → return.
- A 404 against a cached UUID triggers exactly one refresh-and-retry, then fails.
- Ambiguous name match → error listing candidates. Unknown name → error with
  nearest-match suggestions.
- `CYB-42` resolution attempts `?sequence_id=42` first; if the API ignores the
  filter (result count ≠ 1), falls back to a paginated `?fields=id,sequence_id`
  scan and caches the whole map.
- `cyb sync` forces a full refresh.

### `format.mjs`

Three modes, selected automatically:

| Mode | Trigger | Output |
|---|---|---|
| JSON | `--json` | JSON on stdout, nothing else |
| Table | TTY | aligned, coloured via `node:util` `styleText` |
| Plain | non-TTY | aligned, no colour |

Default list rows are one line, ~60 chars:

```
CYB-42  In Progress  high  Fix auth timeout
```

Fetched with `?fields=id,sequence_id,name,state,priority`. Default limit **30**.
Truncation is never silent — output ends with `… 47 more (--limit 100)`.
`--full` opts into all fields.

### `repl.mjs`

`cyb ui` — `node:readline` with a completer, persistent project context:

```
cyb:CYB> ls --state todo
cyb:CYB> open 42
cyb:CYB> mv 42 "In Progress"
cyb:CYB> cd OTHER
cyb:CYB> <TAB>     → item ids, state names, label names, members
```

Commands: `ls`, `open`, `new`, `mv`, `assign`, `cd`, `board`, `help`, `exit`.
Completion sources come from the resolver cache, so it costs no extra calls.
History via readline's built-in buffer.

---

## Command surface

| Group | Commands |
|---|---|
| Setup | `doctor`, `init`, `sync` |
| Projects | `project list\|show\|create\|update\|delete` |
| Items | `item list\|show\|create\|update\|delete\|move\|assign` |
| Metadata | `state list`, `label list\|create`, `member list` |
| Planning | `cycle list\|create\|add-item`, `module list\|create\|add-item` |
| Discussion | `comment list\|add` |
| Composite | `board`, `my`, `search` |
| Interactive | `ui` |

Composite commands exist so the agent makes one call instead of looping — the
primary defence of the rate budget.

- `board CYB` — items grouped by state group, one pass, counts per column.
- `my` — items assigned to the token's user; uses cached `me.id`.
- `search <query>` — no server-side search endpoint confirmed in v2.6.3, so this
  fetches with `?fields=` projection and filters client-side. More calls, always
  works. If a server-side filter is discovered during implementation, prefer it.

`cycle add-item CYB-42 --cycle "Sprint 1"` assigns an existing work item to a
cycle; `module add-item` behaves the same for modules. Neither creates items.

Global flags: `--json`, `--full`, `--limit N`, `--yes`, `--project CYB`
(overrides `defaultProject`), `--no-cache`, `--verbose`.

---

## Safety envelope

Read, create, and update proceed without prompting.

Gated behind `--yes`: `project delete`, `item delete`, `label delete`,
`cycle delete`, `module delete`, and any bulk update touching more than 10 items.
Without `--yes` these print the plan of what *would* change and exit 2 without
calling the API.

`SKILL.md` instructs the agent to confirm with the user before any gated
operation, independent of the flag.

## Error handling

| Exit | Meaning |
|---|---|
| 0 | success |
| 1 | general error |
| 2 | refused — safety gate, needs `--yes` |
| 3 | not found / unresolvable reference |
| 4 | auth failure |
| 5 | rate limited after retries exhausted |

Errors go to stderr. Under `--json`, stderr receives
`{"error": {"code", "message", "hint"}}` so the agent can parse failures.
Messages name the offending reference and suggest a fix — an unresolvable
`--state` lists the project's valid states rather than echoing a 400.

## Capability manifest

The availability table above ships as data in `references/api-surface.md` and is
mirrored into the cache, so the agent never spends calls on endpoints this fork
lacks. `cyb doctor` re-probes and refreshes it, guarding against fork and
version drift.

---

## SKILL.md structure

Progressive disclosure across three levels:

1. **Frontmatter** — `name`, `description` carrying trigger words: Cybernetics,
   Plane, project, task, work item, sprint, backlog, `projects.avarile.com`.
2. **Body (~3KB)** — quick start, the eight most common commands, the output
   contract, the safety rules, and the instruction to run `cyb doctor` first when
   anything looks wrong.
3. **`references/`** — loaded on demand: full endpoint map, recipes for common
   multi-step workflows, troubleshooting.

The body must state explicitly: use `--json` for parsing; default limits exist
and `--limit` is deliberate; confirm before destructive operations; prefer
`board`/`my`/`search` over looping.

## Testing

Built on `node:test` (zero dependency).

- **Unit, no network** — resolver hit/miss/ambiguity, config precedence, arg
  parsing, formatter modes, exit-code mapping.
- **Integration** — creates a scratch project, exercises CRUD, deletes it in a
  `finally`, mirroring the design probe. Skipped unless `CYB_TOKEN` is present
  and `CYB_RUN_INTEGRATION=1`, so a token-less CI run stays green.

## Non-goals

- Attachments, estimates, views, issue-properties, archived-issues, sub-issue
  and relation endpoints — absent on this instance.
- Intake triage. `intake-issues` is present and returned 200, but no command
  covers it in this iteration; it is deferred rather than unavailable, and the
  capability manifest records it as present so a later version can add it.
- Issue types (402), initiatives and teamspaces (403).
- OAuth / `Bearer` auth — rejected by this instance.
- A general-purpose Plane client. This targets one instance at one version.

## Risks

| Risk | Mitigation |
|---|---|
| Fork or upgrade changes endpoints | Runtime capability probe via `cyb doctor`; nothing hardcoded beyond defaults |
| 60 req/min ceiling | Resolver cache, field projection, composite commands, budget-aware client |
| Agent context blowout on large lists | Default limit 30, one-line rows, explicit truncation notice |
| Token leakage into a public repo | Credentials live outside the repo; fingerprint-only display; `.env` gitignored |
| `sequence_id` filter unsupported | Documented fallback to projected scan |

## Follow-up

The API token used during design was shared in conversation and should be
rotated in Plane once implementation is complete.
