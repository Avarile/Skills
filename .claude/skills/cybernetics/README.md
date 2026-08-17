# cyb — Cybernetics CLI

A zero-dependency Node CLI for the Cybernetics project instance
(`https://projects.avarile.com`, a Plane fork).

One codebase serves two audiences: agents invoke it with `--json`, humans use
the tables and the interactive session.

**Status:** verified against Plane v2.6.3 at `projects.avarile.com` on 2026-08-17.
318 unit tests run offline with no token and no network (314 pass, 4 skipped);
4 integration tests run against the live instance when `CYB_TOKEN` and
`CYB_RUN_INTEGRATION=1` are both set, and delete their scratch project
afterwards.

## Requirements

Node 24 or newer. No `npm install` — there are no dependencies.

## Setup

```bash
export CYB_TOKEN='<your Plane API token>'
node bin/cyb doctor        # verify connectivity
node bin/cyb init          # persist config to ~/.cybernetics/config.json (0600)
```

Credentials are stored outside this repository. The CLI never prints your
full token — only a truncated fingerprint.

Optionally put `cyb` on your PATH:

```bash
npm link            # from this directory
cyb doctor
```

## Everyday use

```bash
cyb project list
cyb item list CYB
cyb item create CYB --name "Fix auth timeout" --priority high
cyb item move CYB-42 "In Progress"
cyb board CYB
cyb my
```

Run `cyb --help` for the full list of 15 command groups, or
`cyb <group> --help` for one group's actions and argument syntax.

## Interactive session

```bash
cyb ui
```

```
cyb:-> cd CYB
cyb:CYB> ls --state todo
cyb:CYB> open 42
cyb:CYB> mv 42 "In Progress"
cyb:CYB> cd OTHER
cyb:CYB> exit
```

The session holds one client for its whole lifetime, so it tracks the rate
limit budget across every line instead of resetting per command. Tab
completion draws on the local cache, so it costs no API calls.

## Safety

Deleting anything requires `--yes`. Without it the command shows what it would
destroy and exits 2 without touching the API.

## Rate limit

This instance allows 60 requests/minute, shared across an entire session.
Prefer `board` / `my` / `search` over per-resource loops, and treat `--limit`
as deliberate — see `SKILL.md` and `references/troubleshooting.md`.

## Tests

```bash
npm test                    # unit tests, no network needed
```

```bash
CYB_TOKEN=<your token> npm run test:integration
```

Runs the 4 tests in `tests/integration/live.test.mjs` against the live
instance (the script sets `CYB_RUN_INTEGRATION=1` itself); the scratch
project they create is deleted in a `finally` block.

## Documentation

- `SKILL.md` — the agent-facing entry point
- `references/api-surface.md` — what this fork does and does not expose
- `references/recipes.md` — multi-step workflows
- `references/troubleshooting.md` — exit codes and recovery
