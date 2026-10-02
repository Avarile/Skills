# Schema reference (captured 2026-10-02)

Base `bseJEuE54y5caWO0Xc8` ("data-centre"), space `spc1V7zXKTD999538hf`. IDs are stable unless the user restructures a table. On any "field not found" or option error: re-run `get_table_schema` for that table, continue with fresh IDs, and tell the user this file is stale.

## REST API (server-side filtering)

Base URL `https://cybernetics.avarile.com` (the `projects.avarile.com` address in `table_references` is stale). Token: env var `CYBERNETICS_DATA_API_TOKEN` (loaded from the repo `.env`; never print it). Endpoint `GET /api/table/<tableId>/record` with `fieldKeyType=id`, `take` (<=1000), `skip`, repeated `projection[]=<fieldId>`, JSON `filter` and `orderBy`. Use `scripts/query.py` (`SKILL.md` rule 2). Verified 2026-10-02: `is`, `isNot`, `isAnyOf`, `contains`, `isEmpty` (text, select, link, date), date `isBefore` with `{"mode":"exactDate","exactDate":"<ISO>","timeZone":"Australia/Melbourne"}`, `orderBy` desc. **Requests with the default `Python-urllib` user agent get HTTP 403; send a `User-Agent` header (curl works).** Reads: `scripts/query.py`. Writes: MCP for create and single update; `scripts/write.py` (bulk update, context append) and `scripts/views.py` (filtered views) for the rest. All write paths verified live 2026-10-02 (see below).

## Verified behaviours (2026-10-02 sandbox test; `[TEST]` rows, all deleted afterwards)

- **Invalid select option silently CLEARS the field.** MCP `update_record` with `finished-validating` on a task (hyphen = project spelling) returned success and set `progress` to empty. No error. Always take values from the enum lookup, and read back after every write. `write.py` validates against live field options and refuses.
- **Dates:** write plain `YYYY-MM-DD`; it is stored as Australia/Melbourne midnight. Reads return UTC timestamps (`2026-12-31` reads back `2026-12-30T13:00:00.000Z`). Convert to Melbourne before comparing or displaying (`write.py` `local_date`).
- **Checkbox:** unchecked reads back as `null`, not `false`. "Inactive" means not `true`. Filter with `is true` / `is false`; `isEmpty` is invalid on checkboxes (HTTP 400).
- **`projects.lead_by` shows the contact's EMAIL as its link label** (its lookup field is `contacts.email`, unlike `tasks.assigned_to`, which shows the name). A contact without an email gives an empty label. Resolve names through the contact id (`teable.contact_name`), never from the link title.
- **Defaults apply on create:** task `progress` -> `backlog`, `priority` -> `normal`, `is_active` -> true.
- **Links:** many-to-one `{"id": "rec..."}` and many-to-many `[{"id": "rec..."}]` both work on create and update; reverse fields (`projects.tasks`, `goals.projects`) fill automatically. Link filters: `is <recId>`, `isAnyOf`, `isEmpty`, `hasAnyOf` (many-to-many).
- **Server-side filtering:** REST `filter`/`orderBy` work (`query.py`). A saved view's filter also works through MCP `query_records` with `viewId` (no token needed). `views.py create` stores filters; MCP `create_view` cannot.
- **Trace:** `refer_knowledge` reverse lookup is one filtered query per table (`hasAnyOf <knowledgeRecId>`), no full scan.
- **`context` append:** `write.py ctx-append` creates or extends a `## Section`, leaves other sections intact, keeps bullet lists contiguous, and aborts without writing if the field changed between its two reads.
- **Bulk update:** `write.py bulk-update` applied filtered and by-id updates with read-back verification. Deleting goes to the table trash (recoverable).

## Tables

| Table | ID | Role |
|---|---|---|
| goals | `tblbGSzWdR7KEtPVClg` | OKR Objective |
| projects | `tbliD8gcOTRk9RZ9SmR` | PDCA cycle / Initiative |
| tasks | `tblOMgDiajqa1moRRjE` | Step |
| contacts | `tbl6730ZOe0zToNrcIr` | Assignees and project leads only |
| knowledges | `tblVTWb1kxXSFPBq4Fq` | Inputs and lessons |
| knowledge_type | `tblWcq6Kof1AFHvbC5e` | Knowledge type tree |
| project_frameworks | `tbl6oTxXnstZGJNrHpm` | OKR / PDCA playbooks (read-only) |

System tables (`system_info`, `system_status`, `auditlog`, `table_references`, `template_table`) are read-only and out of scope. `table_references` is stale; do not trust its enum lists.

## goals

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fld8ipvRLGq7YTgPQkI` | Objective sentence |
| context | `fldEoRNZHELqaaQbNTE` | markdown: `## Key Results`, `## Check-ins` |
| deadline | `fldlHvInBnEeptWDAvI` | date, period end |
| projects | `fldKMG4vwodJPQRjw5y` | reverse of `projects.belong_goals`, read-only |
| refer_knowledge | `fldRMySX5jvdIUWIkGB` | M:N one-way -> knowledges |
| is_active / deleted_at | `fldRA4LarPTZ8fwagzt` / `fldHyMiD5GAs8FI3ei8` | soft delete |
| id (auto) / created_at / updated_at | `flduksVpaxButKuoBP5` / `fldF6ePvL85DjAaNBMX` / `fldWsQ0qTEw6e6WPv4V` | read-only |

