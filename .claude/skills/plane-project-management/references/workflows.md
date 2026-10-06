# Workflows

Common preamble for every flow: resolve IDs (see `tool-map.md`). Human mode starts with **Decisions needed**; agent mode ends with `changed: ...`.

## plate
1. `get_current_user`. 2. `list_work_items(assignees=["me"], state_groups=[backlog, unstarted, started], order_by=target_date)`, paged. 3. Bucket: overdue (`target_date < today`), due in the next 7 days, in progress (started), undated. 4. Output counts per bucket and "based on N rows". Exclude archived projects (note it).
Example: `Overdue 0 | Due <=7d 2 | In progress 1 | Undated 4 (7 rows)`.

## status <project>
1. `get_project_summary`, paged `list_work_items(project_id)`, `list_modules` (module health: past target_date with open items). 2. Leaf items only (no sub-items of others as parents: exclude items that have children, i.e. ids that appear as another row's `parent`). 3. Compute % done, overdue, in progress, blocked (`list_work_item_relations` for started items). 4. RAG per `model-mapping.md`, naming the rule. 5. Next gate: the earliest incomplete parent item and its `target_date`.

## portfolio
`status` summary line per active project plus stale (no update in 14 days) and orphans (items with no module).

## capture
Project given -> create there. Not given -> `Inbox` project; if absent, intake queue if enabled; if neither, do not write: list the active projects, resolve the backlog state of the likely one, show the call you would make and ask which project. `create_work_item(name, priority, state=<backlog>)`, never invent labels. Read back with the key.

## plan-project
1. Draft: charter (objective, KR, scope, out of scope), 3-6 modules with dates, labels, one cycle, items named `Step NN Verb object` with priority, dates, acceptance line, dependencies, parents per phase.
2. Show the preview and counts (projects 1, modules n, labels n, items n, relations n). Ask for go and the lead.
3. Create in order: project -> labels -> modules -> parents -> children (`parent_id`) -> module membership -> cycle membership -> relations. Run independent calls in parallel.
4. Read back: `get_project_summary` counts must match the preview; `list_work_item_relations` on one chain. Report mismatches.

## start / finish / hold / cancel
- start: state -> started group. Keep existing `start_date`.
- finish: comment with evidence first, then state -> completed, then read `completed_at`.
- hold: `blocked_by` relation to the blocker (create the blocker item if missing) plus a comment with the reason and owner.
- cancel: confirm, comment with reason, state -> cancelled.

## assign / lead / workload
`list_project_members` (agent members appear after `grant_agent_project_access`). Single item: `update_work_item(assignee_ids=[id])`. If the item already has an assignee other than the target, stop and ask (same rule as tool-map: confirm before replacing someone). Workload: one `list_work_items(assignees=[id])` per member, report open count and overdue count.

## block / risk / change
`add_work_item_relation(blocked_by)`; verify with `list_work_item_relations`. A risk is an item labelled `risk` with likelihood, impact and mitigation in the description. A change is a comment on the affected item: what, why, who approved.

## cycle-plan
`list_cycles(cycle_view=current)`; propose items by priority and dependency (a blocked item enters only with its blocker). `add_work_items_to_cycle` moves items out of any other cycle, so list who is moved. At cycle end: `transfer_cycle_work_items` after confirming.

## triage
`list_intake_work_items`; pending = status -2. Propose accept/reject/snooze/duplicate with a one-line reason each; apply only after confirmation. Accepted items land as work items in the project's default state.

## report / checkin / healthcheck
Weekly report: completed this week (`list_work_items(state_groups=[completed])`, completed_at in window), started, overdue, blocked, next week's due items, risks, decisions needed. Healthcheck adds scope drift (items created since the cycle began) and items without owner.

## close
1. Leaf items all completed or cancelled? If not, list them and stop. 2. `update_module(status=completed)` per module. 3. Retro comment on the last item: what went well, what did not, estimate vs actual dates, lessons. 4. Store lessons via the knowledge-management skill. 5. After the cycle end date and with confirmation: `archive_cycle`, then `archive_project`.

## doctor
Report-only. Checks: no assignee, no target_date, no label, started for more than 14 days, past target_date, empty module, cycle with no items, project without lead, items in the archived state of a module. Output counts and the worst 10 keys per check.

## Example output formats (illustrative: figures in status and doctor are placeholders; finish, block, triage and close use the real PMSKE2E scratch run)

**status (human)**
```
Decisions needed: none
PLANESKILL: 6 of 15 leaf items done (40%), 0 overdue, 2 in progress, RAG Green (no overdue items, no module past target). Based on 15 leaf rows of 18 items (3 parents excluded).
Next gate: [Build] PLANESKILL-2, target 2026-10-21.
```

**finish (agent)**
```
PMSKE2E-3 completed: evidence comment added, completed_at 2026-10-06T23:07:39Z
changed: PMSKE2E-3 -> Done, 1 comment
```

**block (agent)**
```
PMSKE2E-4 blocked_by PMSKE2E-3 (verified with list_work_item_relations)
changed: 1 relation
```

**triage (human)**
```
Decisions needed: 2 pending intake items in PMSKE2E
1. PMSKE2E-1 "Scratch intake A" (low): propose accept
2. "Scratch intake B" (medium): propose snooze until 2026-11-01
Nothing applied yet.
```

**doctor (human)**
```
Decisions needed: none
No assignee: 9 of 18 | No target date: 0 | Started > 14 days: 0 | Empty modules: 0 | Cycle with no items: 0
```

**close (human)**
```
Decisions needed: archive PMSKE2E? (reversible with unarchive_project)
All leaf items completed or cancelled: no, 2 open (PMSKE2E-4 Todo, PMSKE2E-3 In Progress). Stopped before archiving.
```
