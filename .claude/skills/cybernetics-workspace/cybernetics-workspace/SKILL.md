---
name: cybernetics-workspace
description: Operating manual for the user's two MCP servers - cybernetics-data (personal database "data-centre" holding knowledge, finance, goals/projects/tasks) and cybernetics (the CRM - people, companies, opportunities, notes, CRM tasks, calendar, email). Use this whenever the user mentions knowledge-base entries, things to remember or document, how-tos, credentials, expenses, income, transactions, payees, accounts, balances, budgets, categories, tags, goals, projects, tasks, priorities, progress, deadlines, clients, leads, deals, opportunities, contacts, companies, follow-ups, meeting notes, or emailing/scheduling with someone - even if they never name a server. It says which server and table to use, how to call each, and which conventions and guardrails apply.
---

# Cybernetics Workspace

The user runs their personal operating system across two MCP servers. Picking the wrong server or table quietly creates clutter in the wrong place, so route first, then act.

## The two servers

**`cybernetics-data`** is a Teable-style database. Direct tools: `list_spaces`, `list_bases`, `list_tables`, `get_table_schema`, `list_views`, `query_records`, `get_record`, `create_records`, `update_record`, `delete_records`, plus schema tools (`create_table`, `create_field`, ...).
- Space `spc1V7zXKTD999538hf` ("Work"), base `bseJEuE54y5caWO0Xc8` ("data-centre"). Everything personal lives in this one base, so skip discovery and go straight to the table.
- Cells are keyed by **field ID** (`fldXXXX`), never by field name.

**`cybernetics`** is the CRM (a Twenty-style app with 28 objects). It exposes ~300 operations through a 3-step meta-pattern instead of direct tools: `get_tool_catalog` -> `learn_tools` -> `execute_tool`. Details in `references/crm.md`.

If a tool isn't loaded yet, load it with `tool_search` first (one call with several tool names, e.g. "cybernetics-data query_records get_table_schema create_records update_record").

## Routing table

| The request is about... | Server | Where | Read first |
|---|---|---|---|
| Knowledge, notes-to-self, how-tos, reference material, credentials/access docs | cybernetics-data | `knowledges`, `knowledge_type` | `references/knowledge.md` |
| Money: expenses, income, transfers, payees, accounts, budgets, categories, tags, balances | cybernetics-data | `finance_*` (6 tables) | `references/finance.md` |
| Goals, projects, tasks, priorities, progress, deadlines, who is assigned | cybernetics-data | `goals`, `projects`, `tasks` (+ `contacts` for assignees) | `references/projects.md` |
| Customers/leads, deals, companies, meeting notes about people, follow-ups, calendar, email | cybernetics (CRM) | people, companies, opportunities, notes, tasks, ... | `references/crm.md` |

Read only the reference file for the domain at hand. For requests spanning domains, read each relevant one.

## Same word, two systems

Several names exist in both servers. Resolve them with these defaults, and state the choice in one line when there was any real ambiguity.

