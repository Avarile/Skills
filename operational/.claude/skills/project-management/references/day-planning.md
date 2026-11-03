# Day planning: `plan-day`, `replan`, `review-day`, `routine`

Plans time on `daily_plans` (one row per date) and `day_blocks` (one row per slot), with `routines` as repeat rules. Everything numeric comes from `scripts/day.py`. Never work out routines, capacity, overlaps or ranking by hand.

Thresholds are constants at the top of `day.py`: buffer 20%, block cap 120 min, smallest block 30 min, alignment at 4 tasks or 360 min in one project with a 14-day lookback, at most 2 meeting suggestions per session, declined suggestions quiet for 7 days.

## plan-day

**One question per message, always with a recommendation, answerable in a word.** Never show the whole candidate list. Skip any step the user already answered. Hold decisions in the conversation; nothing is written until the final confirmation. If the user stops early, offer to save what was agreed.

1. **Load silently.** `day.py brief RANGE --json`. RANGE: `today`, `tomorrow`, `this-week`, `next-week`, `next-N-days`, a date, or `A..B`. Do not narrate the output.
2. **Close the last open day**, if `open_days` is not empty. Ask once per day: (a) go through it, (b) leave it unknown and carry open tasks forward, (c) skip. For (a) use the review-day steps. For (b) run `day.py review DATE --leave-unknown --yes`; never invent outcomes.
3. **Set the frame.** One question: state capacity and plannable minutes per date, and the flags. Ask for a focus only if it would change the ranking; pass `--focus-goal` and re-run `brief` if so. For a range, give the week as one line, not one question per day.
4. **New work.** "Anything not in the system that has to happen?" Capture each answer as a task (`workflows.md#capture`), then include it as a candidate.
5. **Walk the candidates, one at a time, in `brief` order.** Show the item, why it is here, proposed minutes and time or day, and remaining plannable minutes:
   `Item 2: <short title> (<why>). 90 min at 10:00? yes / change / skip / stop`
   - `auto` fills the rest in rank order and goes to step 6.
   - Stop asking when the plannable minutes run out, and say what was left out; those go in `deferred`.
   - Estimates marked `default` are guesses: if the task looks bigger or smaller, say so and propose a number.
   - Tasks assigned to agents are not candidates, because they do not use the user's focus time. An agent's finished work appears as a `review-agent-output` candidate. If a delegated task should start, mention it once and do not create a block for it.
6. **Meeting check.** `day.py meetings RANGE --json --tasks <chosen ids>`. One suggestion per message:
   `Meeting: <reason>. Book 30 min with <attendee> before this work, plus 15 min to prepare? yes / change / no`
   - **yes:** add a `meeting` block and a `prepare` block, as below. Sequence the affected tasks after it where possible.
   - **no:** record it under `declined_meetings` so it stays quiet for 7 days.
   - **A suggestion is a time block and nothing else.** Do not draft, send or offer to send a meeting request. This skill tracks work; the user handles the invitation.
7. **Preview and write.** Write the plan to a JSON file and run `day.py apply --input FILE`. Show the timeline and every flag. On one confirmation, run it again with `--yes` and read the result back. On `REFUSED`, resolve one error at a time with the user. `--allow-over` only when the user chose to go over capacity.

### apply input
```json
{"days": [{"date": "2026-11-04", "capacity": 600, "focus": "Ship the planner", "focus_goal": "rec...",
  "context": "Why this plan, in one or two lines", "deferred": ["Video scripts: no room this week"],
  "declined_meetings": [{"project": "rec...", "signal": "alignment", "reason": "already spoke"}],
  "blocks": [
    {"title": "Align on requirements", "task": "rec...", "kind": "meeting", "minutes": 30, "start": "10:00", "key": "m1", "notes": "With: Aaron Sansoni"},
    {"title": "Prepare alignment", "task": "rec...", "kind": "prepare", "minutes": 15, "before": "m1"},
    {"task": "rec...", "minutes": 90, "after": "m1"}]}]}
```
`start` is optional. `title` defaults to the shortened task title and `kind` to `deep-work`. The script stamps routines, places blocks, splits long deep work, sets `order`, reuses an existing day and refuses overlaps, past dates, reviewed days and misspelt kinds. Re-running after a failure is safe: routines are not stamped twice and the day is not duplicated.

