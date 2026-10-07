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

## find
Key (`ABC-12`): `get_work_item(key)`. Words: `list_work_items(project_id, name_contains)`, or `search_work_items` with a project when known (it is not key-aware, quirk 27). Print key, name, state, assignee, target date, parent. With "blockers": `list_work_item_relations` gives ids only, so `get_work_item` each `blocked_by` id and say which are not completed.

## comment
Add: `add_work_item_comment` with escaped HTML; agent mode starts with `[handle]`. List is newest first. Editing leaves `edited_at` null, so say "edited" yourself if it matters. Confirm before editing or deleting a comment someone else wrote.

## history
`list_work_item_activities(per_page=100)`; oldest first, so read to the last page (`next_page_results`). It has state, assignee, label, date and relation changes but no comments or links; read `list_work_item_comments` for those. Print `date actor: field old -> new`. For a project-wide "this week" view, state how many items were sampled.

## estimate
1. `get_estimate`: 404 means none. 2. Preview the scale (for example 1, 2, 3, 5, 8, 13) and wait. 3. `create_estimate`, `create_estimate_points`, `update_project(estimate_id)`. 4. `update_work_item(estimate_point_id)` per item (count first). 5. Report points by module from `list_work_items(module_id)`, not from module counters (quirk 43). Changing a point's value changes it for every item that uses it.

## members (human mode only)
`list_project_members` and `list_workspace_members` first; say who is admin. Never change the token owner's or the project lead's role, and never demote the last admin (quirk 36). Roles: admin, member, guest. Do not add archived agents (quirk 37). Adding an agent to a project goes through `agents`, not here.

## workflow (human mode only)
States: `create_state(name, group, color)`; the group decides progress. Never rename the state that holds "done" to something else without saying; resolve done by group. Labels: nest with `parent_id`; renaming or recolouring touches every item that carries it. Show the plan, wait for yes, read back with `list_states` / `list_labels`.

## agents (human mode only)
- **Create:** Markdown for every `_md` field, 3-6 workflow steps, `requires_approval` on steps that change shared state, `project_ids` for access, a handle `^[a-z0-9][a-z0-9_-]{1,47}$`. No secrets. Preview the definition first.
- **Change:** `update_agent` with `change_note`. Definition changes bump the version and write a revision; pause and accept_assignments do not (quirk 33). `get_agent_context(version)` pins an older version.
- **Pause or stop new work:** `status=paused` or `accept_assignments=false`; new assignments are then rejected with 400 (quirk 32); existing items stay.
- **Access:** `grant_agent_project_access` / `revoke_agent_project_access`. After a revoke, assigning silently drops the assignee (quirk 34); after any assignment read back `assignees`.
- **Retire:** list `list_agent_work_items`, re-assign or finish open items, then `archive_agent` (assignments stay otherwise, quirk 21).

## restore
Find the object (`archived_at` in `list_projects`; `list_archived_cycles`; `list_archived_modules`), confirm, then `unarchive_*`, then read back counts. An archived project shows 0 items until restored (quirk 1); restoring brought back all items (quirk 45).

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
