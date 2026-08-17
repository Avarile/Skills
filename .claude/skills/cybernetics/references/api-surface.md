# Cybernetics API Surface

Instance: `https://projects.avarile.com` · workspace `cybernetics` ·
self-managed Plane fork.

## Conventions

- Base path `/api/v1`. Work items live at `/issues/` — there is no separate
  `/work-items/` path on this fork.
- Auth header is `X-Api-Key`. `Authorization: Bearer` returns 401 — never use it.
- Rate limit 60 req/min, reported via `x-ratelimit-remaining` and `x-ratelimit-reset`.
- `?fields=a,b` projects the response down to those keys. The CLI sends it on
  `item list`, `project list`, and `label list` (unless `--full` is passed),
  and always on the three composites — `board`, `my`, `search` — since
  keeping those payloads small is the whole point of a composite. It does
  *not* send `fields` on `member list`, `cycle list`, `module list`, or
  `comment list` (small metadata lists, not worth projecting), nor on the two
  detail views `item show` / `project show` (a detail view returning the
  full record is the point of it).
- `?expand=`, `?per_page=`, `?order_by=`, and cursor pagination (`?cursor=`)
  are all accepted.

## Present

| Resource | Path |
|---|---|
| Projects | `/workspaces/{ws}/projects/` |
| Work items | `/workspaces/{ws}/projects/{id}/issues/` |
| States | `.../states/` |
| Labels | `.../labels/` |
| Members | `/workspaces/{ws}/members/` and `.../projects/{id}/members/` |
| Cycles | `.../cycles/`, items via `.../cycles/{id}/cycle-issues/` |
| Modules | `.../modules/`, items via `.../modules/{id}/module-issues/` |
| Comments | `.../issues/{id}/comments/` |
| Pages | `/workspaces/{ws}/pages/` |
| `/users/me/` | current-user identity, used to resolve "assigned to me" |

`cyb doctor --probe` re-checks a subset of these live (members, pages, issues,
states, labels, cycles, modules) and records the observed status in the local
cache — run it if you suspect this table has drifted from the live instance.

## Absent — returns 404, never call

`estimates`, `views`, `issue-properties`, `archived-issues`, `attachments`,
`sub-issues`, `issue-relation`, `inbox-issues`.

Sub-items are expressed through the `parent` field on a work item (see
`item create --parent`), not through a `sub-issues` endpoint.

## Gated

| Resource | Status | Meaning |
|---|---|---|
| `issue-types` | 402 | not licensed on this instance |
| `initiatives` | 403 | not available to this workspace |
| `teamspaces` | 403 | not available to this workspace |

## Field notes

- Work items carry `sequence_id`, which is what makes `CYB-42` references possible.
- Default states are Backlog (`backlog`), Todo (`unstarted`), In Progress (`started`), Done (`completed`), Cancelled (`cancelled`).
- `priority` is a strict enum: `urgent`, `high`, `medium`, `low`, `none`. Anything else is rejected client-side before a request is even sent.
- Create/update payload keys the CLI sends: `name`, `description_html` (built from `--description`, HTML-escaped), `state`, `assignees` (array), `labels` (array), `parent`, `priority`, `target_date`, `start_date`.
- Comments are sent as `comment_html`, also HTML-escaped, and read back with tags stripped for display.
- Project identifiers are capped at 10 characters on this instance.

## Refresh-and-retry on stale UUIDs

A 404 against a cached project, item, or label UUID triggers exactly one
cache invalidation and retry before the error propagates. States and members
are excluded from this: they're never a path segment, so a stale one shows up
as a 400 body-validation error on `item create`/`update` instead of a 404 —
run `cyb sync` if that happens.

Run `cyb doctor` to re-probe; the fork may drift from this table.
