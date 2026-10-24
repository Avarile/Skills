# project-management

A skill that turns the `goals`, `projects` and `tasks` tables of the **cybernetics-data** Teable database into a working project-management practice. It is meant to be used by an AI agent (Claude Code or similar) and by you, on the same data.

- **Goals** are OKR Objectives, with up to 3 Key Results and a score.
- **Projects** are PDCA cycles (Plan, Do, Check, Act) that move a Key Result. They have one accountable lead.
- **Tasks** are steps inside a PDCA phase. They have one assignee, who can be a person or an agent persona (for example `Agentic Mind (Developer)`).
- **Knowledge** feeds planning and receives the lessons at close-out.

The database is the single source of truth. The skill keeps no state of its own.

## What it can do

| Verb | What it does |
|---|---|
| `capture` | Add a task. With no project named, it goes to the `Inbox` project. |
| `plate` | What's on my plate: overdue, due in 7 days, in progress, blocked, unassigned. |
| `status`, `portfolio` | Health of one project, goal or everything: completion, overdue, SPI, RAG, next gate. |
| `plan-goal`, `plan-project` | Draft an OKR; draft a charter, risks, an estimate range and a dated task list from a template. |
| `start`, `finish`, `hold`, `cancel` | Task lifecycle with date rules and an evidence line. |
| `assign`, `lead`, `workload` | Assign tasks or a project lead to contacts. Per-person workload and task lists. |
| `change`, `risk`, `blocker` | Append to the project's logs and apply the escalation ladder. |
| `report`, `checkin`, `healthcheck` | Weekly status report, OKR check-in, mid-project health check. |
| `close` | Retro, lessons to knowledge, estimation norms, `finalized`. |
| `link`, `trace` | Link knowledge to work; find what used a knowledge entry. |
| `doctor` | Read-only data-quality audit. |
| `resume` | For agents: find the project for the current repo and show its in-progress and next tasks. |

You do not need to name a verb. Ask in plain language ("how is Website Refresh doing?", "assign the CHECK tasks to Anastasia") and the skill picks the workflow.

## Requirements

- Python 3.9 or newer.
- The `cyb-data` MCP server connected (the skill uses it for creating records and single updates).
- `CYBERNETICS_DATA_API_TOKEN` in the environment, or in a `.env` file in the working directory or any parent. Without it the scripts exit with a message and the skill falls back to the MCP tools. Keep `.env` out of git.
- Optional: `CYBERNETICS_DATA_URL` to override the default `https://cybernetics.avarile.com`.

## Install

The source lives in `skill_dev/project-management/`. The installed copy for Claude Code is `.claude/skills/project-management/`. It is a copy, not a link, so re-sync after any change:

```bash
rsync -a --delete --exclude '__pycache__' skill_dev/project-management/ .claude/skills/project-management/
```

## How to use it

**As yourself.** Ask in the chat. The skill leads with decisions you need to make, then the facts. Anything that creates structure (a goal, a project, a bulk change) is shown as a preview first and only written after you confirm.

**As an agent.**
1. At the start of a session, run `python3 scripts/resume.py` (add `--as "<contact name>"` to act as a persona; add `--json` for machine output).
2. Claim a task (`in-progress`), log evidence as you work, and hand off with an honest status.
3. Agents may move a task to `finished_reviewing`. `finished_validating`, project status changes, creating projects, reassigning other people's tasks and bulk changes need your confirmation.

Full rules: `references/agent-protocol.md`.

## Scripts

All are read-only unless noted, and every write is dry-run by default (`--yes` applies it). Run them from the repo root so the `.env` is found.

