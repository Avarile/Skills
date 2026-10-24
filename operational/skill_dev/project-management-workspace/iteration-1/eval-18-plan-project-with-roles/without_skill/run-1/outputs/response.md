I've drafted the Brand Refresh plan from your database but haven't written anything. I need a few answers from you first.

**How roles map in your data**
- Lead: `projects.lead_by` links to a contact. You are the contact "Avarile" (type self).
- Designer: `tasks.assigned_to` links to the contact "Agentic Mind (Designer)" (profession designer).
- Review: there is no reviewer field. Review is a step you own: the task is assigned to Avarile and moves to `finished_reviewing`. Sign-off is also recorded in the project Charter.
- Deadline: projects have no date field and tasks have only started_at/finished_at. Your existing projects keep deadlines in the Charter text and as "Due: YYYY-MM-DD" in each task's context, so I'd follow that.

**Proposed project: "Brand Refresh"**
- Progress is `preparing`. Lead is Avarile. Goal link is open (see questions).
- Charter: sign-off by Avarile, deadline 2026-11-20, fixed constraint time.
- Estimate is a range with a declared buffer. The window is 48 days (3 Oct to 20 Nov). I'd target design complete by 13 Nov, which leaves about 1 week (~15%) as a declared buffer.
- Risks: late feedback or review slots (owner Avarile) and scope creep into website or collateral.

**Draft tasks (Step NN [PHASE] titles, matching your existing projects)**

| # | Task | Assigned to | Due |
|---|---|---|---|
| 01 | [PLAN] Scope, out-of-scope, acceptance criteria | Avarile | 7 Oct |
| 02 | [PLAN] Estimate range, top 3 risks | Avarile | 9 Oct |
| 03 | [DO] Audit current brand and inputs | Designer | 16 Oct |
| 04 | [DO] Concepts and moodboards | Designer | 23 Oct |
| 05 | [CHECK] Review concepts, choose direction | Avarile | 27 Oct |
| 06 | [DO] Develop identity (logo, colour, type) | Designer | 6 Nov |
| 07 | [CHECK] Mid-point review of identity | Avarile | 9 Nov |
| 08 | [DO] Brand guidelines and asset pack | Designer | 13 Nov |
| 09 | [CHECK] Final review and sign-off | Avarile | 17 Nov (buffer to 20 Nov) |
| 10 | [CHECK] Retrospective | Avarile | 20 Nov |
| 11 | [ACT] Lessons learned into knowledge base | Avarile | 20 Nov |

All tasks start as `backlog`; priority is normal, or prioritise for the PLAN steps.

**Questions before I create anything**
1. Do you confirm these writes: one project, 11 tasks, and the links to you and the designer persona?
2. Should it link to the goal "Become the most reliable agent platform" (its KRs are success rate and latency, so brand doesn't obviously move them)? Or leave the goal empty?
3. Is time the fixed constraint, and what is in scope (logo only, or also website and collateral)?
4. Are the dates and 15% buffer OK? Do you want the designer to have any steps beyond those above?
5. Is the designer the "Agentic Mind (Designer)" contact? That is the only designer I found.
