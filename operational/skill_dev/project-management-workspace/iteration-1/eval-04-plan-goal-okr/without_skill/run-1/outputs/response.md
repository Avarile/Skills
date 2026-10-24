Here is a draft OKR for the support bot. Nothing has been written to your database yet.

**What I found:** your `goals` table holds one goal, "Become the most reliable agent platform in our vertical". It has a Key Results table in its `context` (KR1 task success 87% to 94%, KR2 p95 latency) and a 2026-12-31 deadline. Nothing there or in `projects` covers the support bot, so this would be a new goal. I have no baseline data for ticket volume or resolution rate, so the numbers below are placeholders for you to confirm.

**Quarter:** today is 2026-10-03, so "next quarter" is Q1 2027 (Jan to Mar, deadline 2027-03-31). Tell me if you meant the current Q4 instead.

**Objective:** Make the support bot the first line of support, so most tickets never need a human.

| KR | Metric | Baseline | Target | Date |
|---|---|---|---|---|
| KR1 | Share of tickets fully resolved by the bot with no human touch | TBD (measure now) | 60% | 2027-03-31 |
| KR2 | Customer satisfaction on bot-resolved tickets (CSAT) | TBD | >= 4.3/5, no worse than human-resolved | 2027-03-31 |
| KR3 | Wrong or harmful bot answers (audited sample) | TBD | < 2% | 2027-03-31 |

"Most" is read as more than 50%, with 60% as a stretch. KR2 and KR3 stop the bot from hitting KR1 by deflecting customers or answering badly. Initiatives such as a knowledge-base gap review, a handoff flow and weekly transcript audits should be projects that move these KRs. They are not KRs themselves.

**Questions before I save it:**
1. Q1 2027 or Q4 2026?
2. What is today's baseline: tickets per week, and the share the bot already resolves?
3. Is 60% right, and how should "resolved without a human" be counted (no reopen within 7 days?).

**Proposed save, once you confirm:** one new `goals` record with title, context (Key Results table in the same format as your existing goal), deadline and is_active=true. I would then offer to create linked projects for the initiatives.
