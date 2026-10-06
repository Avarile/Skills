# Verb to tool map

Prefix: `mcp__claude_ai_cybernetics-project-management__`. Always start with ID resolution (below). `W` = write, needs the confirmation level in the last column. Details of each tool: `tool-catalogue.md`; behaviours: `quirks.md`.

## ID resolution (every verb)
1. `list_workspaces` -> slug (cache for the session).
2. `list_projects` -> project_id by name or identifier (case-insensitive; if two match, ask). Skip `archived_at != null` unless asked.
3. `list_states` -> state ids by **group**; `list_labels` -> label ids by name; `list_project_members` -> user ids.
4. Work item by key: `get_work_item(key=...)`.
Never guess an ID. If not found, say so.

| Verb | Calls in order | W | Confirm |
|---|---|---|---|
| plate | `get_current_user`; `list_work_items(assignees=["me"], state_groups=["backlog","unstarted","started"], order_by=target_date)` paged; split into overdue / due <=7d / in progress / undated | no | none |
| status (project) | `get_project_summary`; paged `list_work_items(project_id)`; `get_cycle` for the active cycle; `list_modules` | no | none |
| portfolio | `list_projects`; per active project: `get_project_summary` + `list_work_items(state_groups=[started])` | no | none |
| capture | resolve project (default `Inbox`, else intake) -> `create_work_item(name, project_id, priority, state backlog)` -> `get_work_item` | W | none for one item; count first for bulk |
| plan-project | preview only: charter text, modules, labels, cycle, item list with dates and dependencies -> on approval `create_project` -> `create_label` x n -> `create_module` x n -> parents `create_work_item` -> children (with `parent_id`) -> `add_work_items_to_module` per module -> `add_work_items_to_cycle` -> `add_work_item_relation` -> `get_project_summary` read-back | W | full preview, explicit go |
| start | `get_work_item` -> `update_work_item(state_id=<started>)`; set `start_date` only if empty and the user gave one | W | none |
| finish | `add_work_item_comment("YYYY-MM-DD Evidence: ...")` then `update_work_item(state_id=<completed>)`; read back `completed_at` | W | none; refuse without evidence |
| hold | `add_work_item_relation(blocked_by)` or comment; optional `On Hold` state | W | confirm if creating a state |
| cancel | `update_work_item(state_id=<cancelled>)` + reason comment | W | confirm |
| assign | `list_project_members` -> `update_work_item(assignee_ids=[...])` (REPLACES; include existing ids to keep, drop none unless asked) | W | confirm when replacing someone |
| lead | `update_project(project_lead_id)` | W | confirm |
| workload | paged `list_work_items(assignees=[uuid], open groups)` per member | no | none |
| block / unblock | `add_work_item_relation(blocked_by)`; `list_work_item_relations` read-back. No tool removes a relation. | W | none; say unblock is not possible via MCP |
| risk / change | `create_work_item` with label `risk` or a comment on the affected item | W | none |
| cycle-plan | `list_cycles`, `create_cycle` (both dates), `add_work_items_to_cycle` (moves items), later `transfer_cycle_work_items` | W | count first |
| triage | `list_intake_work_items` -> `triage_intake_work_item(action)` | W | confirm reject/duplicate; accept needs project admin |
| report / checkin / healthcheck | read-only composition of status + `list_work_item_activities` for the week | no | none |
| close | all leaf items completed/cancelled? -> `update_module(status=completed)` per module -> retro comment -> `archive_cycle` (after end) -> `archive_project` | W | confirm each archive |
| link / trace | `add_work_item_link(url, title)` to knowledge entries; `list_work_item_links` | W | none |
| doctor | read-only: items without assignee, target_date, label; past-due started items; empty modules; cycles with no items | no | none |
| agent-run | see `agent-protocol.md` | W | per protocol |

## Read-back rule
After every write, re-read with `get_work_item` / `list_work_item_relations` / `get_project_summary` and report what the server holds, not what you sent.