| Script | Purpose |
|---|---|
| `query.py` | Filtered, ordered reads (the MCP `query_records` tool silently ignores a `filter`). |
| `rollup.py` | Deterministic health numbers: `project`, `goal`, `portfolio`. |
| `scaffold.py` | Expand a task template into dated tasks, lint it, optionally create them. `--assign PLAN=Avarile` assigns by phase. |
| `assign.py` | `set`, `lead`, `workload`, `tasks`. Never takes work from someone else without `--reassign`. |
| `write.py` | `bulk-update` (validated, read back) and `ctx-append` (append to a `## Section` of a context field, aborting if it changed meanwhile). |
| `views.py` | List and create saved views with filters. |
| `resume.py` | Agent start-of-session brief. `--hook` mode for a SessionStart hook. |
| `close.py` | `check` the criteria for `finalized`; `stats` for actual vs estimate. |

Examples:

```bash
python3 scripts/rollup.py project <projectRecId>
python3 scripts/assign.py workload
python3 scripts/assign.py set --to Anastasia --project "k3s Migration" --phase CHECK,ACT          # dry run
python3 scripts/scaffold.py build --start 2026-11-02 --days 28 --assign PLAN=Avarile
python3 scripts/query.py tblOMgDiajqa1moRRjE --filter 'fldMTuydiWUFAgtqAPX is urgent' --count
```

## Conventions the skill relies on

- **Task title:** `Step NN [PLAN|DO|CHECK|ACT] Verb object`.
- **Task context:** first line `Due: YYYY-MM-DD` (there is no due-date field), optional `Gate:`, `Depends:`, `Est:`, `Acceptance:`, then a `## Log` of dated evidence lines.
- **Project context:** `Moves:`, `Repo:` (this is how an agent finds the project), `Shape:`, then `## Charter` (with the exact `- Estimate: best 20d / likely 28d / worst 40d; buffer 20%` line), `## Risk Register`, `## Status Log`, `## Change Log`, `## Retro`, `## Lessons`, `## Estimation Record`. Templates are in `references/context-blocks.md`.
- **Ownership:** one `lead_by` per project, at most one `assigned_to` per task.
- **Status values differ by table** (projects use hyphens, tasks use underscores). See the lookup in `references/schema.md`.

## Things to know

- A wrong status spelling does not error. It silently clears the field. The scripts validate values; with the MCP tools, always read back after writing a select field.
- Dates are written as `YYYY-MM-DD` (Melbourne time) but read back as UTC timestamps.
- `projects.lead_by` labels its link with the contact's email, so lead names are read via the contact id.
- Soft delete (`is_active` false plus `deleted_at`) is the default. Hard deletes only on explicit request.
- Secrets (`system_info.access_token`, `knowledge_type.credentials`, credential knowledge entries) are never read or echoed.

## Testing

```bash
python3 evals/run_flow.py          # 55 live checks; creates and deletes only [TEST] rows, then verifies the baseline
python3 evals/make_fixture.py create   # temporary realistic data for the behavioral evals
python3 evals/make_fixture.py drop     # removes exactly what create made
```

`evals/evals.json` holds the 18 behavioral prompts with assertions. First results (iteration 1, one run each, read-only): 92% with the skill vs 80% without. See `../project-management-workspace/iteration-1/benchmark.md`.

## Known gaps

- `close` is documented and its helper scripts are tested, but it has not been run on a real project yet.
- `doctor` is a documented checklist, not a script.
- Due dates cannot be shifted in bulk (each task stores its own `Due:` text); there is no `shift-due` command yet.
- Optional schema upgrades (a real `due_date` field, a `project_logs` table, saved views) are proposed in `references/workflows.md` and the plan, but not applied.
- The skill description has not been tuned for triggering accuracy.

## Layout

```
project-management/
  SKILL.md                    entry point loaded by the agent
  README.md                   this file
  references/                 schema, model mapping, context blocks, reports, workflows, agent protocol
  scripts/                    the Python tools above (teable.py is the shared helper)
  assets/templates/           six task templates (personal-small, build, client-delivery, program, infra-build, migration)
  evals/                      run_flow.py, make_fixture.py, evals.json
```
