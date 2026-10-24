**Decision needed:** your Finance Management Skill project already has a review task. Do you want me to move it to tomorrow, or add a separate one?

**What I found** (read only, nothing written yet)
- Project: **Finance Management Skill** (`recjVfyrbspJxTjpfMl`). Status `initiated`, lead Avarile, 15 tasks. Out of your 4 projects it's the only one about the finance skill.
- Tasks 01 to 11 are `finished_validating`. Step 12 (unit tests, acceptance test and behavioural evals) is `in-progress`; only the with/without-skill behavioural evals are left.
- **Step 13 [CHECK] Review real use and install the skill** (`reczoBdgxPsldDP1ces`) is the review task:
  - Status `backlog`, priority `important`, assigned to Avarile, `Due: 2026-10-09`.
  - Acceptance: you try 3+ real questions (cost windows, categorised search, subscriptions), the skill is synced to `.claude/skills/finance-management`, and settings.json allows `fin.py` reads but asks before `--yes`.
- Searching all task titles for "review" found no other finance review task.

**Option A (recommended): move Step 13 to tomorrow.** This avoids two review tasks for the same thing.
- On `reczoBdgxPsldDP1ces`, change context line 1 from `Due: 2026-10-09` to `Due: 2026-10-06`. Nothing else changes. Then read it back to check.
- Steps 14 and 15 are still due 2026-10-09, so the order still works.
- Step 12's behavioural evals aren't finished yet. You can still review tomorrow, but it will happen before the eval benchmark is in.

**Option B: add a new task, as you asked**
| Field | Value |
|---|---|
| title | `Review the finance management skill` |
| belong_project | Finance Management Skill (`recjVfyrbspJxTjpfMl`) |
| progress | `backlog` (default) |
| priority | `normal` (default) |
| assigned_to | Avarile (`recXUMD8VNfNmKQLs7h`) |
| context | `Due: 2026-10-06` then an empty `## Log` |

I used a plain title for B because the step numbers 01 to 15 are taken and "Step 13" would duplicate the existing one. If you choose B, I'd suggest marking Step 13 as covered by the new task, or cancelling it, so the review isn't counted twice.

Tomorrow = Tuesday 2026-10-06 (Melbourne).

Should I move Step 13's due date to 2026-10-06 (A), or create the new task "Review the finance management skill" due 2026-10-06 (B)?
