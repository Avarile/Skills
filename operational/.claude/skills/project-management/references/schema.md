# Schema reference (captured 2026-10-02, day planning and new fields 2026-11-03)

Base `bseJEuE54y5caWO0Xc8` ("data-centre"), space `spc1V7zXKTD999538hf`. IDs are stable unless the user restructures a table. On any "field not found" or option error: re-run `get_table_schema` for that table, continue with fresh IDs, and tell the user this file is stale.

## REST API (server-side filtering)

Base URL `https://cybernetics.avarile.com` (the `projects.avarile.com` address in `table_references` is stale). Token: env var `CYBERNETICS_DATA_API_TOKEN` (loaded from the repo `.env`; never print it). Endpoint `GET /api/table/<tableId>/record` with `fieldKeyType=id`, `take` (<=1000), `skip`, repeated `projection[]=<fieldId>`, JSON `filter` and `orderBy`. Use `scripts/query.py` (`SKILL.md` rule 2). Verified 2026-10-02: `is`, `isNot`, `isAnyOf`, `contains`, `isEmpty` (text, select, link, date), date `isBefore` with `{"mode":"exactDate","exactDate":"<ISO>","timeZone":"Australia/Melbourne"}`, `orderBy` desc. **Requests with the default `Python-urllib` user agent get HTTP 403; send a `User-Agent` header (curl works).** Reads: `scripts/query.py`. Writes: MCP for create and single update; `scripts/write.py` (bulk update, context append) and `scripts/views.py` (filtered views) for the rest. All write paths verified live 2026-10-02 (see below).

## Verified behaviours (2026-10-02 sandbox test; `[TEST]` rows, all deleted afterwards)

- **Invalid select option silently CLEARS the field.** MCP `update_record` with `finished-validating` on a task (hyphen = project spelling) returned success and set `progress` to empty. No error. Always take values from the enum lookup, and read back after every write. `write.py` validates against live field options and refuses.
- **Date and time fields** (`planned_start`, `actual_start`, `started_at`, `finished_at`): write a UTC timestamp, `2099-01-04T22:00:00.000Z` for 09:00 Melbourne. `teable.utc_iso` handles daylight saving; verified on January and July dates 2026-11-03.
- **Date filter on a timed value:** `is date:YYYY-MM-DD` matches by Melbourne day even when the stored time is not midnight (verified 2026-11-03 on a `daily_plans` row stored at 17:05 local).
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
| contacts | `tbl6730ZOe0zToNrcIr` | Assignees, leads and collaborators. `contact_type` `fldDFnZypupBS2dbhqG`: `self` is the user, `Agentic Mind` is an agent persona |
| knowledges | `tblVTWb1kxXSFPBq4Fq` | Inputs and lessons |
| knowledge_type | `tblWcq6Kof1AFHvbC5e` | Knowledge type tree |
| project_frameworks | `tbl6oTxXnstZGJNrHpm` | OKR / PDCA playbooks (read-only) |
| daily_plans | `tblwUxgw2YgU0Zm67e6` | One row per day |
| day_blocks | `tbl8nr9z2dZEJHcEiUn` | One row per planned slot |
| routines | `tblwb4WWe9Hw7r3BIzn` | Repeat rules, stamped into blocks when a day is planned |

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
| collaborator | `fldgB1KhSop61Qpyssn` | M:N -> contacts |
| agentic_generation | `fldxNdiG9qUupVLW0iF` | generated output, append with `write.py gen-append` |
| notes | `fld3QM0WdioiHSb7GVe` | the user's notes; do not write |
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
| collaborator | `fld8kFQbfW9VIv6V1AB` | M:N -> contacts |
| agentic_generation | `fldzaFydh9DtnOPvZA7` | generated output, append with `write.py gen-append`; entry header `### ◆ YYYY-MM-DD HH:MM UTC · <prompt>` |
| day_blocks | `fldJvbs2pOhdg5xcq4I` | reverse of `day_blocks.task`, read-only |
| notes | `fldfsST2ZFpRjmPeqmk` | the user's notes; do not write |
| is_active / deleted_at | `fldJMclfBagyBukSxoy` / `fldkdTbYu0f3LaYK7wl` | |
| id / created_at / updated_at | `fld2s647Pe9XgapERLS` / `fldYNEyagDaFRoxV8zF` / `fldVlGp4CjCeiNLC6cb` | read-only |

