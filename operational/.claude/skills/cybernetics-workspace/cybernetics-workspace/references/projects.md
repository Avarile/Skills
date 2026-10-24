# Projects, goals and tasks (cybernetics-data)

Base `bseJEuE54y5caWO0Xc8`. A three-level hierarchy: **goal -> project -> task**. People are attached through the `contacts` table.

## Contents
- Hierarchy and table IDs
- Status and priority values (they differ between projects and tasks!)
- Workflows
- Lifecycle conventions

## Hierarchy

```
goals (title, deadline)
  └── projects (progress, lead_by -> contacts)      via projects.belong_goals
        └── tasks (progress, priority, assigned_to -> contacts, started_at, finished_at)   via tasks.belong_project
```

Write the **child-side** link (`belong_goals`, `belong_project`); the parent's `projects` / `tasks` list fills itself.

## Table and field IDs

### `goals` - `tblbGSzWdR7KEtPVClg`
| Field | ID | Notes |
|---|---|---|
| title (primary) | `fld8ipvRLGq7YTgPQkI` | |
| context | `fldEoRNZHELqaaQbNTE` | Markdown: why it matters, definition of done |
| deadline | `fldlHvInBnEeptWDAvI` | date, no time |
| is_active | `fldRA4LarPTZ8fwagzt` | checkbox |
| deleted_at | `fldHyMiD5GAs8FI3ei8` | date |
| projects (reverse) | `fldKMG4vwodJPQRjw5y` | read-only, auto |

### `projects` - `tbliD8gcOTRk9RZ9SmR`
| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldiDksJhyT8mDAhCBP` | |
| context | `fldnzxFdoNG8bN1y4kC` | Markdown: scope, plan, links |
| progress | `fldYje9YsvEa6e7QotE` | single select, see below |
| belong_goals | `flduhpVlKOqQrmbIQv2` | link -> goals (write this side) |
| lead_by | `fldJKSNWzxTU1K5o83t` | link -> contacts |
| is_active | `fldF4pjQ5r6H0qSsbdy` | checkbox |
| deleted_at | `fldG6RCwocmogw71RqY` | date |
| tasks (reverse) | `fldmosZm5TTPkuyo5hr` | read-only, auto |

### `tasks` - `tblOMgDiajqa1moRRjE`
| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldGqUoXO7oyq6ufX2Y` | Start with a verb |
| context | `fldaOhjcXqdiF3IRVB1` | Markdown: details, acceptance criteria |
| progress | `fldG7fZN9XhOa0lMy33` | single select, default `backlog` |
| priority | `fldMTuydiWUFAgtqAPX` | single select, default `normal` |
| belong_project | `fld6X3nrMTQlYiV5XSa` | link -> projects (write this side) |
| assigned_to | `fld3ZGyfGzogzwHt5Md` | link -> contacts |
| started_at | `fldj3Xb1g9nUX4iFqE0` | date |
| finished_at | `fldn95wbkTqefn18WdO` | date |
| is_active | `fldJMclfBagyBukSxoy` | checkbox |
| deleted_at | `fldkdTbYu0f3LaYK7wl` | date |

### `contacts` - `tbl6730ZOe0zToNrcIr` (assignees / leads only)
Primary `title` `fldlcgf8tb0mWkzv3Rd`; also `email` `fldzbqogNQXHBtVmnEk`, `firstname` `fldJjAX79KRdKf58tbL`, `lastname` `flduzs6A7IbVnVAco9v`, `mobile` `fld7xdpslRgUB150twC`, links `contact_type`, `contact_profession`, `contact_company`. Look people up here only to assign/lead. For sales relationships use the CRM.

## Status and priority values

**These lists are different, and the spelling differs too (hyphen vs underscore).** Use the exact option name for the table you're writing to; new options can't be auto-created.

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

Note `tasks` uses `finished_reviewing` / `finished_validating` (underscores) while `projects` uses `finished-reviewing` / `finished-validating` (hyphens). Priority runs most to least pressing: urgent > important > prioritise > normal > can wait. Projects have no priority field.

"Done" for a task means `finished_validating` (fully verified) or `finished_reviewing` (delivered, awaiting check); tell the user which you set if they just said "done". Use the value they name if they name one.

## Workflows

**Capture a task** ("add a task to fix the invoice template, urgent, under the Website Refresh project")
1. Find the project: `query_records` on `projects` with `search`. Several matches -> ask. None -> offer to create it (and ask which goal, if any).
2. Create the task: `title`, `belong_project`, `priority` (default `normal` if unstated), `progress` (leave default `backlog`), `context` if there is detail. Resolve `assigned_to` from `contacts` if a person is named.
3. Echo back title, project, priority, assignee.

**Update status** ("started the invoice task" / "finished the migration")
- Set `progress`, and apply the lifecycle conventions below for the dates. Confirm what changed.

**Plan / review** ("what's on my plate?", "what's blocked?", "status of the website project")
- Tasks: page `tasks` with `projection` = title, progress, priority, belong_project, assigned_to, started_at, finished_at, is_active. Exclude `is_active` = false and, for "what's left", exclude finished_* and cancelled. Group by project, order by priority (urgent first). Highlight `onhold` separately as "blocked/paused".
- Project rollup: find the project, then its tasks (via the `tasks` reverse link or by scanning tasks with that `belong_project`); report counts by progress and what's overdue relative to the goal's `deadline`.
- Goals: list goals with `deadline`, and the projects beneath each, sorted by nearest deadline. Flag deadlines already passed with unfinished projects.

**Create a goal / project**
- Goal: `title`, `context`, `deadline`. Project: `title`, `context`, `belong_goals`, `lead_by`, `progress` (default to `backlog` unless the user says it's already underway).

**Move / re-parent**
- Change `belong_project` (task) or `belong_goals` (project). Moving many tasks at once is a bulk write: list them and confirm.

**Archive**
- `is_active` = false, `deleted_at` = today. Cancelled work stays visible via `progress` = `cancelled`; archive only when the user wants it out of the way.

## Lifecycle conventions (edit these to match your habits)

- Moving a task to `in-progress`: set `started_at` to today if it's empty.
- Moving a task to `finished_reviewing` or `finished_validating`: set `finished_at` to today if it's empty.
- Moving a task back out of a finished state: clear `finished_at` (tell the user).
- Don't overwrite existing `started_at`/`finished_at` values unless the user gives a date.
- Project `progress` isn't derived from its tasks automatically. Don't change a project's status because its tasks changed unless the user asks; you may suggest it ("all 6 tasks are finished - mark the project `finished-reviewing`?").
