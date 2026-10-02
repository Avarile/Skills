**Decisions needed**
1. Start date. Today is Sat 3 Oct and 14 Nov is also a Saturday, so the last working day is Fri 13 Nov. I planned 4 weeks as Mon 19 Oct to Fri 13 Nov. Starting Mon 5 Oct would give about 6 weeks, which is far safer for a fixed-scope, hard-deadline job. Which do you want?
2. Sponsor (who signs off the charter and the final acceptance), and the repo/workspace path (so an agent can find the project later). Neither is in the database.
3. Approve the preview below. I have not created anything.

**Where it fits**
- Goal: "Become the most reliable agent platform in our vertical". KR1 is Agent task success rate, baseline 87%, target 94%, now 89% (score 0.29, below the 0.4 mark). Owner Avarile, due 31 Dec.
- Heads-up: an expense-approval dashboard is an internal tool, and I can't see how it moves task success rate. The charter should state the mechanism and how we'd measure it. Otherwise it may be an initiative with no KR (orphan). Is KR1 definitely the right one?
- Existing projects: Website Refresh (in-progress), k3s Migration (preparing), Inbox. No duplicate of this one (3 projects read).

**Charter draft (project `preparing`, lead = you, Avarile)**
- Constraint: scope is fixed and the date is fixed, so the only flex is buffer (and extra help). Scope cuts are off the table by your rule, so a slip must be escalated, not absorbed.
- Estimate: best 16d / likely 20d / worst 28d; declared buffer 30% (new, uncertain work), so the span is 26 days and ends Fri 13 Nov. Worst case (28d) overruns by 2 days, which is the real risk to the deadline. These are my starting numbers; please correct them.
- Scope, out-of-scope and acceptance criteria: to be written in Steps 01 and 02 (the first two tasks). Nothing is invented here; I need your scope list.
- Top risks (each with a mitigation): (1) scope is fixed but unwritten, so freeze it in writing at the gate and route any change through the Change Log; (2) expense data or approval rules are not available or are messy, so audit the inputs in week 1 (Step 05); (3) the date is hard and the worst case overruns, so a mid-point check on 2 Nov, and escalate to the sponsor at the first >5% slip; (4) approver/stakeholder availability for UAT, so book review slots now.
- Comms: weekly status to the sponsor, a demo at each increment, a mid-point check on 2 Nov.

**Task skeleton (template `build`, 14 steps, lint OK)**
| Due | Step | Owner |
|---|---|---|
| 20 Oct | 01 PLAN scope + out-of-scope | Avarile |
| 20 Oct | 02 PLAN acceptance criteria | Avarile |
| 21 Oct | 03 PLAN estimate range + buffer | Avarile |
| 21 Oct | 04 PLAN top 3 risks (GATE, nothing is built before it) | Avarile |
| 23 Oct | 05 DO audit inputs and data | Agentic Mind (Developer) |
| 26 Oct | 06 DO design and layout | Agentic Mind (Developer) |
| 29 Oct | 07 DO first deliverable | Agentic Mind (Developer) |
| 2 Nov | 08 DO mid-point check | Agentic Mind (Developer) |
| 4 Nov | 09 DO second deliverable | Agentic Mind (Developer) |
| 9 Nov | 10 DO third deliverable | Agentic Mind (Developer) |
| 10 Nov | 11 CHECK verify against acceptance | Avarile |
| 12 Nov | 12 CHECK retrospective | Avarile |
| 13 Nov | 13 ACT lessons to knowledge | Avarile |
| 13 Nov | 14 ACT estimation notes | Avarile |

Caveats: the verify step lands only 3 days before the deadline and the dates are weekday-adjusted, so the buffer is already inside the span, not on top. The generic deliverable names (first/second/third) should be renamed to the real dashboard pieces once scope is written. The default split is you on PLAN/CHECK/ACT and the agent persona on DO; say if you'd rather do the build yourself.

Knowledge pre-flight: not run yet (I'd list up to 5 related entries by title for you to pick). Say go and I will.

**Next step on your yes:** create the project and its 14 tasks (counts confirmed back), then run the rollup (expect GREEN, no overdue). The project stays `preparing` until the gate task is finished.
