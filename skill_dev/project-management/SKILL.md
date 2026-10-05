---
name: project-management
description: Run goals, projects and tasks in the user's cybernetics-data database as a real project-management practice (OKR for goals, PDCA for projects), for both an AI agent doing work and the user planning it. Use whenever the user or an agent wants to capture or update a task, see "what's on my plate", get project or goal status, plan a goal/OKR or a new project, run a weekly review or check-in, log a risk, blocker or change, claim/finish work from a coding session, close a project with a retro and lessons learned, audit the backlog, or link knowledge to a project - even if they never say "project management". Not for CRM follow-ups tied to a person or deal, and not for finance.
---

# Project Management (cybernetics-data)

The database is the single source of truth. This skill is stateless: read fresh, write back, read back. Goals are OKR Objectives, projects are PDCA cycles that move a Key Result, tasks are steps in a PDCA phase, knowledge feeds Plan and receives lessons at Act.

Base `bseJEuE54y5caWO0Xc8`, tools `mcp__cyb-data__*` (load with ToolSearch if not loaded). Cells are keyed by **field ID**. IDs, link shapes and enum spellings: `references/schema.md`. Reuse the CRUD and guardrail rules of the `cybernetics-workspace` skill (soft delete, confirm bulk, no secrets); do not restate them here.

## Pick a mode

- **Agent mode** (you are Claude Code or another agent doing work): terse, structured, IDs included, no narration, end with one line `changed: ...`. Follow `references/agent-protocol.md` and its autonomy ceiling.
- **Human mode** (the user is asking): lead with **Decisions needed** (if any), then facts, short prose. Ask before writes that create structure.

Same verbs, same data, same numbers in both modes.

## Verbs

| Verb | Use for | Detail |
|---|---|---|
| `capture` | add a task; no project given -> project titled `Inbox` | `references/workflows.md#capture` |
| `plate` | what's on my plate: overdue, due <=7d, in progress, blocked | `#plate` |
| `status` | one project or goal: counts, % done, overdue, SPI, RAG, next gate (`scripts/rollup.py`) | `#status`, `references/reports.md` |
| `portfolio` | all active goals -> projects, RAG, stale, orphans | `#portfolio` |
| `plan-goal` | draft OKR (1 Objective, <=3 KRs) | `#plan-goal`, `references/model-mapping.md` |
| `plan-project` | charter + risks + estimate range + task skeleton + knowledge links | `#plan-project` |
| `assign` `lead` `workload` | assign tasks/leads to contacts (people or agent personas), per-person workload and task lists (`scripts/assign.py`) | `#assign--lead--workload` |
| `start` `finish` `hold` `cancel` | task lifecycle with date rules and evidence | `#lifecycle` |
| `change` `risk` `blocker` | append to the project's logs, apply escalation ladder | `#logs` |
| `report` `checkin` `healthcheck` | weekly status, OKR check-in, mid-project review | `#review` |
| `close` | retro, lessons -> knowledge, estimation norms, `finalized` (`scripts/close.py`) | `#close` |
| `link` `trace` | maintain / reverse-scan knowledge links | `#knowledge` |
| `doctor` | data-quality audit, report-only | `#doctor` |
| `resume` | agent: `scripts/resume.py` finds the project for this repo, shows in-progress/next tasks, blockers | `references/agent-protocol.md` |

Scripts (Python 3, token from `CYBERNETICS_DATA_API_TOKEN`): `query.py` filtered reads, `rollup.py` health numbers (incl. open work by assignee), `assign.py` assignment and workload, `scaffold.py` task templates, `write.py` bulk update and log append, `views.py` filtered views. `resume.py` agent start-of-session brief (and SessionStart hook mode), `close.py` finalize checks and estimate-vs-actual. Templates: `assets/templates/`. Acceptance test: `evals/run_flow.py`.

## Core rules

