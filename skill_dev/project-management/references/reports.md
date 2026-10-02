# Health model and report formats

All numbers are computed from rows read in the same run, so agent and human see identical figures. State how many rows each figure used. Exclude `is_active` = false.

## Thresholds (edit here)

| Name | Value |
|---|---|
| Stale project | `updated_at` older than 14 days while `in-progress` |
| Status gap | no Status Log entry for more than 10 days (amber) |
| Gate overdue (red) | gate or critical task overdue by more than 3 days |
| Overdue ratio red | more than 25% of open tasks overdue |
| On-hold red | `onhold` longer than 14 days |
| SPI amber / red | below 0.85 / below 0.70 |
| Inbox age | Inbox tasks older than 7 days are flagged |
| Escalation | impact >5% needs written notice within 24 h |
| WIP limit | more than 3 in-progress tasks per person is flagged in `assign.py workload` (constant `WIP_LIMIT`) |

## Definitions

- **Open task:** `is_active` and progress not in `finished_reviewing`, `finished_validating`, `cancelled`.
- **Due:** the `Due:` line in task `context` (or the due-date field if the probe found one). No due date -> counted as "undated", reported, not overdue.
- **Overdue:** open and Due < today.
- **Completion:** finished / (total - cancelled), where finished = `finished_reviewing` or `finished_validating`.
- **SPI:** tasks finished / tasks with Due <= today, optionally weighted by `Est:`.
- **Project RAG:** Red if a gate/critical task is >3 days overdue, or overdue ratio >25%, or `onhold` >14 days, or the goal deadline has passed with the project unfinished. Amber if any task is overdue, SPI < 0.85, an open high-impact risk has no mitigation, or status gap >10 days. Otherwise Green. Say which rule fired.
- **Goal:** average KR score, runway = days to `deadline`, projects by RAG.

## Formats

**Assignees:** `rollup.py` adds `Lead: <name> · Open by assignee: A n, B n, unassigned n` to a project status; `assign.py workload` gives the per-person table (open, in progress, overdue, due in 7 days, urgent+important, on hold) and flags.

**Task list (plate)** sections in order: Overdue, Due in 7 days, In progress, Blocked/onhold, Unassigned, Undated. Each row: priority, title, project, due, assignee. Sorted urgent -> can wait, then due.

**Status (project)**
```
<title> · <progress> · RAG <emoji> (<rule fired>)
Tasks n: backlog a / in-progress b / reviewing c / validated d / onhold e / cancelled f
Completion 40% · SPI 0.9 · Overdue 2 · Undated 1
Next gate: <task> due <date> · Open risks: n (h high) · Last status: <date>
Decisions needed: ...
```

**Weekly report (PDCA format):** Overall status (RAG + one sentence), Accomplished this week (3-5), Planned next week (3-5 with owners), Risks and issues, Decisions needed, Metrics (completion, SPI, overdue, blockers). Offer to append it to `## Status Log`.

**Agent mode:** same content as compact lines with IDs, no prose. **Human mode:** open with Decisions needed, then the block above.
