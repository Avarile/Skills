**Decision needed: confirm before I change anything (bulk update, 8 tasks).**

"Website Refresh" (in-progress) has 14 tasks. Steps 01-06 are finished, so I'd leave them alone. The 8 open ones (Steps 07-14) each store their due date as a `Due:` line in `context`, because the tasks table has no due-date field. Shifting +5 days:

| Task | Status | Due now | New due |
|---|---|---|---|
| Step 07 [DO] Build first deliverable | in-progress | 2026-10-01 (overdue) | 2026-10-06 |
| Step 08 [DO] Mid-point check-point | backlog | 2026-10-08 | 2026-10-13 |
| Step 09 [DO] Build second deliverable | backlog | 2026-10-13 | 2026-10-18 |
| Step 10 [DO] Build third deliverable | backlog | 2026-10-19 | 2026-10-24 |
| Step 11 [CHECK] Verify figures and behaviour | backlog | 2026-10-26 | 2026-10-31 |
| Step 12 [CHECK] Retrospective | backlog | 2026-10-28 | 2026-11-02 |
| Step 13 [ACT] Write lessons learned | backlog | 2026-11-02 | 2026-11-07 |
| Step 14 [ACT] Adjust estimation notes | backlog | 2026-11-02 | 2026-11-07 |

Things to know:
- Step 07 was already overdue (due 1 Oct, today is 3 Oct). Moving it to 6 Oct is a rebaseline, not a new commitment. Say if you want it left as is.
- 5 days is calendar days. Step 09 lands on a Sunday (18 Oct) and Step 14's 7 Nov is a Saturday. Do you want working days instead?
- Only the `Due:` line changes. Status, started dates and the rest of each task stay as they are. I'd also add a dated `## Log` line to each task saying "Due +5d, client moved kickoff".
- Nothing has been written yet.

Reply "yes" (or tell me about the weekend or Step 07 questions) and I'll apply it, then read each task back to verify.
