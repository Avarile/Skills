# CRM (the `cybernetics` MCP server)

A Twenty-style CRM. Unlike `cybernetics-data`, it has no direct per-object tools. Everything goes through three meta-tools, and there are ~300 operations behind them.

## Contents
- How to call it (the 3-step pattern)
- Objects worth knowing
- Tool name cheat-sheet
- Filter syntax
- Workflows: find, notes, tasks, pipeline, email, calendar
- Advanced areas and `load_skills`
- Guardrails

## How to call it

1. **`get_tool_catalog`**: the server requires this before `learn_tools`/`execute_tool`. **Always pass a narrow `categories` filter** (e.g. `["ACTION"]`), because the unfiltered catalog lists ~300 tools and floods the context. Categories: `DATABASE_CRUD`, `ACTION`, `WORKFLOW`, `METADATA`, `VIEW`, `DASHBOARD`, `NAVIGATION_MENU_ITEM`, `WEBHOOK`, `LOGIC_FUNCTION`. One narrow call per session is enough; use the cheat-sheet below for CRUD names.
2. **`learn_tools`** with **all** the tool names you need in a single array. It returns each tool's argument schema (composite field shapes such as name, emails, phones, currency amounts included). Never guess arguments.
3. **`execute_tool`** with `toolName` and `arguments` matching that schema.

Discovering the data model: `list_object_metadata_names` gives the 28 objects; `get_object_metadata` (via `execute_tool`, with `includeFields: true`) returns fields for an object. `search_help_center` answers "how does the CRM do X" questions.

## Objects worth knowing

