---
name: knowledge-management
description: Look up, read, save and organise entries in the user's knowledge base (cybernetics-data `knowledges` and `knowledge_type` tables) fast, through the Teable REST API. Use whenever the user or an agent wants to find something in their notes, how-tos, runbooks, cheatsheets, deployment guides, docker-compose files, configs, commands or credentials ("how did I set up k3s?", "what's the mariadb backup script?", "my Apple account password"), save or document something to remember, add an update to an existing entry, browse or restructure knowledge types, clean up duplicates, or link knowledge to a goal, project or task - even if they never say "knowledge base". Not for CRM notes about people, companies or deals.
---

# Knowledge Management (cybernetics-data)

The knowledge base is the single source of truth; this skill keeps no state. Everything goes through one CLI, run from the repo root so `.env` is found:

```bash
python3 .claude/skills/knowledge-management/scripts/kb.py <command> ...   # add --json for machine output
```

IDs, link semantics and verified API behaviours: `references/schema.md`. Workflows step by step: `references/workflows.md`. Types, parents and series: `references/taxonomy.md`. How to write an entry: `references/entry-format.md`.

## Pick a mode

- **Agent mode** (you are doing work in a coding session): use `--json`, include record ids, no narration, end with one line `changed: ...` (or `changed: nothing`).
- **Human mode** (the user is asking): answer the question from the entry text first, then name the entry (title + id). Lead with decisions if a write needs approval.

## Commands

| Need | Command | HTTP calls |
|---|---|---|
| look something up | `find <terms>` (all terms; `--any`; `--type <name or domain>`; `--exact` no aliases; `--all` incl. archived; `--titles`) | 1-2 |
| read an entry | `get <id or title>`; long entries: `--toc` first, then `--section "<heading>"`; `--max-chars N` | 1 |
| browse | `types` (tree + counts), `type <name>` (description, credentials value, entries), `tree <id>` (parent chain, children, related) | 1-3 |
| save new knowledge | `capture --title --type --body-file F [--parent ID] [--related ID ...] [--refer project:ID] [--new-type [--parent-type T]]` | 3-6 |
| add to an entry | `append <id> --text-file F [--section "## Updates"] [--no-date]` | 3 |
| organise one entry | `link <id> [--type T] [--title X] [--parent ID / --no-parent] [--related ID ...] [--unrelate ID ...]` | 2-6 |
| knowledge for work | `for-work project:ID` (linked + suggestions), `refer <ids> --to project:ID [--remove]`, `trace <id>` | 2-5 |
| archive | `archive <id> [--restore]` (soft: `is_active` false + `deleted_at`) | 3 |
| taxonomy | `type-set "<type>" [--create] [--title] [--parent-type T / --no-parent] [--description D]` | 2-3 |
| data quality | `doctor` (read-only, groups A-H with a fix command each) | 5 |

Every write command is a **dry-run unless `--yes`**: run it once, show or check the preview, then re-run with `--yes`. Writes read back and verify; exit 2 = blocked by a check, 3 = not found or ambiguous.

## Core rules

1. **Search before answering, search before creating.** Answer "how did I..." questions from the stored entry, not from memory, and name the entry used. If `find` returns nothing, retry once or twice with other words, `--any`, or a `--type` domain, then say it is not in the knowledge base.
2. **Read narrowly.** `find` shows snippets; open only the 1-2 entries that matter. For entries over ~4k chars use `get --toc` then `--section`; never dump a 30k-char entry to answer one question.
3. **Everything is readable.** Owner decision 2026-10-05 (CR-1): `find`/`get`/`type` return credential entries and `knowledge_type.credentials` unredacted. Show a secret only when the user asked for it; never copy secrets into other tables, commits, logs, task text or other tools.
4. **Prefer updating over duplicating.** `capture` blocks an exact-title duplicate and lists similar entries; if one fits, `append` to it instead.
5. **Types are a shared taxonomy.** Use an existing type (`types`); partial names resolve if unique. A new type, renaming or re-parenting a type, re-parenting an entry, archiving, and any change to more than one record need the user's OK first (count and list them).
6. **Secrets in bodies.** `capture`/`append` warn when a body looks like it holds a password, key or token and the type is not a credential type. Tell the user and suggest a credential type; do not silently strip or move it.
7. **Links are one-way in the data.** `related_knowledge` has no working reverse field: always use `link --related` (writes both sides). `refer_knowledge` lives on goals/projects/tasks: use `refer` (adds, never replaces). Never write `knowledge_type.child_types`; the tree is `parent_type`.
8. **Exclude archived** entries unless asked (`find` does by default; `--all` includes them).
9. **Don't fabricate.** Never guess a record id; resolve by `find`/`get`. If an id or title is ambiguous, the CLI lists candidates: pick with the user.
10. **No token** (`CYBERNETICS_DATA_API_TOKEN` missing): the CLI exits with a message. Fall back to MCP `mcp__cyb-data__query_records` (`search`, `projection`; it has no filter), `get_record`, `create_records`, `update_record`, and say the fast path is unavailable.

## Autonomy ceiling (agents)

| Action | Alone | Confirm with the user |
|---|---|---|
| find, get, types, tree, trace, for-work, doctor | yes | |
| capture into an existing type after the duplicate check | yes, report the new id | if `capture` warned about secrets or near-duplicates |
| append a dated update to an entry | yes | |
| refer / link related entries for the work you are doing | yes | |
| new type, type rename/re-parent, entry re-parent, archive, bulk or doctor fixes | | always |

## With other skills

- **project-management** decides *when* knowledge is linked (plan pre-flight, close-out lessons); this skill does the *how* (`for-work`, `refer`, `capture --refer`).
- **cybernetics-workspace** covers the other tables (finance, CRM). For knowledge, this skill's rules win where they differ (CR-1 readability, one-way links).
- Meeting notes about a person, company or deal are CRM notes, not knowledge.

## Status

Built in project "Knowledge Management Skill" (cybernetics-data `recHXdCBQqv89De6Yti`). Acceptance test: `evals/run_flow.py`. Data clean-up (doctor groups A-F) is Step 13 and needs approval per group.