No due-date, estimate, phase, dependency or project priority field exists (Tier 1 proposals). Do not assume `Due:`, `Est:` or `Step NN` are present: none of the 8 in-flight tasks on 2026-11-03 has them.

## daily_plans

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldJ7lDiVIaMgpEJmDj` | a **date**. Write `YYYY-MM-DD`. A stored row can hold any time of day, so compare local dates |
| focus_goal | `fldSHFsOcQRq1YXGfqM` | link -> goals |
| focus | `fldWtTWlVudAAaQwhuy` | one line |
| status | `fld2abfT6ehoPtdWTa4` | `planned`, `running`, `reviewed` |
| capacity_minutes | `fldiby5lp2qT2IU3IVs` | |
| context | `fldXmne6mW8Xpkmq7EA` | markdown: `## Plan`, `## Deferred`, `## Meetings declined` |
| review | `fld1nag746vMJc3UvEE` | end-of-day text |
| notes | `fldeKU7bUxELTBcagmt` | the user's notes |
| day_blocks | `fldnz1MisFxXbFISvSf` | reverse of `belong_day`, read-only |
| is_active / deleted_at | `fldTAzKHlDaUvRsh53T` / `fldIr1WNg6g45K8UrUc` | |

## day_blocks

When priorities shift, mark a block `moved` with a reason and create a new one linked through `replaces`. Direct edits are only for unstarted blocks on future days (`day-planning.md#replan`).

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldtRZW60moxChIA1mb` | |
| belong_day | `fldKasFde0zQQLEb4qi` | link -> daily_plans |
| task | `fldOQcUAwEzRbhCy0vV` | link -> tasks, optional |
| kind | `fldK1gAFmolw5ZNHTWM` | select, default `deep-work` |
| status | `fldStji12ZpAomeQhPz` | select, default `planned` |
| source | `fldreE16ZFdJ1rcc1MV` | `plan`, `routine`, `adhoc` (adhoc has no planned_minutes) |
| routine | `fld15qEPrgEoKSqAJkQ` | link -> routines |
| replaces | `fldiuowC8CC70d5IRrN` | link -> day_blocks, one-way |
| order | `fldA9KGAERqhstiX1H1` | follows the timeline |
| planned_start / planned_minutes | `fld5BHdbS7RVL2qQILK` / `fldrGrVgBmWXDShODOt` | date with time |
| actual_start / actual_minutes | `fldnxj4thkYKgMyJvcK` / `fldf7pKThqQLnJ6G7uX` | |
| change_reason / notes | `flde9uVADhsWsQlJ7ey` / `fldV7saC9Pn6QXMn02A` | attendees: `With: <name>` in notes |
| is_active / deleted_at | `fldEjEBUiVdmbkjTiAK` / `fldRDTx4aBvdoVmajhH` | |

## routines

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldw3FxsebE1ztrGIgP` | |
| kind | `fldRJZXQYHKHM5Dp2Px` | same options as `day_blocks.kind`, default `meeting` |
| frequency | `fldFxLJaPuTXVx2pehW` | `daily`, `weekdays`, `weekly`, `monthly` |
| weekdays | `fldGZj2x13i1OSGULT2` | multi-select `Mon` ... `Sun`; required for `weekly` |
| month_day | `fld9zqW2uL3heMqnfFL` | -1 is the last day; required for `monthly` |
| start_time | `fldMDbrc8V3wBUZJm7L` | text `HH:MM`, Melbourne |
| planned_minutes | `fldGCx4sZKzr7pX1Rj2` | |
| valid_from / valid_until | `fldh4UPUsDzSORZRBaK` / `fldQltwtwKYFjTulBof` | inclusive |
| task | `fldr9Purk0NhK1qwciM` | link -> tasks, optional |
| day_blocks | `fldmLlkzmNitFOy3Vd7` | reverse of `day_blocks.routine`, read-only |
| notes | `fldiyNJpR9T5DdxqVZf` | optional `Output: <type>` line (`execution.md`) |
| is_active / deleted_at | `fldByDXoUfOy1H4Z6I0` / `fldb8BLr5z3Oa5z7get` | |