## projects

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldiDksJhyT8mDAhCBP` | |
| context | `fldnzxFdoNG8bN1y4kC` | markdown: Charter and logs |
| progress | `fldYje9YsvEa6e7QotE` | select, 10 options below |
| belong_goals | `flduhpVlKOqQrmbIQv2` | link -> goals (write this side) |
| lead_by | `fldJKSNWzxTU1K5o83t` | link -> contacts |
| tasks | `fldmosZm5TTPkuyo5hr` | reverse of `tasks.belong_project`, read-only |
| refer_knowledge | `fldCw3cnpw8EWs09C1v` | M:N one-way -> knowledges |
| is_active / deleted_at | `fldF4pjQ5r6H0qSsbdy` / `fldG6RCwocmogw71RqY` | |
| id / created_at / updated_at | `fldsF1jpTNEc9ueidVf` / `fldRVnmWZ3Wb9ReEC9k` / `fldj85aGVZVUyo2xerD` | read-only |

## tasks

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldGqUoXO7oyq6ufX2Y` | `Step NN [PHASE] Verb object` |
| context | `fldaOhjcXqdiF3IRVB1` | markdown: `Due:` line, details, `## Log` |
| progress | `fldG7fZN9XhOa0lMy33` | select, default `backlog` |
| priority | `fldMTuydiWUFAgtqAPX` | select, default `normal` |
| belong_project | `fld6X3nrMTQlYiV5XSa` | link -> projects (write this side) |
| assigned_to | `fld3ZGyfGzogzwHt5Md` | link -> contacts |
| started_at / finished_at | `fldj3Xb1g9nUX4iFqE0` / `fldn95wbkTqefn18WdO` | date |
| refer_knowledge | `fldJzsKyzBaDFt7bHIu` | M:N one-way -> knowledges |
| is_active / deleted_at | `fldJMclfBagyBukSxoy` / `fldkdTbYu0f3LaYK7wl` | |
| id / created_at / updated_at | `fld2s647Pe9XgapERLS` / `fldYNEyagDaFRoxV8zF` / `fldVlGp4CjCeiNLC6cb` | read-only |

No due-date, estimate, phase, dependency or project priority field exists (Tier 1 proposals).

## knowledges / knowledge_type (for linking)

knowledges: title `fldROFj15OlD8COVxX0`, context `fld5tr2rH8oJXLrjUo9`, knowledge_type `fldAEK8ULw9urxE0qiF` (-> knowledge_type), knowledge_parent `fldzUUVy3q1vSWURhZD`, related_knowledge `fldz7U2RsCfm0j1RZOs` (M:N symmetric).
knowledge_type: title `fldvL1LqKmEAfNKVBCO`, parent_type `fld924GlXY0tL5um2wk`, **credentials `fld1s2dEom17aZIu4nx` (secret, never read)**.
Excluded from project lookups: types `credentials`, `credential_apikey`, `credential_login`, `credential_access_token`, `credential_sshkey`, and any `missav_*` / personal-media type.

## project_frameworks

title `fldi05ZCxsEFOEwJDlD`, context `fldtxhDAHpdRIwUZjjM`, type `fldX8DlWEqoxTAtFyxj` (`goal-management` = OKR, `project-management` = PDCA, `meeting-strategy`, `conversation-strategy`, `business-management`). Read by title (`OKR`, `PDCA`) when depth is needed; do not paste whole playbooks into answers.

## Enum lookup (exact spelling)

| projects.progress | tasks.progress | tasks.priority |
|---|---|---|
| `backlog` | `backlog` | `urgent` |
| `preparing` | `in-progress` | `important` |
| `initiated` | `finished_reviewing` | `prioritise` |
| `in-progress` | `finished_validating` | `normal` |
| `finished-reviewing` | `onhold` | `can wait` |
| `finished-validating` | `cancelled` | |
| `finished-testing` | | |
| `finalized` | | |
| `onhold` | | |
| `cancelled` | | |

Priority order: urgent > important > prioritise > normal > can wait. Tasks have no `finalized` or `finished_testing`.

## Link write shapes

Reads return `{ "id": "recXXX", "title": "..." }`. Many-to-one write: `{ "id": "recXXX" }`. Many-to-many write: array of those. On the first link write of a session, `get_record` an existing linked record and mirror its shape; if rejected, fix and retry. Write only the write-side field (see tables above); reverse fields update themselves.

## Capability probe (Tier 0 vs Tier 1)

At the start of a session that will write, `get_table_schema` for `tasks` and `projects`. If a field named `due_date`, `phase`, `estimate_h`, `blocked_by` (tasks) or `start_date`, `due_date`, `priority` (projects) exists, use it and skip the text-line convention for that attribute. If a table `project_logs` exists, write logs there instead of `context` sections.

## Current state notes (2026-10-02)

goals 0 rows, projects 0 rows, tasks 89 rows, none linked to a project: 84 `backlog` rows marked `_Mock data._` and 5 `finished_validating` leftovers from an earlier dashboard build ("Scaffold the Next.js app" ... "Package and deliver project to user"). Auto-number `id` reaches 171 because deleted rows leave gaps; count rows, never use `id` as a count. Only a "Grid view" exists per table: `goals` `viwWavkgZpnTvthU8IG`, `projects` `viwwKKU4y3qtekoPPKx`, `tasks` `viw01WYSzvwCYdoEjqy`.
