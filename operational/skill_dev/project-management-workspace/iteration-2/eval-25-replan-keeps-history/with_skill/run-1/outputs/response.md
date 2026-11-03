ASSISTANT: **Decision needed:** OK to move this block to Friday at 09:15?

| | Block | When | Length |
|---|---|---|---|
| From | [TEST] Design work (deep work) | Thu 5 Nov, 13:30 to 15:30 | 120 min |
| To | [TEST] Design work (deep work) | Fri 6 Nov, 09:15 to 11:15 | 120 min |

- **Why 09:15:** your morning standup runs 09:00 to 09:15 on Fridays, and the morning is otherwise empty. Say if you'd prefer another time.
- **History is kept:** the Thursday block stays on record as `moved`, with the reason "Something urgent came up". The Friday block links back to it, and the move doesn't count twice in Thursday's totals.
- **Friday isn't planned yet:** this creates the day with only this block on it. Standup, Weekly report (16:00) and the end-of-day meeting (17:30) get added when you plan Friday, and none of them clash.
- **Thursday:** 13:30 to 15:30 opens up, and this was the only block on the plan that day.

The title starts with `[TEST]` and no task is linked to it, so check this is the block you meant.

Nothing has been changed yet. Shall I make the move?

## Actions

Commands and tool calls run (all read-only; nothing was written):

```
cd .claude/skills/project-management/scripts
python3 day.py --help
python3 day.py review 2026-11-05 --json        # found the 13:30 block, rec4KNQZad9N3KNL4h7
python3 day.py review 2026-11-06 --json        # "no plan on 2026-11-06"
python3 day.py brief 2026-11-05..2026-11-06 --json   # routines and free time on both days
python3 -c 'T.get_record(T.BLOCKS, "rec4KNQZad9N3KNL4h7")'   # full block record: no task, no notes
python3 day.py replan rec4KNQZad9N3KNL4h7 --reason "Something urgent came up on Thursday" --date 2026-11-06 --start 09:15   # dry run, first wording
python3 day.py replan rec4KNQZad9N3KNL4h7 --reason "Something urgent came up" --date 2026-11-06 --start 09:15   # dry run, final wording
```

Dry-run output for the final wording:

```
 - block [TEST] Design work: moved (Something urgent came up)
 - new block on 2026-11-06 09:15, 120 min, replaces it
DRY RUN: nothing written. Re-run with --yes to apply.
```

Writes on confirmation, through one command:

```
python3 day.py replan rec4KNQZad9N3KNL4h7 --reason "Something urgent came up" --date 2026-11-06 --start 09:15 --yes
```

1. **Create a `daily_plans` row:** date `2026-11-06`, status `planned`, because no plan exists for that date.
2. **Update `day_blocks` rec4KNQZad9N3KNL4h7:** status `moved`, reason `Something urgent came up`. It stays on the 2026-11-05 plan (recnImQRgBkIs7CmBU0).
3. **Create a `day_blocks` row:**
   - title `[TEST] Design work`
   - day: the new 2026-11-06 plan
   - kind `deep-work`, status `planned`, source `plan`
   - start 2026-11-06 09:15 Melbourne (`2026-11-05T22:15:00.000Z`), minutes 120
   - replaces rec4KNQZad9N3KNL4h7
4. **Read back:** the script confirms the moved status and the `replaces` link.

No routines are stamped by this command, and no task is touched, because the block has no linked task.