1. **Enums are table-specific.** Projects use hyphens (`finished-reviewing`), tasks use underscores (`finished_reviewing`). Take values from the lookup in `references/schema.md`; never free-type them. New options cannot be created. **A wrong spelling does not error: it silently clears the field** (verified 2026-10-02), so read back after every select write; `scripts/write.py` validates values and refuses bad ones.
2. **No server-side filter.** `query_records` has only `search`, `viewId`, `skip/take`, `projection`. A `filter` argument is **silently ignored** (tested 2026-10-02: returned unfiltered rows, no error), so never pass one and never trust a result as filtered unless it came via `viewId`. **For filtered or ordered reads run `scripts/query.py`** (Teable REST API, token from `CYBERNETICS_DATA_API_TOKEN`, usage in the script header and `references/schema.md`); if the token is missing it exits with a message, then fall back to MCP and filter client-side. Always pass `projection`, page with `hasMore`, filter client-side, and say how many rows a figure is based on. Use a saved view if one fits (`list_views`).
3. **Exclude inactive** (`is_active` = false) from every report unless asked.
4. **Dates** write `YYYY-MM-DD` (stored as Melbourne midnight); reads return UTC timestamps, so convert to Australia/Melbourne before comparing. Today comes from the conversation, never guessed. Unchecked `is_active` reads `null`: treat anything not `true` as inactive.
5. **Task conventions (Tier 0).** Title `Step NN [PLAN|DO|CHECK|ACT] Verb object`. `context` line 1 `Due: YYYY-MM-DD`, then optional `Gate:`, `Depends:`, `Est:`, `Acceptance:`, then `## Log`. If `tasks` has a real due-date field (probe `get_table_schema`), use it instead.
6. **Lifecycle dates.** `in-progress` sets `started_at` if empty. Any `finished_*` sets `finished_at` if empty. Leaving a finished state clears `finished_at` (say so). Never overwrite an existing date unless given one.
7. **"Done" = `finished_validating`** for tasks unless the user names another; state which you set. Project status is never auto-advanced: suggest it.
8. **Evidence.** A task moved to a finished state gets a dated `## Log` line with the evidence (commit, PR, test result, link, or the user's word).
9. **Log writes use `scripts/write.py ctx-append`** (section-aware append, aborts if someone edited the field meanwhile, read-back verified). Do not re-emit a whole `context` through MCP to add a log entry. Replacing a block (not appending) is still read-modify-verify: `get_record`, change only that section, write, read back. Logs are append-only. Templates: `references/context-blocks.md`.
10. **Write routing.** MCP `create_records` for creating (bulk OK) and `update_record` for one record. `scripts/write.py bulk-update` for the same change on many records (dry-run first, then `--yes`; refuses >200 rows). `scripts/views.py create` for filtered saved views (MCP `create_view` cannot set a filter). Scripts default to dry-run and need the token; without it, use MCP and tell the user.
11. **Confirm before:** creating a goal or project, any bulk create/update (count first), cancel, archive, re-parent, `lead_by` changes, schema or view changes. Show a full preview for `plan-*`.
12. **Secrets and knowledge.** Never read `system_info.access_token`. All knowledge reads and writes (pre-flight, link, trace, lessons) go through the `knowledge-management` skill's `kb.py`; per the owner's decision (2026-10-05) every entry, credential types included, is readable. Pre-flight suggestions list title + type only.
13. **Don't fabricate.** If a project, contact or knowledge entry isn't found, say so; never guess an ID.
14. **Assignment.** One accountable `lead_by` per project, at most one `assigned_to` per task. Assigning never silently takes work from someone else: such tasks are skipped unless `--reassign` plus the user's confirmation. Resolve contacts by name or id with the scripts and never guess. `projects.lead_by` labels its link by email, so read lead names via the contact id.

## Disambiguation

"Task" means `cybernetics-data.tasks` unless it is tied to a person, company or deal (then CRM, via `cybernetics-workspace`). "Assign to X" resolves X in `contacts`.

## Status of this skill

Phases 0, 1 and 2 of `/Users/avarilewang/.claude/plans/analysis-the-mcp-cybernetics-data-floofy-sketch.md` are built and pass `evals/run_flow.py`. Open items: run `evals/evals.json` (with-skill vs baseline) and Tier 1 schema upgrades (`due_date`, `project_logs`, saved views), both need the user's go-ahead. Tier 1 schema upgrades are proposals only and need the user's approval.
