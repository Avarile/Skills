# Tool catalogue: cybernetics-project-management (Plane)

Prefix every name with `mcp__claude_ai_cybernetics-project-management__` (load with ToolSearch `select:`). Verified 2026-10-07 against the live schemas. Every call takes `workspace_slug` (here `cybernetics`); project-scoped calls also take `project_id` (UUID). `R` = required args beyond those two.

Count: 96 tools (counted from the server's tool list) in 11 groups.

## Identity and workspace
| Tool | Purpose | R / notes |
|---|---|---|
| list_workspaces | workspaces + slug + role | none |
| get_current_user | token owner | none |
| list_workspace_members | members + role | admin/member only |
| list_workspace_invitations | pending invites | admin only |
| invite_workspace_member | record an invite (sends no email) | email; role admin/member/guest |
| cancel_workspace_invitation | cancel | invitation_id |

## Projects
| Tool | Purpose | R / notes |
|---|---|---|
| list_projects | id, identifier, name, archived_at | cursor, per_page<=100. Includes archived. |
| get_project | full detail | |
| get_project_summary | counts (members, states, labels, cycles, modules, issues, intakes, pages) | `fields` subset |
| create_project | new project with 5 default states | name, identifier `^[A-Z0-9]{1,12}$`; project_lead_id, timezone, cycles/modules/intake flags |
| update_project | settings; activates estimate via estimate_id | not for archived |
| archive_project / unarchive_project | read-only hide / restore | |
| delete_project | PERMANENT | needs confirm_identifier; never run unasked |
| list_project_members / add_project_member / update_project_member / remove_project_member | membership | role admin/member/guest |

## States and labels
| Tool | R / notes |
|---|---|
| list_states | id, name, group (backlog, unstarted, started, completed, cancelled; intake adds `triage`) |
| create_state | name, group, color `#RRGGBB`; optional default |
| update_state | name, color, group, default |
| delete_state | refused for the default state or states holding items |
| list_labels / create_label / update_label / delete_label | create: name; optional color, parent_id; delete strips it from every item |

## Work items
| Tool | Purpose | R / notes |
|---|---|---|
| list_work_items | server-side filtered list, cross-project if project_id omitted | filters AND-ed, values within one filter OR-ed: assignees (`me`/`none`/uuid), created_by, state_groups, state_ids, priorities, label_ids, module_id, cycle_id, parent_id (`none` = top level), due_before/after, start_before/after, name_contains, estimate_point_ids. order_by incl. target_date, priority, sequence_id. limit<=100, offset. Returns total, next_offset. |
| search_work_items | quick name/key search | query; limit<=50. Returns only id, name, key parts. |
| get_work_item | expanded state/labels/assignees | key `ABC-12` or project_id+work_item_id |
| create_work_item | | project_id, name; description_html, state_id, priority (urgent/high/medium/low/none), assignee_ids, label_ids, parent_id, start_date, target_date (YYYY-MM-DD), estimate_point_id |
| update_work_item | partial | assignee_ids and label_ids REPLACE the set. A null argument means "unchanged", so a field cannot be cleared through this tool. |
| delete_work_item | creator or project admin | |
| list_work_item_activities | field-level history | |
| add_work_item_comment / list_work_item_comments / update_work_item_comment / delete_work_item_comment | comments | comment_html |
| add_work_item_link / list_work_item_links / update_work_item_link / delete_work_item_link | external links | url, title |
| list_work_item_attachments / delete_work_item_attachment | list and delete only; no upload | |
| add_work_item_relation / list_work_item_relations | list returns ids only (no key or state), see quirk 29. relation_type: blocking, blocked_by, duplicate, relates_to, start_before, start_after, finish_before, finish_after | related_work_item_ids[] |

## Cycles
list_cycles (cycle_view all/current/upcoming/completed/draft/incomplete), get_cycle (counters by state group), create_cycle (both dates or neither), update_cycle, archive_cycle (only after end date), unarchive_cycle, list_archived_cycles, delete_cycle (items kept), add_work_items_to_cycle (moves from any other cycle), remove_work_item_from_cycle, list_cycle_work_items, transfer_cycle_work_items (unfinished items to another cycle, source must have ended).

## Modules
list_modules, get_module, create_module (status backlog/planned/in-progress/paused/completed/cancelled, lead_id, member_ids, dates), update_module (member_ids REPLACES), archive_module (only completed/cancelled), unarchive_module, list_archived_modules, delete_module, add_work_items_to_module (an item may be in several), remove_work_item_from_module, list_module_work_items.

## Estimates
get_estimate (404 when none), create_estimate (type points|categories), update_estimate, delete_estimate, create_estimate_points (max 20: key, value), list_estimate_points, update_estimate_point, delete_estimate_point. Activate with `update_project(estimate_id=...)`, then `update_work_item(estimate_point_id=...)`.

## Intake
create_intake_work_item (project needs intake_enabled), list_intake_work_items, get_intake_work_item, triage_intake_work_item (work_item_id = the intake row's `issue`; accept, reject, snooze+snoozed_till, duplicate+duplicate_of_id, pending; project admin), delete_intake_work_item.
Intake `status` codes observed: -2 pending, -1 rejected, 0 snoozed, 1 accepted, 2 duplicate.

## Agents (agentic members)
list_agents (status active/paused/archived/all, capability, search), get_agent (includes bot_user_id), get_agent_context (prompt-ready markdown, optional version), get_agent_task_brief (definition plus one assigned item), list_agent_work_items (state_group open/...), list_agent_revisions, create_agent (admin; handle `^[a-z0-9][a-z0-9_-]{1,47}$`, workflow steps with requires_approval), update_agent (status active/paused, accept_assignments, change_note), archive_agent, grant_agent_project_access, revoke_agent_project_access.

## Stickies
create_sticky, list_stickies, update_sticky, delete_sticky. Personal to the token owner.

## Not available
Pages (counted in the summary but no tool), file upload, time tracking, issue types, saved views, bulk work-item update (one call per item), clearing a field.
