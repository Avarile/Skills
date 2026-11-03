ASSISTANT: I've taken "next week" as Monday 9 to Friday 13 November. There are no plans in those dates yet, and your routines only run on weekdays, so I've left the weekend of 14-15 November empty.

**What's fixed**
- Morning standup at 09:00 and end-of-day meeting at 17:30, every weekday.
- Weekly report on Friday 13 November at 16:00, 60 minutes.
- The monthly report isn't in this range. It's set to the last day of the month, which I read as Monday 30 November.

**What's open**
- **Data centre, waiting on you:** four tasks still need a browser run or visual pass. These are the day-mode cockpit (#605), the daily tracking schema (#602), the Data Graph (#609) and the Cyberpunk red theme (#603). Three of them are marked `finished_validating`, but their logs say the check hasn't happened.
- **Data centre, with the Developer agent:** the `@cybernetics/openapi` rebrand (#606), the agent-fields analysis (#610) and the Skill-running code review (#612). All three are still in backlog, and their target dates fall on or before 4 November.
- **Marketing:** the Knowledge for Fee launch (#613) and three videos (#614, #615, #616). None has an owner or a date, and all say "details to be completed by the owner".

Neither goal has a deadline, so nothing in the data decides how to split your time.

How do you want to split the week?
1. **Close out the data centre first, then start marketing (my recommendation).** Monday and Tuesday clear the browser checks and merge the two unpushed branches. Wednesday covers the agent analyses and the marketing brief. Thursday and Friday go to the first video. The review work is nearly finished, and it's holding up the rebrand.
2. **Data centre only.** Marketing waits another week.
3. **Marketing first.** The browser checks wait until later in the week.

USER (simulated): Option 1.

ASSISTANT: Here's the draft for 9-13 November. All times are Melbourne time, and nothing has been saved yet.

### Monday 9 Nov: close out day mode (300 min)
| Time | Block | Min | Task |
|---|---|---|---|
| 09:00 | Morning standup | 15 | routine |
| 09:15 | Browser run: day-mode cockpit and daily plan schema | 120 | #605, #602 |
| 11:30 | Close validated tasks and check the ones with no evidence | 30 | see below |
| 13:30 | Fix browser-run findings and merge `feat/cockpit-day-mode` | 90 | #605 |
| 16:00 | Email and admin | 30 | |
| 17:30 | End-of-day meeting | 15 | routine |

### Tuesday 10 Nov: close out the graph and theme (330 min)
| Time | Block | Min | Task |
|---|---|---|---|
| 09:00 | Morning standup | 15 | routine |
| 09:15 | Browser run: Data Graph scenes | 120 | #609 |
| 11:30 | Visual pass: Cyberpunk red theme | 45 | #603 |
| 13:30 | Fix findings, commit the theme, merge `feat/graph-scene` | 90 | #609 |
| 15:15 | Hand the openapi rebrand to the Developer agent | 15 | #606 |
| 16:00 | Email and admin | 30 | |
| 17:30 | End-of-day meeting | 15 | routine |

### Wednesday 11 Nov: agent decisions and the marketing brief (300 min)
| Time | Block | Min | Task |
|---|---|---|---|
| 09:00 | Morning standup | 15 | routine |
| 09:15 | Read the Skill-running review and decide the code-interpreter path | 60 | #612 |
| 10:30 | Read the agent-fields analysis and decide knowledge records or a new table | 60 | #610 |
| 13:30 | Write the Knowledge for Fee brief: audience, offer, format, price | 120 | #613 |
| 16:00 | Email and admin | 30 | |
| 17:30 | End-of-day meeting | 15 | routine |

### Thursday 12 Nov: first video and rebrand review (315 min)
| Time | Block | Min | Task |
|---|---|---|---|
| 09:00 | Morning standup | 15 | routine |
| 09:15 | Video "AI adoption, where almost everyone gets it wrong": outline and script draft | 120 | #616 |
| 11:30 | Fill in the details for the other two videos | 45 | #614, #615 |
| 13:30 | Review the openapi rebrand | 90 | #606 |
| 16:00 | Email and admin | 30 | |
| 17:30 | End-of-day meeting | 15 | routine |

### Friday 13 Nov: finish the script and report (330 min)
| Time | Block | Min | Task |
|---|---|---|---|
| 09:00 | Morning standup | 15 | routine |
| 09:15 | Video: finish the script and record a test take | 120 | #616 |
| 13:30 | Buffer for overruns from the week | 120 | |
| 16:00 | Weekly report | 60 | routine |
| 17:30 | End-of-day meeting | 15 | routine |

**Load:** 1,575 minutes (about 26 hours) against the 3,000 minutes you'd get at 600 a day, the capacity on your existing daily plans. That's about 52%, on purpose. Your only real day so far, 2 November, was planned at 315 minutes, and no actual times have been logged yet, so there's no evidence you can sustain more. No task has an estimate either, so the block lengths are my judgement.

**Choices to check**
- **Rebrand after the merges (#606):** I've held it until Tuesday afternoon because a repo-wide rename on top of two unpushed branches is likely to cause merge conflicts. This is based on the branch state logged on 2 November, so it's worth rechecking. Its dates on the task will be out of date, and I haven't changed them.
- **First video (#616):** I chose it because it argues one point, while the other two are full learning paths. That's my call and easy to swap.
- **Email and admin:** I copied this slot from your 2 November plan. It isn't a routine.

**What Monday's 11:30 sweep covers**
- **Ready to close:** #596, #597, #598 and #601. Their logs say they were validated on your word.
- **Not ready (#599):** its log waits on renaming two `contacts` fields. I checked the live schema today and they're still `projects (linked)` and `tasks (linked)`, not `collaborating_projects` and `collaborating_tasks`.
- **No evidence (#607 and #611):** both are marked `finished_validating`, but neither has a log or any recorded output. They need the output found, or reopening.

**What could change the plan**
- **#610 and #612 need to run this week.** Wednesday morning assumes the agent's output exists by then, and both are still in backlog. If they haven't run, those two slots become working through them with the agent.
- **I haven't seen your calendar.** I only used the database, and a search of your synced email for "next week" found nothing for these dates. Appointments or school runs would need to be moved around.
- **Two other things I'm leaving alone:** 2 November is still marked `running` with all six blocks at `planned`, and there are `[TEST]` plans on 5 and 19 November. Neither affects next week, but the `[TEST]` plan will show up this Thursday. I can clean these up separately if you want.

Saving this creates 5 daily plans and 30 blocks, 19 planned and 11 from routines. No existing tasks or plans change. Shall I save it as shown?

## Actions

### Run (all read-only)
- `Read` on `RUN_RULES.md`.
- `ToolSearch` to load `list_spaces`, `list_bases`, `list_tables`, `get_table_schema`, `query_records` and `get_record` from `mcp__cyb-data__`.
- `mcp__cyb-data__list_tables` on base `bseJEuE54y5caWO0Xc8`.
- `mcp__cyb-data__get_table_schema` on `tasks`, `daily_plans`, `day_blocks`, `routines`, `projects`, `goals`, `Emails · avarile@gmail.com` and `contacts`.
- `mcp__cyb-data__query_records` on:
  - `routines`, `daily_plans`, `day_blocks`, `goals` and `projects`
  - `tasks` three times: all 93 rows (the result overflowed to a file), then `skip` 80 and `skip` 74 for context and logs
  - the emails table with `search: "next week"`, `take: 10`, subject, sender, date and snippet only
- `mcp__cyb-data__get_record` on:
  - tasks `reck8rcOrEk9tY1HNiK`, `rec8De25IAGb7WFbTB8`, `recveBTIcW0HpQcGZzx`, `recFuV9dxDfqOEdZPir`, `recQKky88xi7fqxMTMb`, `reczYTjZyx7CA2ZSQKK`, `recdp55tcK2GDrfMgfX`, `recxFtZh95Hq6UjTktV`, `recFK9PXznbrvezz2Ua`, `recdBw9OTfNopwzVgKr`
  - projects `rechNbMPaXlSq47ZcVQ`, `recsKdvS9uwSDBXs5AQ`, `recjwiijjBO4wKg2XAl`
- `Bash`: local Python to parse the saved `tasks` result, a weekday check on the key dates, and `ls` on the outputs folder.
- `Write` on this file.

No database writes were made and nothing was sent to anyone.

### Writes on confirmation (not done)

**1. `mcp__cyb-data__create_records` on `daily_plans` (`tblwUxgw2YgU0Zm67e6`), 5 rows.** All have `status` = `planned` and `capacity_minutes` = 600. `title` is local midnight, stored in UTC as in the existing rows.

| title (local) | title (stored) | focus_goal | focus |
|---|---|---|---|
| 2026-11-09 | 2026-11-08T13:00:00.000Z | `recMNCthHjRTE2mxnqj` | Close out day mode: browser run, fixes, merge |
| 2026-11-10 | 2026-11-09T13:00:00.000Z | `recMNCthHjRTE2mxnqj` | Close out Data Graph and Cyberpunk red, merge, hand off rebrand |
| 2026-11-11 | 2026-11-10T13:00:00.000Z | `recMSfwALS4gN7m4DAR` | Decide from agent analyses, write Knowledge for Fee brief |
| 2026-11-12 | 2026-11-11T13:00:00.000Z | `recMSfwALS4gN7m4DAR` | First video draft, scope the other videos, review rebrand |
| 2026-11-13 | 2026-11-12T13:00:00.000Z | `recMSfwALS4gN7m4DAR` | Finish first video script, weekly report |

**2. `mcp__cyb-data__create_records` on `day_blocks` (`tbl8nr9z2dZEJHcEiUn`), 30 rows.** All have `status` = `planned`. `belong_day` is the new row for that date. `order` follows the listed sequence within each day. `planned_start` is in UTC (Melbourne is UTC+11).

Routine rows have `source` = `routine`. Morning standup links to `recOgx7PFjJd13Wg8cr`, End-of-day meeting to `recxGRNsT0gF6vxC4bl`, and Weekly report to `recaoN5s5JUyAyV79Rz`.

| Day | order | planned_start (UTC) | title | kind | min | source | task | notes |
|---|---|---|---|---|---|---|---|---|
| 09 | 1 | 2026-11-08T22:00Z | Morning standup | meeting | 15 | routine | | |
| 09 | 2 | 2026-11-08T22:15Z | Browser run: day-mode cockpit and daily plan schema | review-agent-output | 120 | plan | `rec125uFMUjo7eQDR9x` (#605) | Also covers #602 (`reck8rcOrEk9tY1HNiK`): day stage test checklist |
| 09 | 3 | 2026-11-09T00:30Z | Close validated tasks and check the ones with no evidence | admin | 30 | plan | | #596, #597, #598, #601 ready; #599 waiting on field rename; #607, #611 have no evidence |
| 09 | 4 | 2026-11-09T02:30Z | Fix browser-run findings and merge feat/cockpit-day-mode | deep-work | 90 | plan | `rec125uFMUjo7eQDR9x` (#605) | |
| 09 | 5 | 2026-11-09T05:00Z | Email and admin | admin | 30 | plan | | |
| 09 | 6 | 2026-11-09T06:30Z | End-of-day meeting | meeting | 15 | routine | | |
| 10 | 1 | 2026-11-09T22:00Z | Morning standup | meeting | 15 | routine | | |
| 10 | 2 | 2026-11-09T22:15Z | Browser run: Data Graph scenes | review-agent-output | 120 | plan | `recEe5qbfqbwf1YoOi3` (#609) | S7 browser run |
| 10 | 3 | 2026-11-10T00:30Z | Visual pass: Cyberpunk red theme | review-agent-output | 45 | plan | `reclf1YEfntyP5mxbwD` (#603) | Grid, forms, menus, dialogs, charts |
| 10 | 4 | 2026-11-10T02:30Z | Fix findings, commit the theme, merge feat/graph-scene | deep-work | 90 | plan | `recEe5qbfqbwf1YoOi3` (#609) | Also covers #603 commit |
| 10 | 5 | 2026-11-10T04:15Z | Hand the openapi rebrand to the Developer agent | admin | 15 | plan | `rec8De25IAGb7WFbTB8` (#606) | Only after both branches are merged |
| 10 | 6 | 2026-11-10T05:00Z | Email and admin | admin | 30 | plan | | |
| 10 | 7 | 2026-11-10T06:30Z | End-of-day meeting | meeting | 15 | routine | | |
| 11 | 1 | 2026-11-10T22:00Z | Morning standup | meeting | 15 | routine | | |
| 11 | 2 | 2026-11-10T22:15Z | Read the Skill-running review and decide the code-interpreter path | review-agent-output | 60 | plan | `recFuV9dxDfqOEdZPir` (#612) | |
| 11 | 3 | 2026-11-10T23:30Z | Read the agent-fields analysis and decide knowledge records or a new table | review-agent-output | 60 | plan | `recveBTIcW0HpQcGZzx` (#610) | |
| 11 | 4 | 2026-11-11T02:30Z | Write the Knowledge for Fee brief | deep-work | 120 | plan | `recQKky88xi7fqxMTMb` (#613) | Audience, offer, format, price |
| 11 | 5 | 2026-11-11T05:00Z | Email and admin | admin | 30 | plan | | |
| 11 | 6 | 2026-11-11T06:30Z | End-of-day meeting | meeting | 15 | routine | | |
| 12 | 1 | 2026-11-11T22:00Z | Morning standup | meeting | 15 | routine | | |
| 12 | 2 | 2026-11-11T22:15Z | Video "AI adoption": outline and script draft | deep-work | 120 | plan | `recxFtZh95Hq6UjTktV` (#616) | |
| 12 | 3 | 2026-11-12T00:30Z | Fill in the details for the other two videos | prepare | 45 | plan | | #614 (`reczYTjZyx7CA2ZSQKK`), #615 (`recdp55tcK2GDrfMgfX`) |
| 12 | 4 | 2026-11-12T02:30Z | Review the openapi rebrand | review-agent-output | 90 | plan | `rec8De25IAGb7WFbTB8` (#606) | |
| 12 | 5 | 2026-11-12T05:00Z | Email and admin | admin | 30 | plan | | |
| 12 | 6 | 2026-11-12T06:30Z | End-of-day meeting | meeting | 15 | routine | | |
| 13 | 1 | 2026-11-12T22:00Z | Morning standup | meeting | 15 | routine | | |
| 13 | 2 | 2026-11-12T22:15Z | Video "AI adoption": finish the script and record a test take | deep-work | 120 | plan | `recxFtZh95Hq6UjTktV` (#616) | |
| 13 | 3 | 2026-11-13T02:30Z | Buffer for overruns from the week | deep-work | 120 | plan | | No buffer kind exists, so this uses deep-work |
| 13 | 4 | 2026-11-13T05:00Z | Weekly report | admin | 60 | routine | | |
| 13 | 5 | 2026-11-13T06:30Z | End-of-day meeting | meeting | 15 | routine | | |

No other writes would be made. Task statuses and dates stay as they are, and the 2 November plan and `[TEST]` rows are not touched.
