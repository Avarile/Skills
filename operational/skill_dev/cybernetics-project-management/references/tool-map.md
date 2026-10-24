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
| find | key `ABC-12`: `get_work_item(key)`; words: `list_work_items(project_id, name_contains)` (state, assignee in the row) or `search_work_items(query, project_id)` then `get_work_item`; add `list_work_item_relations` + `get_work_item` per blocker if asked | no | none |
| comment | `add_work_item_comment` / `list_work_item_comments` (newest first) / `update_work_item_comment` / `delete_work_item_comment`; escape HTML; agent mode prefix `[handle]` | W | none to add; confirm edit or delete of a comment the user did not write |
| history | `list_work_item_activities(per_page=100)` read to the last page (oldest first); add `list_work_item_comments`; project window: loop `list_work_items(updated)` then activities per item, say what was sampled | no | none |
| estimate | `get_estimate` (404 = none) -> `create_estimate(type)` -> `create_estimate_points` (<=20) -> `update_project(estimate_id)` -> `update_work_item(estimate_point_id)`; edits: `update_estimate`, `update_estimate_point`; `list_estimate_points` and sort by `key` | W | confirm create, activate, or changing a point value used by items |
| members | `list_project_members`, `list_workspace_members`; `add_project_member`, `update_project_member`, `remove_project_member` (project admin); `list_workspace_invitations`; never `invite_workspace_member` unasked | W | human mode only; name current admins and the change; never the token owner or lead |
| workflow | `list_states` / `create_state` / `update_state`; `list_labels` / `create_label(parent_id)` / `update_label`; resolve done by group | W | human mode only; confirm; renaming affects every item |
| agents | `list_agents(status=all)`, `get_agent`, `create_agent` (Markdown fields, workflow steps, `project_ids`), `update_agent(change_note)` (status, accept_assignments, definition), `list_agent_revisions`, `get_agent_context(version)`, `grant_agent_project_access`, `revoke_agent_project_access`, `archive_agent` | W | human mode only; confirm; re-assign open items before archive or revoke |
| restore | `list_projects` (archived_at set), `list_archived_cycles`, `list_archived_modules` -> `unarchive_project` / `unarchive_cycle` / `unarchive_module`; read back | W | confirm |

## Read-back rule
After every write, re-read with `get_work_item` / `list_work_item_relations` / `get_project_summary` and report what the server holds, not what you sent.