- **"task"**: default to `cybernetics-data.tasks` (the user's own work: projects, goals, personal to-dos). Use CRM tasks only when the task is tied to a person, company or deal ("follow up with Acme", "send proposal to Dana"). If genuinely unclear on a write, ask one short question before creating.
- **"contact" / "person"**: `cybernetics-data.contacts` are internal-facing people used as project leads and task assignees. CRM `people` are the relationship/sales records. For sales, clients, leads or outreach use the CRM. For "assign this to X" use `contacts`.
- **"company"**: CRM `companies` is the source of truth for clients and prospects. (`cybernetics-data` also has a `companies` table that is out of scope here; leave it alone.)
- **"transaction"**: money movements are always `finance_Transactions` in cybernetics-data. CRM `transactions` and `subscriptions` are billing objects, only relevant if the user explicitly talks about CRM billing or Stripe-style subscriptions.
- **"note"**: meeting or interaction notes about a person/company/deal go to CRM `notes`. Durable knowledge the user wants to keep and find later goes to `knowledges`.

There are no foreign keys between the servers. When a finance payee is also a CRM company, or a task relates to a CRM deal, keep the names identical and mention the relationship in the `context`/`Notes` text.

## Working with cybernetics-data

1. **Use the reference file's IDs** (table and field IDs are cached there), then verify cheaply. If a write fails with an unknown-field or option error, the schema has drifted: re-run `get_table_schema` for that table and continue with the fresh IDs.
2. **Resolve links before writing.** Link fields need the target record's ID, not its name. Find it with `query_records` (`search` = the name, `projection` = the primary field). If nothing matches, do not invent a record; tell the user and offer to create it (payees, categories, tags and knowledge types are cheap to create once confirmed).
   **Link values:** Teable's convention is an object with the record ID for a many-to-one link (`{ "id": "recXXXX" }`) and an array of those objects for many-to-many links (Tags, `related_knowledge`). The first time you write a link in a session, read one existing linked record with `get_record` and mirror the shape you see; if a write is rejected, fix the shape and retry.
3. **Write only writable fields.** Computed fields (`created_at`, `updated_at`, `id`, Signed Amount, balances, rollups, formulas, `Scope` on transactions/budgets) reject writes. Write only one side of a link pair; the reverse field updates itself.
4. **Single-select values must match an existing option name exactly** (case and punctuation included). The schemas disallow auto-creating new options, so a typo fails rather than creating junk.
5. **Read back after writing** when the result matters (money, deadlines, status changes) and show the user the created/changed values, not just "done".

`query_records` has no filter argument. It offers `search` (full-text), `viewId` (apply a saved view's filter and sort), `skip`/`take` and `projection`. So:
- Look for an existing filtered view with `list_views` before paging through everything.
- Use `search` for names and keywords.
- Otherwise page with `take` (use `hasMore`/`nextSkip`) and filter on your side; always pass `projection` to keep responses small.
- For date-range or aggregate questions over many rows (monthly totals, category breakdowns), prefer the computed fields (`Actual Spent`, `Current Balance`) when they answer it; otherwise pull the needed rows once and calculate, and say how many rows the answer is based on.

## Conventions for all cybernetics-data tables

- **Soft delete by default.** Most tables carry `is_active` (checkbox, default true) and `deleted_at` (date). To "delete" something, set `is_active` = false and `deleted_at` = today, instead of calling `delete_records`. When listing, skip rows where `is_active` is false unless the user asks for archived items. Use hard `delete_records` only on an explicit "permanently delete", and tell the user what was removed (Teable keeps a restorable trash).
   *(The finance tables have no `is_active`; accounts use `Active`. For finance, ask before hard deleting anything.)*
- **Dates** are `YYYY-MM-DD`, timezone Australia/Melbourne. Take "today" from the conversation's date; never guess.
- **Money** uses the `$` symbol with 2 decimals. Never convert currencies or add a currency name the user didn't state.
- **`context` fields are Markdown.** Write structured, scannable Markdown there (headings, bullets), not one long paragraph.

## Guardrails

- **Secrets stay out of chat.** `system_info.access_token` (the Teable API token) and `knowledge_type.credentials` hold sensitive values. Do not read, echo or copy them unless the user asks for that specific value, and never write a secret into `context`, `Notes`, a CRM note, an email or this skill. `system_info`, `system_status`, `auditlog`, `table_references`, `template_table` and `project_frameworks` are system tables: read-only unless asked.
- **Confirm before anything hard to undo:** bulk updates/deletes (`update_many_*`, `delete_many_*`, multi-record `delete_records`), schema changes (`delete_field`, `delete_table`, CRM `*_metadata`), and every outbound CRM action. `send_email` is irreversible; prefer `draft_email` and let the user send. `create_calendar_event` with `sendInvitations: true` emails real people; default to false and ask first.
- **Before any bulk write, count first.** Run the matching `find_many_*` (CRM) or `query_records` (data) and report how many rows will change.
- **Attachments** (e.g. the Receipt field on transactions) can't be uploaded through these tools. Say so and suggest the user attach the file in the app.
- **Don't fabricate.** If an account, category, payee, contact or company can't be found, say so. Never guess an ID.
- **Rate limits.** A 429 means slow down: wait a moment and retry once, then tell the user.

## Cross-domain recipes

- **"Log my meeting with Dana at Acme":** CRM: find the person (`find_many_people`), create a note (`create_one_note`), attach it via `note_targets`. If a follow-up is client-facing, create a CRM task with a `task_target`; if it's the user's own work, create a `cybernetics-data.tasks` row instead.
- **"Record what I paid the contractor":** `finance_Transactions` with Type Expense, resolve Account/Payee/Category (create the payee first if missing, after confirming). If the payee is a CRM company, mention that in `Notes`.
- **"Turn this decision into something I can find later":** create a `knowledges` entry under the right `knowledge_type`, and link `related_knowledge` to neighbouring entries.
- **"What's on my plate this week?":** `tasks` where progress is not finished/cancelled and `is_active` is true, sorted by priority; add CRM tasks only if the user says "including client follow-ups".

## Keeping this skill accurate

The IDs in `references/` were captured on 2026-09-19. Table and field IDs are stable unless the user restructures a table. On any "field not found" error, refresh with `get_table_schema` and use the new IDs for the rest of the session; mention to the user that the reference is stale so they can update it.