| Object (plural) | Use |
|---|---|
| `people` | Contacts/leads/customers |
| `companies` | Organisations |
| `opportunities` | Deals/pipeline, with stage and amount |
| `notes` + `note_targets` | Free-text notes; a note attaches to records through `note_targets` |
| `tasks` + `task_targets` | CRM follow-ups; attach to records through `task_targets` |
| `calendar_events` | Synced calendar events (read-only in practice; create with `create_calendar_event`) |
| `messages`, `message_threads`, `message_participants` | Synced email (read/search; don't try to create) |
| `call_recordings` | Recorded calls |
| `attachments` | Files on records |
| `timeline_activities` | Activity history on records |
| `message_campaigns`, `message_lists`, `message_list_members` | Outreach lists/campaigns |
| `products`, `prices`, `subscriptions`, `transactions` | Billing objects (not personal finance; that lives in cybernetics-data) |
| `workspace_members` | Users of the CRM |
| `dashboards`, `blocklists` and calendar/message association objects | Rarely needed directly |

Field names differ per object: get the real ones from `get_object_metadata` / `learn_tools` before writing.

## Tool name cheat-sheet

These are the exact names (from the server's catalog on 2026-09-19). Object names are singular for `_one_` operations and plural for `_many_`.

- `find_many_<plural>`, `find_one_<singular>`, `group_by_<plural>` exist for every object.
- `create_one_<singular>`, `create_many_<plural>` (max 20 per call), `update_one_<singular>`, `update_many_<plural>` (same values to *every* match), `upsert_many_<plural>` (max 20, different values per record), `delete_one_<singular>`, `delete_many_<plural>` exist for: `person/people`, `company/companies`, `opportunity/opportunities`, `note/notes`, `note_target/note_targets`, `task/tasks`, `task_target/task_targets`, `attachment/attachments`, `call_recording/call_recordings`, `timeline_activity/timeline_activities`, `message_campaign/message_campaigns`, `message_list/message_lists`, `message_list_member/message_list_members`, `product/products`, `price/prices`, `subscription/subscriptions`, `transaction/transactions`, `blocklist/blocklists`.
- Synced/system objects (`calendar_event(s)`, `message(s)`, `message_thread(s)`, `message_participant(s)`, the association objects, `workspace_member(s)`, `dashboard(s)`) only have `find_*`, `group_by_*` and `delete_*`.
- Actions: `send_email`, `draft_email`, `create_calendar_event`, `search_help_center`, `navigate_app`.
- Metadata: `get_object_metadata`, `get_field_metadata`, `create_/update_/delete_object_metadata`, `create_/update_/delete_field_metadata` and batch variants.
- Views: `get_views`, `get_view_query_parameters`, `upsert_complete_view`, ... Dashboards: `create_complete_dashboard`, `list_dashboards`, `get_dashboard`, `add_dashboard_widget`, ... Workflows: `list_workflows`, `create_complete_workflow`, `activate_workflow_version`, `get_workflow_run`, ... Webhooks: `list_webhooks`, `create_webhook`, ...

All deletes are **soft** (hidden, reversible), but still tell the user what was deleted.

## Filter syntax (find / update_many / delete_many)

Filters are **top-level arguments**, one per field, not wrapped in a `filter` object. Do not put a bare operator like `ilike` at the top level.

```
find_many_people   { name: { firstName: { ilike: "%dana%" } }, limit: 10 }
find_one_company   { id: { eq: "<uuid>" } }
find_many_opportunities { and: [ { stage: { eq: "PROPOSAL" } }, { amount: { amountMicros: { gt: 5000000000 } } } ], orderBy: [...], limit: 20 }
```

(Field names and enum values above like `stage`/`PROPOSAL` are illustrative; read the real ones from the metadata.) Operators include `eq`, `ilike`, `gt/gte/lt/lte`, `in`, null checks; combine with `and` / `or` / `not`. Page with `limit` + `offset`. Composite fields (person name, currency amount, emails) filter through their sub-fields. Confirm exact operators and enum values (stage names!) from `learn_tools` output before running.

Currency fields are composite: an amount in `amountMicros` (major units x 1,000,000) plus a currency code. Verify the shape with `learn_tools` on first use, and show the user normal currency values, not micros.

## Workflows

**Find a person or company**
- `find_many_people` / `find_many_companies` with `ilike` on name (and email/domain if given). If several match, list them (name, company, email) and ask which. Report what you found; don't guess.

**Log a note about a meeting/call** ("note for Dana at Acme: agreed pilot in October")
1. Find the person (and their company/opportunity if relevant).
2. `create_one_note` (title + body).
3. Attach it with `create_one_note_target`, linking the note to the person/company/opportunity. Call `learn_tools` on both `create_one_note` and `create_one_note_target` (one call) to get the exact fields.
4. Confirm: what was written and which records it's attached to.

**CRM follow-up task** ("remind me to send Dana the proposal Friday")
- `create_one_task` (title, due date, status) then `create_one_task_target` to attach it to Dana (and the opportunity). Use only when it's tied to a person/company/deal; personal or project work goes to `cybernetics-data.tasks`.

**Pipeline reporting** ("what's in my pipeline?")
- `group_by_opportunities` by stage with SUM of amount (and COUNT). For the list, `find_many_opportunities` filtered to open stages, ordered by amount or close date. Report totals in normal currency units.

**Email**
- Default to **`draft_email`**: it saves a draft the user reviews in their mail client. Use `send_email` only when the user explicitly says to send and you've shown the final recipients, subject and body. It requires permission, and sent mail can't be recalled.
- Recipients come from what the user said or the CRM record. Don't add recipients they didn't mention.

**Calendar**
- `create_calendar_event` with `sendInvitations: false` by default (event is created with no attendees, nobody is notified). Only set it `true` after the user agrees to notify named attendees. Read existing events with `find_many_calendar_events`.

**Bulk updates**
- Run the equivalent `find_many_*` with the same filter first, report the count and a sample, get confirmation, then `update_many_*` / `delete_many_*`. Use `upsert_many_*` when each record needs its own values (max 20 per call; batch and report progress).

## Advanced areas and `load_skills`

For anything beyond record CRUD, call `load_skills` with the matching name before starting, and follow the instructions it returns. Available skills (from `list_skills`): `data-manipulation`, `research`, `workflow-building`, `dashboard-building`, `view-building`, `view-filters-and-sorts`, `metadata-building`, `custom-objects-cleanup`, `workspace-demo-seeding`, `code-interpreter`, `xlsx`, `pdf`, `docx`, `pptx`. Refresh the list with `list_skills` if one seems missing.

- Data model changes (`METADATA` tools: creating/deleting objects or fields) are structural and can destroy data: only on explicit request, after describing exactly what will change.
- Dashboards, views and workflows: load the matching skill first; workflows can send email or change records automatically, so confirm before `activate_workflow_version`.

## Guardrails

- Outbound actions (`send_email`, `create_calendar_event` with invitations, activating workflows, webhooks) affect other people or systems: confirm first.
- Don't put secrets (passwords, API tokens) into CRM notes, emails or task text.
- The CRM holds other people's personal data. Use it to serve the user's request; don't compile or export more than was asked for.
- A `429`/rate-limit or transient error: wait and retry once, then report.
