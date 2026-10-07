# Workflows

IDs and enum spellings: `schema.md`. Block formats: `context-blocks.md`. Formulas: `reports.md`. Phase 0 workflows are complete; Phase 1+ sections are marked and give the required shape until expanded.

## capture
0. If the user names a person ("for Anastasia", "assign to the designer"), resolve the contact with `teable.resolve_contact` semantics (exact name, unique partial, else ask) before creating.
1. Resolve the project: `query_records` on projects with `search` = the name, `projection` = title. Several matches -> ask. None named -> use the project titled `Inbox`. No `Inbox` and none named -> offer to create it (confirm).
2. Create the task: title as `Step NN [PHASE] Verb object` when it belongs to a planned project, otherwise a plain verb phrase; `belong_project`; `priority` (default `normal`); leave `progress` at default; `context` starts `Due: <date>` if the user gave one; resolve `assigned_to` from `contacts` if a person is named.
3. Read back and echo: title, project, priority, due, assignee.

## plate
1. Page `tasks` with `projection` = title, progress, priority, belong_project, assigned_to, started_at, finished_at, is_active, context (for `Due:`). Check `list_views` for a suitable view first.
2. If a person is named, use `assign.py tasks --contact <name>` instead. Drop inactive (`is_active` not `true`). Keep open tasks only unless asked otherwise. Group per `reports.md` (Overdue, Due in 7 days, In progress, Blocked, Unassigned, Undated). Scope to one project/assignee if named.
3. Report row count and how many were excluded.

