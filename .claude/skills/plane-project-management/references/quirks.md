# Quirks of the Plane MCP (probed 2026-10-07)

Each line says how it was established. "Tested" = observed live, "schema" = read from the tool schema only, "untested" = could not be checked.

| # | Quirk | Evidence | Rule for the skill |
|---|---|---|---|
| 1 | Items of an **archived** project are invisible to `list_work_items` (E2EWEB: summary says 26 items, `list_work_items(project_id)` returns total 0). `list_projects` still shows it with `archived_at`. Its intake queue is still readable. | tested | Say "archived, N items per summary" instead of reporting 0. Never report an archived project as empty. |
| 2 | `list_work_items` pages with `total` + `next_offset` (limit 5 of 18 returned next_offset 5; last page returns null). | tested | Loop until `next_offset` is null; state the row count. |
| 3 | List tools using cursors (`list_projects`, `list_intake_work_items`, ...) return a `next_cursor` even on the last page. The reliable flag is `next_page_results`. | tested | Stop on `next_page_results: false`. |
| 4 | `add_work_item_relation(work_item_id=X, relation_type=blocked_by, related=[Y])` means **X is blocked by Y**. The response echoes the *related* items, not X. Y then lists X under `blocking`. | tested | Read back with `list_work_item_relations` on X. |
| 5 | `create_state` accepts any group (tested `started`); slug is auto-derived (`blocked`); a state with no items deletes cleanly. Behaviour with items assigned to a custom state was not exercised. | tested (create/delete), untested (items) | Resolve "done" by `group == completed`, never by the name "Done". |
| 6 | Dates passed to `create_cycle` as `YYYY-MM-DD` are stored as UTC instants (`2026-10-07T13:00:01Z` for Oct 8 Melbourne, end `...12:59:00Z`) and the cycle's `timezone` is `UTC`. Work item dates stay plain `YYYY-MM-DD`. | tested | Convert cycle dates to the project timezone when reporting. |
| 7 | Intake items not yet accepted sit in state group `triage`, which is **not** in the `state_groups` filter enum. Intake `status`: -2 pending, -1 rejected, 0 snoozed, 1 accepted, 2 duplicate. | tested | Read the queue with `list_intake_work_items`, not `list_work_items`. |
| 8 | `update_work_item` treats null as "unchanged": no field can be cleared (target_date, parent, estimate). `assignee_ids` and `label_ids` replace the whole set. | schema | Always `get_work_item` first and resend the labels or assignees you keep. Tell the user a clear is not possible via MCP. |
| 9 | `get_estimate` returns a 404 error when the project has none. | tested | Treat 404 as "no estimate", not a failure. |
| 10 | `get_cycle` counts include parent items. A cycle with 3 parents and 15 steps reports `total_issues: 18`. | tested | Report "leaf items" when parents are in the cycle. |
| 11 | `search_work_items` returns only id, name, sequence_id, project identifier. | tested | Follow with `get_work_item` for state. |
| 12 | `list_work_items` rows carry `key`, `state_name` and `state_group`; `create_work_item` / `update_work_item` responses carry the state UUID only. | tested | Do not print state names from write responses; use the list row. |
| 13 | `archive_cycle` only after the end date, `archive_module` only when completed/cancelled, `transfer_cycle_work_items` only from an ended cycle. | schema | Check status before offering archive. |
| 14 | Intake can only be created when the project has `intake_enabled`. PLANESKILL has it off. | schema + project record | Offer to enable intake before `create_intake_work_item`. |
| 15 | Comments are stored as given HTML with `access: INTERNAL`. | tested | Use `<p>`, `<ul>`, `<code>` only. |
| 16 | Permission limits for guests or non-admins were **not tested**: this workspace has one member (admin). | untested | Say so in reports; surface 403 errors verbatim. |
| 17 | At first probe the workspace had no agents. `list_agents` defaults to `status=active`, so it also looks empty when only archived agents exist. | tested | Always pass `status=all` when checking whether an agent exists. Agent tools were later exercised in the Step 12 run (#18-26). |

## Added by the Step 12 end-to-end run (2026-10-07, scratch project PMSKE2E, archived afterwards)

| # | Quirk | Evidence | Rule for the skill |
|---|---|---|---|
| 18 | Leaving a completed state clears `completed_at` (Done -> In Progress returned `completed_at: null`). Entering completed sets it server-side. | tested | Say that reopening clears the completion time. |
| 19 | Comments made through this MCP are attributed to the **token owner** (`actor` = the human), even when written "as" an agent. The agent has no author identity via the MCP. | tested | In agent mode prefix comments with the agent handle, e.g. `[scratch-qa] ...`. |
| 20 | `create_agent` with `project_ids` makes the bot a project member at once (it appears in `list_project_members` with `is_bot: true`) and it can be passed as `assignee_ids` on `create_work_item`. `get_agent_task_brief` returned the definition plus the item and wraps item text in `BEGIN/END WORK ITEM DATA` markers. `list_agent_work_items` returned the item. | tested | Pass the agent's `bot_user_id`; trust the brief's data markers. |
| 21 | `archive_agent` sets status `archived` and empties `project_ids`, but the items assigned to it stay assigned (`assigned_open_count` 1 after archive). | tested | Re-assign open items before archiving an agent. |
| 22 | `archive_cycle` before the cycle is completed returns 400 "Only completed cycles can be archived"; `archive_module` before status completed/cancelled returns 400. `update_module(status=completed)` then `archive_module` succeeds. | tested | Complete the module first. A cycle cannot be archived early, so `close` leaves it and says so. |
| 23 | `create_cycle` with a start date of today stores start = now (`23:06:39Z`), unlike a future start date (`13:00:01Z` for Melbourne midnight). | tested | Expect a start-of-day shift only for future dates. |
| 24 | Accepting an intake item puts it in the project's default state (Backlog) and it then appears in `list_work_items`; a snoozed item stays in group `triage` and does not appear. `snoozed_till` is echoed back. | tested | After accept, read back with `get_work_item`. |
| 25 | `create_project(intake_enabled=true)` works at creation time (intake view on, `create_intake_work_item` succeeded). | tested | Enable intake at creation when the user wants a queue. |
| 26 | `archive_project` returns `{success: true}`; the project then shows `archived_at` in `list_projects`. | tested | Confirm before archiving; it is reversible with `unarchive_project`. |