### Ranking
Carry-overs and work in progress, then reviews waiting, then due in range, then the rest. Inside a tier: priority, due date, focus goal, projects that are not green, oldest. Left out, with counts in `skipped`: on hold, delegated to an agent, held by someone else, behind an open gate or dependency, already planned, under a paused project.

### Capacity
`free` is the smaller of the open time in the working window and `capacity` minus what is already committed. `plannable` is `free` minus the buffer. Today counts only the time left, from the Melbourne clock. The window runs from the earliest start to the latest end of the weekday routines; set `window` to override it. Going past `plannable` is a flag; going past `free` is refused until the user chooses what to drop.

### Routines
Every routine that falls on a planned date is stamped once, as a copy. Editing a routine changes only days not yet planned. `month_day` -1 is the last day of the month. **A routine stays on its exact date, including a weekend, and is flagged in the preview. Never move it silently.** Overlapping routines are flagged too, for example Monthly and Weekly report when a month ends on a Friday. Routines already past today are still stamped and come up at review.

### Meeting signals
| Signal | Fires when | Attendee |
|---|---|---|
| `escalation` | project is RED, or a change over 5% impact was logged this week | lookup below |
| `signoff` | a planned `Gate:` task, or a `finished_reviewing` task held by someone else | lookup below |
| `dependency` | an open blocker owned by someone else, or a human collaborator on planned work | that person |
| `alignment` | 4+ implementation tasks or 360+ min in one project, no meeting in 14 days | lookup below |
| `unclear` | planned work has placeholder text, or is 120+ min with no `Acceptance:` | lookup below |

Lookup: Charter `Sponsor / sign-off`, then a lead who isn't the user, then human collaborators, then the user's +1, **Aaron Sansoni** (company owner; override with env `PM_PLUS_ONE`). Agent personas are never attendees. If the user says nobody is needed, offer a 30-min block alone to decide it. Attendees go in the block's `notes` as `With: <name>`. Link the block to the first affected task, so later planning can see the project had its meeting.

## replan
For a priority shift, once the plan exists:
- **Default:** `day.py replan BLOCK --reason "..." [--date D] [--start HH:MM] [--minutes N]`. The old block becomes `moved` with the reason, and a new one links to it through `replaces`. The shift is recorded, not overwritten.
- **Dropped:** `--drop --reason "..."` marks it `skipped`.
- **Direct edit, only if needed:** `--edit` changes a block in place. It is refused unless the block is unstarted and on a future day. Use it for reworking a future plan where a moved row would only be noise, and say that the change was made in place.

## review-day
1. `day.py review DATE` shows blocks, totals, carry-over candidates, and blocks whose task has since finished (`likely done`).
2. Offer the shortcut first: "All as planned?" If yes: `--all-as-planned`.
3. Otherwise one block at a time, only those with no outcome: done, partial or skipped, plus minutes. Pre-fill `likely done`. Put them in a JSON file and pass `--outcomes FILE` (`[{"block": "rec...", "status": "partial", "minutes": 40, "reason": "..."}]`).
4. Ask for one line on how the day went. Pass it as `--text`.
5. Run with `--yes`. Plan status becomes `reviewed`. Name the carry-overs; `plan-day` picks them up automatically.

Actual minutes are the user's word. Never fill them from agent runtime. Day totals exclude `moved` and inactive blocks, so a move never counts twice; `adhoc` blocks count towards actuals only.

## routine
`day.py routine list`, `add --name --freq --start --minutes [--kind --weekdays Mon,Fri --month-day -1 --valid-from --valid-until --task --notes]`, `set REC ...`, `pause REC`, `resume REC`. Dry-run unless `--yes`; confirm with the user first. A line `Output: <type>` in a routine's `notes` overrides the output `do` chooses for it (`execution.md`).
