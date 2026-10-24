# Backlog and projects audit (read-only, 2026-10-03)

I read goals (1), projects (3) and tasks (115). I changed nothing.

## Main problem: 89 of 115 tasks have no project
They are all in `backlog` except 5 that are `finished_validating`. They look like project plans whose parent projects were never created, or whose links were lost. The groups are:
- Backup plan, 6 steps.
- Finance dashboard, 14 steps.
- Patient booking / clinic project, 25 steps.
- Program charter, 18 steps.
- Cloud landing zone and security, 10 steps.
- Migration "tier-1", 11 steps.
- 5 finished "Next.js app" tasks (scaffold, dashboard UI, verify build, sync, deliver).

None of these tasks roll up to a project or a goal, so they won't show in any project view.

## Projects (3)
- **Website Refresh** is `in-progress` and linked to the goal. 13 of its 14 tasks are done (`finished_validating`) and the last one (Step 07, build first deliverable) is in progress. Steps 08 to 14 are still `backlog`.
  - Step 07 started 2026-09-27 and is still open, so it is about 6 days old.
  - The project's `progress` is only "in-progress", so it is not out of step with its tasks.
- **k3s Migration** is `preparing` with 11 tasks, all in backlog. That is consistent.
- **Inbox** is a catch-all marked `in-progress`. It has one task, "Renew the domain name" (priority `important`, no due date, no assignee), and no goal. Note that tasks have no deadline field, so an important renewal can't be tracked by date.

## Goal
There is one goal, "Become the most reliable agent platform in our vertical" (deadline 2026-12-30). Both real projects point to it.
- The 89 orphan tasks and the Inbox have no link to it.
- The k3s project and the 11-step Migration tasks above look like they might be duplicates. Please confirm which is which.

## Smaller issues
- Only 12 of 115 tasks have an assignee.
- 84 backlog tasks were all created on 2026-09-19, and none has a start date. They are not stale in an obvious way, but none has been touched since creation.
- Priority is heavily weighted. 36 tasks are `important` and 17 are `prioritise`, against 57 `normal`, so priority isn't discriminating much.
- Checks that found nothing wrong:
  - no soft-deleted or inactive records;
  - no done task without a finish date;
  - no open task with a finish date;
  - no finish date earlier than its start.

## Proposed next step (needs your OK)
Decide, for each of the orphan groups above, whether to create a project and link the tasks, or archive them. I haven't written anything. See the proposed writes in actions.md.
