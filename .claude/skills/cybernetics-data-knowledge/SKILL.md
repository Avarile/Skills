---
name: cybernetics-data-knowledge
description: Manage the personal knowledge base on the self-hosted Cybernetics (Teable) instance at cybernetics.avarile.com through the zero-dependency kb CLI. Use when asked to search, read, add, edit, retype, reparent, relate, audit, or delete knowledge entries or knowledge types; to inspect the knowledge hierarchy, tree, orphans, or credentials entries; or whenever the knowledges / knowledge_type tables are mentioned.
---

# Cybernetics Knowledge Base

Read/write management of the `knowledges` and `knowledge_type` tables on the
Teable instance at `cybernetics.avarile.com`, through the `kb` CLI.

**Never call the API with curl.** The CLI handles auth, the Cloudflare UA
requirement, the macOS cert fallback, reference resolution, link-array merging,
and the several places where the instance's published API docs are simply
wrong. `references/api-behavior.md` records every probed behaviour.

Not to be confused with `cybernetics-project` — a Plane fork at
`projects.avarile.com` for work items. Similar name, unrelated service.

The same Teable base also holds six `finance_*` tables (accounts, budgets,
categories, payees, tags, transactions). This skill does not touch them; the
token can, so scope any filter you write to the two knowledge tables.

## Invocation

`kb` is not on PATH. From the repo root:

```bash
.claude/skills/cybernetics-data-knowledge/bin/kb <command> [options]
```

Check the connection first if anything looks off:

```bash
.claude/skills/cybernetics-data-knowledge/bin/kb doctor
```

Every command prints one JSON document to stdout. Errors go to stderr; exit
code `1` for a failure, `2` for a refused destructive action.

## Setup

The token lives in `.env` **inside this skill directory** — its one canonical
home, so the skill is self-contained and moves or copies without depending on
anything outside it. The repo's bare `.env` gitignore rule matches at any
depth, so it is not committable there.

Resolution order: environment first, then `<skill>/.env`. Any of
`CYBERNETICS_DATA_APITOKEN`, `CYBERNETICS_DATA_API_TOKEN`,
`CYBERNETICS_API_TOKEN`, `TEABLE_API_TOKEN`, `TEABLE_TOKEN`, `API_TOKEN`. Base
URL overrides: `CYBERNETICS_DATA_URL`, `CYBERNETICS_DATA_BASE_URL`,
`CYBERNETICS_BASE_URL`, `TEABLE_BASE_URL`; otherwise
`https://cybernetics.avarile.com`. `.env` accepts `KEY=value` and `KEY: value`.

An environment variable wins over the file, which is the way to point the skill
at a different instance without editing it. `kb doctor` reports which base URL
resolved and that a token was found, never the token itself.

## Referring to an entry

Anywhere a command takes a `ref`, three forms work:

| Form | Example |
|---|---|
| record id | `recjjkJqhOlcT1LGR4j` |
| autonumber | `42` or `#42` |
| title | `"Plane - docker-compose"` — exact match (case-insensitive) preferred, else a unique substring |

An ambiguous title is an error that lists the candidates rather than picking
one. Titles are **not** unique in this base, so prefer a record id in scripts.

## Commands

```bash
kb list [--type T] [--active|--inactive] [--sort id] [--order asc] [--limit N]
kb get <ref>                      # one entry, full context body
kb search <query> [--field title|context|knowledge_type] [--limit N]
kb tree [--type T]                # hierarchy as nested JSON
kb children <ref>
kb orphans                        # entries with no parent and no children
kb stats                          # counts by type, activity, orphans

kb create --title T [--context C|-] [--type T] [--parent P] [--related a,b] [--inactive]
kb update <ref> [--title T] [--context C|-] [--type T] [--parent P|''] [--related a,b] [--active|--inactive]
kb parent <ref> --parent P        # reparent
kb parent <ref> --clear           # detach
kb relate <ref> --add a,b [--mutual]
kb relate <ref> --remove a,b
kb delete <ref>... --force

kb types list|get|create|delete
```

`--context -` reads the body from stdin, which is how to write a long
Markdown document into an entry:

```bash
cat notes.md | kb create --title "Caddy reverse proxy" --type "deployment - caddy" --context -
```

## Things that will bite you

**`search` in the raw API is broken — don't reach for it.** Passing
`search=foo` returns `400`; passing it correctly as an array returns *every*
record even for a nonsense query. `kb search` instead builds one
`{"conjunction":"or"}` filter of `contains` conditions over title, context and
the linked knowledge_type — server-side, one request. `--field` narrows to one
of those. An unknown field name in a filter does *not* error, it just matches
nothing, so take names from `client.SEARCHABLE` rather than inventing them.

`credentials` is deliberately not searchable: it holds real secrets and no
normalizer returns it, so a hit there could not be explained.

**`--related` on `kb update` REPLACES the list.** Use `kb relate --add` /
`--remove` to change it incrementally; they read the current members and merge.

**A "related" link only points one way.** `A → B` does not give you `B → A`.
Pass `--mutual` when you want both sides.

**Never write the parent's child list to move one entry.** The `knowledges`
field replaces the entire child set, orphaning everything you left out. Use
`kb parent <child> --parent <new>`, which writes the child's side only.

**The far side of a link takes ~1s to appear.** After a reparent, a `kb
children` read straight away can still show the old set. Re-read if it looks stale.

**Deleting a parent orphans its children, it does not cascade.** `kb delete`
refuses without `--force` and prints each target with its child count first —
read that list before re-running. Deletion is permanent; there is no trash.
`deleted_at` exists as a field but nothing filters on it, so it is not a
working soft-delete.

**`knowledge_type.credentials` holds secrets.** The `credentials` and
`credential_apikey` types cover real logins and API keys. Don't print those
entries into a shared transcript, a commit, or an issue unless asked.

## Conventions in this base

131 entries across 42 types at the time of writing, and worth matching:

- Types read as `domain - specific`: `deployment - docker-compose`,
  `database - mariadb`, `search engine - qdrant`. Reuse an existing type
  (`kb types list`) before creating one.
- The hierarchy is barely used — 129 of 131 entries are orphans. A flat entry
  with a good type is normal and fine; don't invent a tree to fill in.
- `context` is Markdown, often a fenced `.env` block or a runbook.
- `missav_meta*` types are a bulk-imported metadata set, unrelated to the
  infrastructure notes. Exclude them when auditing real knowledge.

## Tests

```bash
python3 .claude/skills/cybernetics-data-knowledge/tests/test_knowledge.py
```

41 offline tests, no network. `KB_LIVE=1` adds one live create/read/update/
delete round-trip that cleans up after itself.

## Layout

| Path | Contents |
|---|---|
| `src/client.py` | HTTP, config, filters, record CRUD, batch ops |
| `src/knowledge.py` | resolution, normalization, links, tree, stats |
| `src/cli.py` | the `kb` command surface |
| `references/api-behavior.md` | probe results; read before trusting the vendor docs |
