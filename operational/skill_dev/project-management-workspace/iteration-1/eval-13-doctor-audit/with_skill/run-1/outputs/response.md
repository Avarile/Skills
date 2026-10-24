# Backlog and project audit (doctor, report-only), 2026-10-03

Based on: 1 goal, 3 projects, 115 task rows (all active). Nothing was changed.

## Decisions needed
1. **89 orphan tasks (no project).** 84 are `_Mock data._` backlog rows and 5 are old `finished_validating` leftovers from the dashboard build. Archive them (set `is_active` false), or keep? I need your yes and the count before touching them.
2. **k3s Migration has no lead.** Who should be `lead_by`? Its 11 tasks also have no assignee.
3. **Website Refresh Step 07 is overdue** (due 2026-10-01, in-progress since 09-27). Re-baseline the later due dates, or push to finish it? The mid-point check-point (Step 08) is due 10-08 and sits behind it.

## High
- Website Refresh is AMBER (SPI 0.86, 43% done, 1 overdue): high-impact risk "CMS API instability" has no mitigation.
- No Status Log entry since 2026-09-17 (16 days; the rule is 10).

## Medium
- 89 orphan active tasks (see above); fix is a bulk archive after your approval.
- k3s Migration (`preparing`): no `lead_by`, no Risk Register or Communication Plan in the charter, only the estimate and scope.
- Website Refresh is past `preparing` with empty `refer_knowledge` (no knowledge linked).
- 4 open Website tasks (Steps 09, 10, 13, 14) are unassigned.
- Inbox project is marked `in-progress` and holds one task, "Renew the domain name" (due 2026-10-08, unassigned). Inbox items older than 7 days: none yet.

## Low
- Website Steps 01-06 were all finished on the same day (2026-09-23) despite due dates 09-14 to 09-23. This looks like a bulk close, so I can't tell whether each has an evidence log line. I did not check the `## Log` text.
- 84 rows still carry the `_Mock data._` marker (same rows as the orphans).

## Checked and clean
No in-progress task without `started_at`; no finished task without `finished_at`; every project has a goal and tasks; all project tasks have a `Due:` line; no finished or cancelled project with open tasks; no gate problem.

## Proposed fixes (not applied)
1. Archive the 89 orphans (needs your confirm of the count).
2. Set a lead on k3s Migration.
3. Add a mitigation for the CMS API risk, and append a Status Log entry (I can draft it from `rollup.py`).
4. Assign owners for the unassigned tasks.
5. Link knowledge to Website Refresh.
