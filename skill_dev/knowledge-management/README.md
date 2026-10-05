# knowledge-management

A skill for the `knowledges` and `knowledge_type` tables of the **cybernetics-data** Teable database. It lets an AI agent (Claude Code or similar) or you find, read, save and organise knowledge quickly, and link it to goals, projects and tasks.

- **Fast query.** One REST call with a server-side filter (title or body, all terms or any, by type or domain, aliases such as k8s = k3s = kubernetes), ranked, with snippets. 0.1-0.5 s on the current base.
- **Careful writes.** Every write is a dry run first; creating checks for duplicates, resolves the type, lints the body and warns about secrets; every write is read back.
- **Links.** Parent/child series, "see also" (written on both sides, because the reverse field is broken), and `refer_knowledge` from goals, projects and tasks.
- **Doctor.** A read-only report of type-tree gaps, untyped, mistyped, temporary and empty entries, missing series hubs and near-duplicates, each with the command that fixes it.

## Requirements

- Python 3.9 or newer (standard library only).
- `CYBERNETICS_DATA_API_TOKEN` in the environment or in a `.env` file in the working directory or a parent. Optional `CYBERNETICS_DATA_URL` (default `https://cybernetics.avarile.com`).
- The `cyb-data` MCP server is only needed as a fallback when the token is missing.

## Install

Source: `skill_dev/knowledge-management/`. Installed copy for Claude Code: `.claude/skills/knowledge-management/` (a copy, not a link). Re-sync after any change:

```bash
rsync -a --delete --exclude '__pycache__' skill_dev/knowledge-management/ .claude/skills/knowledge-management/
```

## Use

Ask in plain language ("how did I set up the private docker registry?", "save this caddy config", "link the k3s notes to the migration project") and the skill picks the command. Directly:

```bash
kb=".claude/skills/knowledge-management/scripts/kb.py"
python3 $kb find k3s backup                    # all terms
python3 $kb find caddy nginx --any --titles    # any term, titles only
python3 $kb find docker --type deployment      # within a domain
python3 $kb get "K3S - Cheatsheet" --toc       # headings of a long entry
python3 $kb get rec9TTSDoktu59fT89i --section "Node Management"
python3 $kb types
python3 $kb capture --title "Caddy - Reverse Proxy Basics" --type "deployment - caddy" --body-file note.md   # dry run
python3 $kb append <id> --text-file update.md --yes
python3 $kb for-work project:<id>
python3 $kb refer <entry id> --to project:<id> --yes
python3 $kb doctor
```

`--json` on any command gives machine output. Exit codes: 0 ok, 2 blocked by a check, 3 not found or ambiguous.

## Decisions baked in

- **Everything is readable** (owner decision, 2026-10-05): credential entries and the type-level `credentials` value are returned unredacted. The skill shows secrets only when asked and never copies them elsewhere.
- Agents may capture into an existing type and append updates on their own; new types, re-parenting, archiving and bulk changes need confirmation.

## Things to know

- The generated API docs are wrong about `search` (the plain form returns HTTP 400). The CLI uses `filter` + `contains`, which is case-insensitive.
- `related_knowledge` and `knowledge_type.child_types` have dangling reverse fields. Links are written on both sides; the type tree uses `parent_type` only.
- Python's default user agent is rejected (HTTP 403); `teable.py` sends a curl user agent.
- `scripts/teable.py` is a copy of the project-management helper; `evals/run_flow.py` checks they stay identical.

## Layout

```
knowledge-management/
  SKILL.md               entry point loaded by the agent
  README.md              this file
  references/            schema, workflows, taxonomy, entry-format
  scripts/kb.py          the CLI (find, get, types, type, tree, capture, append, link, refer, trace, for-work, archive, type-set, doctor)
  scripts/doctor.py      read-only data-quality report
  scripts/safety.py      secret detection for capture/append warnings
  scripts/teable.py      shared REST helper (copied from project-management)
  evals/run_flow.py      live acceptance test ([TEST] rows, cleaned up)
  evals/evals.json       behavioral prompts with assertions
```