## knowledges / knowledge_type (for linking)

knowledges: title `fldROFj15OlD8COVxX0`, context `fld5tr2rH8oJXLrjUo9`, knowledge_type `fldAEK8ULw9urxE0qiF` (-> knowledge_type), knowledge_parent `fldzUUVy3q1vSWURhZD`, related_knowledge `fldz7U2RsCfm0j1RZOs` (M:N, one-way in practice: its reverse field is gone, so write both sides; `kb.py link --related` does).
knowledge_type: title `fldvL1LqKmEAfNKVBCO`, parent_type `fld924GlXY0tL5um2wk`, credentials `fld1s2dEom17aZIu4nx`. Full knowledge schema and verified behaviours: `knowledge-management/references/schema.md`.

## project_frameworks

title `fldi05ZCxsEFOEwJDlD`, context `fldtxhDAHpdRIwUZjjM`, type `fldX8DlWEqoxTAtFyxj` (`goal-management` = OKR, `project-management` = PDCA, `business-management`; no meeting framework row exists, so meeting rules live in `day-planning.md`). Read by title (`OKR`, `PDCA`) when depth is needed; do not paste whole playbooks into answers.

## Enum lookup (exact spelling)

| projects.progress | tasks.progress | tasks.priority |
|---|---|---|
| `backlog` | `backlog` | `urgent` |
| `preparing` | `in-progress` | `important` |
| `initiated` | `finished_reviewing` | `prioritise` |
| `in-progress` | `finished_validating` | `normal` |
| `finished-reviewing` | `onhold` | `can wait` |
| `finished-validating` | `cancelled` | |
| `finished-testing` | `closed` | |
| `finalized` | | |
| `onhold` | | |
| `cancelled` | | |

| day_blocks.kind / routines.kind | day_blocks.status | day_blocks.source | daily_plans.status | routines.frequency |
|---|---|---|---|---|
| `deep-work` | `planned` | `plan` | `planned` | `daily` |
| `review-agent-output` | `done` | `routine` | `running` | `weekdays` |
| `meeting` | `partial` | `adhoc` | `reviewed` | `weekly` |
| `admin` | `skipped` | | | `monthly` |
| `learning` | `moved` | | | |
| `personal`, `rest`, `prepare` | | | | |

Priority order: urgent > important > prioritise > normal > can wait. Tasks have no `finalized` or `finished_testing`. Task `closed` (added by the owner 2026-10-05) is the final done state, set when the user asks to close tasks or at project close; it counts as finished everywhere.

## Link write shapes

Reads return `{ "id": "recXXX", "title": "..." }`. Many-to-one write: `{ "id": "recXXX" }`. Many-to-many write: array of those. On the first link write of a session, `get_record` an existing linked record and mirror its shape; if rejected, fix and retry. Write only the write-side field (see tables above); reverse fields update themselves.

## Capability probe (Tier 0 vs Tier 1)

At the start of a session that will write, `get_table_schema` for `tasks` and `projects`. If a field named `due_date`, `phase`, `estimate_h`, `blocked_by` (tasks) or `start_date`, `due_date`, `priority` (projects) exists, use it and skip the text-line convention for that attribute. If a table `project_logs` exists, write logs there instead of `context` sections.

## Current state notes (2026-11-03)

goals 2, projects 8, tasks 93 (7 `backlog`, 1 `finished_reviewing`, the rest finished), daily_plans 1, day_blocks 6, routines 4. Auto-number `id` values have gaps because deleted rows leave them; count rows, never use `id` as a count. Grid views: `goals` `viwWavkgZpnTvthU8IG`, `projects` `viwwKKU4y3qtekoPPKx`, `tasks` `viw01WYSzvwCYdoEjqy`.
