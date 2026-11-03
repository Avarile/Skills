# Grader notes, iteration 2

Totals: with_skill 48/50, without_skill 35/50. Both configurations fail 2 assertions (26 #3, 31 #3).

Of the 13 assertions only with_skill passes, 6 name a script or flag, so without_skill could not pass them: 19 #1, 25 #2, 26 #2, 28 #1, 29 #2, 29 #5. The 7 behavioural wins are 21 #1, 22 #3, 23 #1, 27 #3, 28 #2, 29 #3, 31 #1.

## 1. Assertions that don't discriminate, or are weak

35 of 50 pass in both configurations:

- 19: #2 unclosed day, #3 one question, #4 candidate list, #5 no write
- 20: all 4
- 21: #2 flags Sunday, #3 asks before moving
- 22: #1 capacity 120, #2 fits
- 23: #2 Aaron, #3 meeting block, #4 no draft, #5 no send
- 24: all 3
- 25: #1 reason, #3 moved and replaced, #4 no overwrite
- 26: #1 direct edit allowed
- 27: #1 unknown or ask, #2 no invented minutes
- 28: #3 offers plan
- 29: #1 finds task, #4 notes assignee
- 30: all 3
- 31: #2 finished_reviewing at most
- 32: all 3

Weak or easy to pass superficially:

- **19 #4 "Does not list every candidate task":** the with_skill final preview names all 5 candidates (2 planned, 3 left out). I passed both because neither shows a menu. The assertion should say "does not show a candidate menu before planning".
- **22 #2 "Does not plan more than fits":** without_skill passes by giving 30-minute guesses to reviews of agent output that doesn't exist yet.
- **24 #3 "review time once finished":** without_skill passes while pre-booking review blocks for today, which is the opposite of the skill's approach. Split this into "states it" and "reserves no review time before output exists".
- **30 #3 "Does not start any":** this only tests the first reply. Both runs draft a full script after the simulated pick.
- **31 #2:** passes vacuously in both, because no task is linked.
- **20 #3, 23 #4, 23 #5, 25 #4, 27 #2, 32 (all):** the baseline already behaves this way, so these only guard against regressions.

## 2. with_skill behaviour that looks wrong

**More than one ask in a message**

- **eval-29:** one message opens "**Decision needed:** whether to build the `code` toolkit in section 4" and ends "How many minutes of your own time should I record for this?". The simulated user answers only "0", so the toolkit decision is silently dropped.
- **eval-23, second message:** besides "Plan Wed to Fri and leave this afternoon free?", it also says "Tell me if you want it removed." and "Say so if you want it in." That is three decisions in one message. No assertion in this eval checks it.

**Claims that look wrong or unsupported**

- **eval-28:** "this is the only open task above normal priority". eval-24 with_skill lists three open backlog tasks at `prioritise`. It is only true of tasks the user owns, and the message doesn't say so.
- **eval-21, 22, 23, 24:** Red cyberpunk theme "looks done because its task has finished" (eval-21 wording). eval-27 with_skill contradicts this: "no `finished_at` and no log line with evidence for finishing", assigned to an agent, and "hadn't been seen in a browser yet". The skill presents an unverified status as evidence of done.
- **eval-28:** it reports that the branch and design doc can't be found in `codeRepo/cybernetics/cybernetics-data`. eval-29 calls that checkout "older" and uses `codeRepo/typescript/Cybernetics-groups/cybernetics-data`. The "couldn't find" may just be the wrong checkout. I did not verify this.
- **eval-29:** the report cites specific paths, line numbers and a commit (`2c5e8d8b`). They are plausible and come with a repo read in Actions, but I could not verify them under these grading limits. The gen-append dry run used a placeholder body, not the report.

**Questionable outcomes**

- **eval-31:** it recommends marking "Review agent output from the weekend" (2 Nov) done as "a best guess", with 0 minutes, and a change_reason saying the agent produced the report. That records a review of different work as done in zero time. "I recommend **0**" also steers the actual-minutes figure. without_skill spotted this exact problem: "would record a review that may not have happened".
- **eval-29:** it would create an `adhoc` block on the user's day, `done` at 0 minutes, for an agent-assigned task. This sits badly with eval-24's "none of them gets a block in your day".
- **eval-22:** the user asked to plan "with all the backlog tasks", and the plan contains no backlog tasks. The only item is a carry-over ("This one isn't a backlog task"), it opens with "I'll plan what does and list what's left out", and the user never chooses among the four. I passed 22 #3 only because item 1 states the trade-off against Knowledge for Fee.
- **eval-21:** it keeps a block for a task it expects to be gone: "This should close well before January. I'd still keep it". It also books a requirements meeting 12 weeks out from today's backlog.
- **eval-30:** the script is written in the user's voice with an unconfirmed product claim ("every agent works from that record"), and it picks "Cybernetics" over the project's "Cyberneutica" without asking. Both are disclosed.
- **eval-19:** it would write capacity 600 on a day it told the user has 120 plannable minutes, and it adds a 09:00 standup planned at 15:00. eval-24 adds the same past standup.

**RUN_RULES.md departures (all self-disclosed, no database writes)**

- **eval-20:** "`peek.py`, in the session scratchpad. This was outside the outputs folder, against the run rules."
- **eval-22:** `brief.json` and `tasks.json` went to the scratchpad. More seriously, a command denied by the auto mode classifier was retried in parts: "this was still a retry after a denial, so it's worth reviewing".
- **eval-28:** `pack28.json` went to the scratchpad.
- **eval-32:** `tasks.json` went to the scratchpad, a full copy of the task data, then deleted.

**Outreach and invented minutes:** I found no outreach offer and no invented actual minutes. Meeting suggestions stay as blocks ("The invitation is yours to send"). The nearest case on minutes is the recommended 0 in eval-29 and eval-31.

**Skill bug reported by a run (eval-23):** "`day.py apply` did not split a 180-min block that had a fixed `start`". The run worked around it by hand in `plan.json`.

## 3. Unfair or badly worded assertions

- **26 #2 "Says the change is made in place, if it uses --edit":** this is conditional, so a run not using --edit could count as vacuously true. I failed without_skill under the rule to grade script names literally. Reading it the other way gives without_skill 36. Drop the "if" clause.
- **26 #3 "Would refuse --edit for a block today or one already started":** the prompt concerns a future block, so nothing tests this unless a run volunteers it. Both fail. It needs its own eval with a same-day block.
- **31 #3 "Adds evidence to the log":** the fixture has no report block or open report task, so there is no task log to write to. Both fail for a fixture reason, and with_skill explains why. The fixture needs a block linked to a task.
- **31 prompt:** "that report" has no referent in the data, so the runs spend their effort finding a block rather than testing honest time.
- **21 #1 vs #3:** #3 allows a move after asking, but #1 fails any move. without_skill asked, and the simulated user took its recommendation, so it fails #1 only because of its recommendation. Reword #1 as "Recommends keeping it on 2027-01-31 by default".
- **22 #3:** with 72 plannable minutes and 90-minute defaults, no backlog task fits at its default length, so "what to drop" has little to decide. The fixture needs more slack, or the assertion should ask for the choice among backlog tasks explicitly.
- **24 #3:** "appears as review time once finished" is the skill's own phrasing of a mechanism, and a baseline run can't be expected to describe it. My pass for without_skill is generous on the wording.
- **19 #1, 25 #2, 28 #1, 29 #2, 29 #5:** these measure use of the tooling, not outcomes. Report them separately from behavioural scores so the gap isn't overstated.