## status
Find the project (`search`). Run `python3 scripts/rollup.py project <recId>` (add `--json` for agents). It computes completion, overdue, undated, SPI, RAG with the rule that fired, next gate, open risks and last status date exactly as `reports.md` defines, and states its row basis. For a goal: `rollup.py goal <recId>` (KR scores from `## Key Results`, runway to `deadline`, each project's RAG). Add "Suggested next step" (advance the project? escalate? unblock?) but make no writes. If the token is missing, compute from MCP reads using the same definitions and say so.

## portfolio
`python3 scripts/rollup.py portfolio`: goals -> projects with RAG, projects with no goal / no lead / no tasks, stale projects, orphan active tasks, Inbox items older than 7 days.

## assign / lead / workload
Model (see `model-mapping.md`): `projects.lead_by` = the one accountable owner of a project; `tasks.assigned_to` = the one person (or agent persona) responsible for a task. Both link to `contacts`; a task has at most one assignee. Contacts include agent personas (e.g. `Agentic Mind (Developer)`), so work can be assigned to agents the same way as to people.
- **assign tasks:** `python3 scripts/assign.py set --to <contact> (--project <id|title> | --ids ...) [--phase PLAN,DO] [--unassigned-only] [--reassign]`. Dry-run first: it prints how many tasks change, how many are already theirs, and how many are **held by someone else (skipped)**. Taking over someone else's tasks needs `--reassign` and the user's confirmation. `--to none` clears. Apply with `--yes` (count first, then confirm; verified read-back).
- **set the lead:** `assign.py lead <project> --to <contact> [--reassign]`. Replacing an existing lead needs `--reassign` and confirmation.
- **at planning time:** `scaffold.py ... --assign PLAN=<contact> --assign DO=<contact> --assign CHECK=<contact>` (repeatable; `--assignee` is the default for unmapped phases). The preview shows who gets each task; a good default is the lead on PLAN/CHECK/ACT and the doer on DO, but ask.
- **workload:** `assign.py workload [--project P]`: per person open / in progress / overdue / due in 7 days / urgent+important / on hold, an `(unassigned)` row, who leads which active projects, and FLAGs for more than 3 in progress (WIP limit) or any overdue. Use it before assigning new work ("who has capacity?") and in the weekly review.
- **a person's list:** `assign.py tasks --contact <contact> [--project P]` (Overdue, Due in 7 days, In progress, Blocked, Undated). This is "what's on X's plate".
- Contacts resolve by exact name first, then a unique partial match; an unknown or ambiguous name stops with the candidates listed. Never guess a contact. Do not create contacts silently; offer to, and confirm.
- `doctor` also flags: `in-progress` tasks with no assignee, open tasks of a project with no `lead_by`.

## lifecycle (start / finish / hold / cancel)
- `start`: task -> `in-progress`; if it has no assignee, assign it to the person starting it (the user, or the agent's own contact); never take over a task held by someone else without confirmation; set `started_at` = today if empty; check the project's gate (if a `Gate:` task earlier in the project is unfinished, warn and ask); append `## Log` line.
- `finish`: ask for or state the evidence; -> `finished_validating` (or `finished_reviewing` if delivered but unchecked, or the value the user names); set `finished_at` if empty; append `## Log` with evidence. Agent ceiling applies (`agent-protocol.md`).
- `hold`: -> `onhold`; reason required; append `## Log`; if the project is affected, offer a Blocker entry.
- `cancel`: confirm; reason required; -> `cancelled`; append `## Log`.
- Moving out of a finished state clears `finished_at` (say so).
- After any change, if all open tasks of the project are now finished, suggest the next project status. Do not apply it.
- Read back and show changed fields.

## doctor
Report-only. Scan goals, projects, tasks (`projection` limited to what each check needs) and list findings grouped by severity with counts:
- tasks with no `belong_project`; tasks in Inbox older than 7 days
- projects with no `belong_goals`, no `lead_by`, or no tasks; stale `in-progress` projects
- `in-progress` task with empty `started_at`; finished task with empty `finished_at`
- finished project with open tasks; open tasks under `cancelled`/`finalized` projects
- DO task started while an earlier gate task is unfinished
- all tasks finished but project not advanced
- open tasks with no `Due:`
- rows still marked `_Mock data._`
- projects past `preparing` with empty `refer_knowledge`; `finalized` projects with an empty `## Lessons`
Each finding gets a proposed fix. Apply fixes only after the user approves them, with a count first.

## plan-goal
1. Gather the objective, period and what success looks like. Check `list`/search for an existing goal to avoid duplicates.
2. Draft one Objective (qualitative, memorable) and <=3 Key Results, each with metric, baseline, target, date, owner, and a one-line rationale for why the target is a stretch but reachable. Lint with `model-mapping.md` (outcomes not tasks; <=3 KRs; <=3 Objectives per period, count existing goals with the same period).
3. Preview as the `## Key Results` table from `context-blocks.md` plus `deadline`. On approval create the goal (`create_records`: title = Objective, context = KR table + empty `## Check-ins`, `deadline` = period end `YYYY-MM-DD`). Read back.

## plan-project
1. Interview: outcome, which KR it moves (goal), sponsor and lead (`contacts`), hard deadline, fixed constraint (scope, time or cost), repo/workspace path, size.
2. Draft the `## Charter`, a Risk Register with >=3 risks (each with mitigation), a Communication Plan, and the estimate as best / likely / worst with a declared buffer (default 20%; 30% for new or uncertain work). Lint per `model-mapping.md`.
3. Knowledge pre-flight (see knowledge): up to 5 candidates by title and type, user picks.
4. Pick the template: `python3 scripts/scaffold.py --list`, then preview `scaffold.py <template> --start <date> --days <likely days> --buffer <b>`. It prints every task with its due date and runs the lint (gate, CHECK, ACT, mid-point). Show the whole preview, including the declared buffer and end date.
5. After the user approves: create the project (`create_records`: `progress` `preparing`, `belong_goals` `{id}`, `lead_by` `{id}`, `context` = Moves/`Repo:`/`Shape: <template>`/Charter (with the exact `- Estimate: best Nd / likely Nd / worst Nd; buffer N%` line)/Risk Register/Communication Plan/empty logs; `Repo:` is what lets an agent find the project later), then `scaffold.py ... --project-id <id> --create` (dry-run) and again with `--yes`. It refuses a project that already has tasks. Link knowledge on the project with `refer_knowledge`.
6. Read back counts (tasks created, links) and run `rollup.py project <id>`; expect GREEN with no overdue. Project stays `preparing` until the gate task is finished; never set `initiated` automatically.

## logs (change / risk / blocker)
Append the block from `context-blocks.md` with `scripts/write.py ctx-append` (section `## Change Log`, `## Risk Register` or `## Blockers`). Change: state scope/time/cost impact; impact >5% -> written notice within 24 h and the escalation level; re-baselining due dates is a bulk write (`write.py bulk-update`, count first, confirm). Risk: a high-impact risk without a mitigation turns the project AMBER in `rollup.py`.

## review
- **report (weekly):** run `rollup.py project`, then write the PDCA-format report from `reports.md` (RAG + one sentence, accomplished 3-5, planned 3-5 with owners, risks and issues, decisions needed, metrics). Offer to append it to `## Status Log` with `ctx-append` (entry heading `### YYYY-MM-DD · <emoji> <RAG>`). The status-gap rule resets when an entry is appended.
- **checkin (OKR):** read `## Key Results`; ask the user for current values (or compute only when a KR is directly measurable from the database); score = (current - baseline) / (target - baseline), clipped 0-1; flag KRs that dropped >0.2 since the last check-in or are below 0.4 at the midpoint; list blocked initiatives (projects not GREEN). Show the new table and append `### YYYY-MM-DD · avg <x>` to `## Check-ins`; replacing the KR table is a read-modify-verify edit of that block only.
- **healthcheck:** for projects >3 months or at 50% of the timeline: run `rollup.py`, then walk the six questions in `context-blocks.md` with the user, append the findings under `## Health Check`.

## knowledge (link / trace)
Use the `knowledge-management` skill (`skill_dev/knowledge-management/scripts/kb.py`, installed under `.claude/skills/knowledge-management/`).
- **pre-flight:** `kb.py for-work project:<id> [--terms <domain words>]` lists what is already linked (project, its goal, its tasks) and up to 5 suggestions by title and type. Link only the user's picks: `kb.py refer <entry ids> --to project:<id> --yes` (or `task:<id>` when specific). `refer` adds to the existing links and reads back; never write `refer_knowledge` with only the new id.
- **trace:** `kb.py trace <entry id or title>` lists the goals, projects and tasks that reference it (one `hasAnyOf` query per table).

## close
Entry: the project is in a CHECK state (`finished-reviewing` or later) or the user says it is done. Never rush this: it is where the knowledge loop closes.
1. **Readiness.** `python3 scripts/close.py check <projectId>` lists six criteria (all tasks finished or cancelled, `finished_at` on every finished task, `## Retro` and `## Lessons` have content, a lessons entry is linked via `refer_knowledge`, an `## Estimation Record` row exists). Work through every FAIL with the user; do not skip one to reach `finalized`.
2. **Retro.** Ask the five questions (went well / didn't / confused us / do differently with owner and date / expectation gaps), draft the answers from the project's logs, tasks and status history, and have the user correct them. Append under `## Retro` with `ctx-append`.
3. **Blameless post-mortem** (only if something went wrong or slipped): what happened, timeline, root causes, contributing factors, action items with owners and due dates. Process and system causes, not individuals. Each action item becomes a task (in the next-cycle project or Inbox) or a risk. Append under `## Retro`.
4. **Lessons -> knowledge.** Draft 3-7 lessons (what to repeat, what to stop, what to estimate differently). Find the `knowledge_type` `project - lessons`; if it does not exist ask once, then create it (`create_records` on `knowledge_type`; set `parent_type` only if the user wants it nested). Create the entry `Lessons - <project title>` with `kb.py capture --title "Lessons - <project title>" --type "project - lessons" --body-file lessons.md --related <entries consulted at Plan> --refer project:<id>` (dry-run first; `--new-type` only after the user agreed to create the type). Show the preview; run with `--yes` after approval. `--refer` sets the project's `refer_knowledge` and append the same bullets under `## Lessons` with a `-> knowledge: <title>` pointer.
5. **Estimation norms.** `python3 scripts/close.py stats <projectId>` gives actual vs best/likely/worst, declared-buffer verdict, on-time rate and the slipped tasks, and an `Estimation norms row`. Find (or, after asking, create with type `project - estimation`) the knowledge entry `Estimation norms`; append the row to a table under `## Records` with `ctx-append` (add the header the first time). Append the same row to the project's `## Estimation Record`. If the actuals consistently exceed the likely estimate for a shape, say so and propose a larger default buffer in the norms entry (the user decides).
6. **Finalize.** Re-run `close.py check`; when it prints READY, ask the user to confirm, then set the project `progress` to `finalized` (project spelling) and read back. Tasks need no change. Offer: archive (`is_active` false + `deleted_at`, only if they want it hidden) and a next-cycle draft (`plan-project`, with the post-mortem actions and updated buffer).
Agents may run `check` and `stats` and draft, but retro content, lessons, `finalized`, and any new `knowledge_type` need the user's confirmation.

## Automated acceptance test
`python3 evals/run_flow.py` creates `[TEST]` rows, exercises scaffold, rollup (GREEN/AMBER/RED rules), the write guards, trace and views, deletes only what it created and checks the baseline is restored. Run it after any change to the scripts or to `reports.md` thresholds.
