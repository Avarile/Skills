# Model mapping: PDCA / OKR onto Plane

Plane has no goal or phase object, so some concepts are conventions. Conventions are marked **(convention)**.

| Concept | Plane object | Notes |
|---|---|---|
| Organisation | Workspace (`cybernetics`) | one today |
| Goal / Objective + Key Results | **(convention)** first lines of the project `description`: `Objective: ...` then `KR1: ...` (max 3) | Plane has no OKR object. Stickies are personal and must not hold goals. |
| Project (one PDCA cycle moving a KR) | Project, identifier = 3-12 uppercase chars | Lead = `project_lead_id`. One accountable lead. |
| PDCA phase / deliverable group | Module (status `planned` -> `in-progress` -> `completed`) | Plan/Do/Check/Act, or domain phases such as Discovery, Design, Build, Verify, Rollout. Module dates bracket its items. |
| Phase gate / parent task | Parent work item named `[Phase] ...` with the step items as sub-items | Gate acceptance goes in its description. |
| Task | Work item named `Step NN Verb object` | `NN` is the order; PDCA tag optional as a label |
| Iteration / timebox | Cycle | Parents and leaves both count in cycle totals (quirks #10). |
| Task type | Labels (`skill`, `docs`, `eval`, `mcp`, `risk` here; per project) | Create labels before use; `label_ids` replaces the set. |
| Dependency | `blocked_by` relation | X blocked_by Y: see quirks #4. |
| Assignment | `assignee_ids` (human member or agent `bot_user_id`) | At most one assignee per item by convention. |
| Estimate | Estimate system + `estimate_point_id` | Optional; create only on request. |
| Evidence | Dated comment: `YYYY-MM-DD Evidence: ...` | Required when finishing. |
| Risk / change / blocker log | Work item with label `risk` (or comment on the affected item) | No log table exists. |
| Retro / lessons | Comment on the closing item plus the knowledge-management skill | Plane pages are not reachable via MCP. |
| Inbox | Intake queue if enabled, else a project titled `Inbox` | |

## States
Resolve by **group**, never by name.

| Verb | Target group | Default state in new projects |
|---|---|---|
| capture | backlog | Backlog (default) |
| ready | unstarted | Todo |
| start | started | In Progress |
| finish ("done") | completed | Done |
| cancel | cancelled | Cancelled |
| hold | started + `blocked_by` relation + comment | no dedicated state; offer to create `On Hold` (group started) once, with confirmation |

`completed_at` is set by the server on entering a completed state (observed on Step 01). Leaving it is not tested; re-read after reopening.

## Dates
`start_date` and `target_date` are real fields (`YYYY-MM-DD`), so the cybernetics-data `Due:` line convention is not needed. Overdue = `target_date` before today and state group in backlog/unstarted/started. Today comes from the conversation.

## Statuses and RAG
`status` and `portfolio` compute from `list_work_items` rows (leaf items only; parents excluded):
- % done = completed / (all - cancelled)
- overdue = target_date < today and not completed/cancelled
- Red: any overdue item with priority urgent/high, or a started item blocked by an open item for more than 3 days; Amber: any overdue item or module past its target_date with open items; Green otherwise.
State which rule fired and the number of rows used.
