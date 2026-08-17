---
name: "Cybernetics Project Management"
description: "Manage projects, work items, sprints and backlogs on the remote Cybernetics instance (a Plane fork at projects.avarile.com) through the zero-dependency cyb CLI. Use when asked to create, list, update, assign, move, comment on, or search project tasks and work items; to inspect a backlog, sprint, cycle or module; or whenever Cybernetics, projects.avarile.com, or Plane project management is mentioned."
---

# Cybernetics Project Management

Manage the remote Cybernetics instance through the `cyb` CLI. Never call the
API directly with curl — the CLI handles auth, UUID resolution, rate limiting
and pagination for you.

## Invocation

`cyb` is not on PATH. Run it from the repo root:

```bash
node .claude/skills/cybernetics/bin/cyb <group> <action> [options]
```

Check the connection first if anything looks wrong:

```bash
node .claude/skills/cybernetics/bin/cyb doctor
```

Discover the surface as you go — every group answers `--help` with its
actions and argument syntax:

```bash
node .claude/skills/cybernetics/bin/cyb --help          # all 15 groups
node .claude/skills/cybernetics/bin/cyb item --help      # actions + positionals for one group
```

`cyb --help` lists a `ui` group — that is a human-only interactive REPL that
reads from stdin. Never run it: it refuses `--json` and a non-terminal stdin
with a clear error, but use the one-shot commands above instead of trying it.

## Output contract

- Add `--json` whenever you intend to parse the result. Human tables are for people.
- Lists default to **30** items. Pass `--limit N` deliberately — see the rate-limit section before raising it.
- Errors go to stderr. Under `--json` they arrive as `{"error":{"code","message","hint"}}`.
- **Truncation and cap notices go to stderr in `--json` mode** (inline on stdout otherwise), so a parsed stdout payload is never polluted — but also never silent about what was withheld. Read stderr, not just stdout.
- Exit codes: `0` ok · `1` general · `2` refused · `3` not found · `4` auth · `5` rate limited.

## The commands you will use most

```bash
cyb project list                                   # what projects exist
cyb item list CYB --json                           # the backlog
cyb item list CYB --state "In Progress" --json     # filtered
cyb item show CYB-42 --json                        # one work item
cyb item create CYB --name "Fix auth" --priority high
cyb item move CYB-42 "In Progress"                 # change status
cyb item assign CYB-42 avarile
cyb board CYB --json                               # everything, grouped by state
```

Work items are referenced as `<PROJECT>-<number>`, e.g. `CYB-42`. States,
labels and members are referenced by name, case-insensitively — the CLI
resolves them to UUIDs for you. `--description` and comment text are
HTML-escaped before being sent, so plain text is always safe to pass.

## Staying inside the 60 req/min budget — for the whole session, not one call

This instance allows **60 requests per minute total**, shared across every
command you run in this session. A single command usually respects it; a long
agent session that loops over resources will not. Defend the budget:

- Prefer the composite commands over looping per-resource:
  `cyb board CYB` (whole project by state), `cyb my` (everything assigned to
  you), `cyb search "auth" --project CYB` (name search) — each costs a small,
  bounded number of requests instead of one per item.
- Treat `--limit` as a deliberate choice, not a default to raise. A bigger
  `--limit` on `item list` means more pages, i.e. more requests.
- These commands carry their own hard caps — real ceilings, not
  suggestions: `my` scans at most **15 projects**; `search` scans at most
  **500 items** and filters names client-side (this fork has no server-side
  search); the resolver's item-lookup sequence scan is bounded at **2000**.
  Hitting a cap produces a notice (stderr under `--json`) — read it rather
  than retrying the same call.
- Prefer `--json` and read the actual data rather than re-querying to "check"
  a result.

## Safety

`delete` on any resource requires `--yes`. **Confirm with the user before
passing it.** Without `--yes` the command prints what it would destroy and
exits 2 without calling the API.

## Recovering from stale data

A cached item, label or project UUID that 404s is refreshed and retried
automatically, exactly once. States and members are not part of that
retry — a stale state or member surfaces as a 400 validation error instead of
a 404, so re-run `cyb sync` if a state/member name that should exist is
rejected.

If a name lookup fails, the error's hint lists the valid values. Read it
rather than guessing again.

## Deeper reference

- `references/api-surface.md` — which endpoints exist on this fork, and which return 404/402/403
- `references/recipes.md` — multi-step workflows (sprint setup, triage, status sweep)
- `references/troubleshooting.md` — what each exit code means and how to recover
