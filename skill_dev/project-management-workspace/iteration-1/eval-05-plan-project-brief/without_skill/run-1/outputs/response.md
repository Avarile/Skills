# Expense-approval dashboard: 4-week plan (draft, nothing saved)

**Check first: your constraints conflict.** You said scope is fixed and 14 Nov is a hard deadline. A project can fix only one of scope, time and cost. Your PDCA playbook says to state which one is fixed. Today is 3 Oct, so 14 Nov is 6 weeks away. A 4-week build leaves about 2 weeks (~50%) of declared buffer. That is why both constraints can hold. If the 4 weeks slip, I need to know which one yields. I'd record it as **Fixed constraint: scope, with 14 Nov as a hard external date**, and protect the date with the 2-week buffer. Please confirm.

**Second check: KR1 link.** KR1 is "Agent task success rate" (89% now, target 94%, due 31 Dec). An expense-approval dashboard doesn't obviously move it. Please give me one sentence on the mechanism (for example, it surfaces failed agent approvals). Otherwise it should be logged as outside the OKR, not "Moves: KR1".

**Capacity risk.** You already lead Website Refresh (in progress, likely 42d, ~20% buffer) and k3s Migration (preparing, likely 42d). Both also move KR1. A third project in the same window is a risk for you personally, so I'd log it.

## Plan (PDCA, shape: build, lead/sponsor: you)
| When | Work |
|---|---|
| Week 1 (5-9 Oct) | PLAN: scope statement and out-of-scope list, acceptance criteria per deliverable, estimate range, top 3 risks. Audit data inputs (where expense and approval data lives). Design and layout. |
| Week 2 (12-16 Oct) | Build deliverable 1 (e.g. pending-approvals queue). Demo. |
| Week 3 (19-23 Oct) | Mid-point checkpoint. Build deliverable 2 (approve/reject flow, filters). |
| Week 4 (26-30 Oct) | Build deliverable 3 (summary metrics, roles). Verify against source data and acceptance criteria. |
| 2 Nov-14 Nov | Buffer (declared), sign-off, retrospective, lessons learned to the knowledge base, estimate-vs-actual notes. 14 Nov = hard date. |

Estimate range: I can't honestly give best/likely/worst without scope. I need the deliverables list. Placeholder: best 15d / likely 20d / worst 28d (4 weeks), buffer ~50% to the deadline. Replace once scope is known.

Top risks (draft): (1) scope not defined or growing while scope is "fixed", so changes go through a change request; (2) access to expense data and approval rules; (3) your capacity across three projects.

## What I need from you
1. Confirm the fixed constraint and KR1 mechanism above.
2. Deliverables, out-of-scope list and acceptance criteria.
3. Okay to save this to the database (see proposed writes in actions.md): one project plus ~12 task records, linked to the goal "Become the most reliable agent platform in our vertical", lead avarile@gmail.com, progress "preparing". I have not written anything.
