# Agent protocol (Claude Code and other agents)

Goal: an agent doing real work leaves the database accurate without the user having to tell it to.

## Session protocol

1. **resume.** Run `python3 scripts/resume.py` (add `--json`); it does the matching below, prints the brief, and exits 0 (match), 3 (none) or 4 (ambiguous). Matching: match the working directory or repo name against the `Repo:` line in project `context`, else `search` projects by that name. One match -> load its Charter and my tasks. None or several -> ask once; do not guess. Output: project, RAG, progress, in-progress tasks, next 3 open tasks by priority then due, open blockers.
2. **claim.** Before starting a task: `in-progress`, `started_at` = today if empty, `## Log` line. Check for an unfinished earlier gate task; if present, stop and ask.
3. **work and log.** Append dated `## Log` lines with evidence (commit hash, PR, test output, link). Record a blocker as soon as it blocks.
4. **hand off.** At the end of the session set each touched task to its honest state and add a one-line summary. Never leave a claimed task `in-progress` without a log line that says where it stands.
5. **discoveries.** New work found along the way: create a task in the current project (allowed). Changing scope, priority order, due dates or acceptance criteria goes through `change` and needs the user's confirmation.

## Agent identity and assignment

An agent works as a contact (e.g. `Agentic Mind (Developer)`). Pass `--as "<contact>"` to `resume.py`, or set `PM_AGENT_CONTACT`; the brief then shows only tasks assigned to that contact plus a count of **unassigned tasks it could claim**. Without an identity the brief shows every open task.
- **Claim:** an agent may assign an *unassigned* task to itself when it starts it (`assign.py set --to "<me>" --ids <task> --yes`). It must not take a task held by someone else; ask the user (or the assignee) and use `--reassign` only after confirmation.
- **Hand-off:** to give work to another person or agent, `assign.py set --to <them> --ids ...`, add a `## Log` line saying why, and tell the user. Reassigning someone's tasks always needs confirmation.
- Never create or edit contacts without confirmation.

## Autonomy ceiling

| Action | Alone | Confirm with user |
|---|---|---|
| Read goals/projects/tasks/knowledge (not secrets) | yes | |
| Create or edit tasks in an existing project, append logs | yes | |
| Task -> `in-progress`, `finished_reviewing` | yes, with an evidence line | |
| Task -> `finished_validating` | only with objective evidence (tests pass, acceptance criterion met), stated explicitly | otherwise |
| Project status above `in-progress` | | always |
| Assign an unassigned task to itself, assign newly created tasks inside an existing project | yes | |
| Reassign tasks held by others, change `lead_by`, create or edit contacts | | always |
| Create goal or project, bulk create/update, re-parent, cancel, archive, schema or view changes | | always |
| `credentials`, `access_token`, `credential_*` knowledge | never | |

## Output style

Compact lines, IDs included, no narration. Finish with `changed: <n> task(s) ... | project <title> RAG <x>`. Surface anything the user must decide as one line starting `NEEDS DECISION:`.

## Optional automation (recipes only; nothing is installed unless the user asks)

**SessionStart hook** (project `.claude/settings.json`): injects the brief automatically when the working directory matches a project's `Repo:` line. It stays silent when there is no confident match or the match is ambiguous, never blocks (stdin read has a 1 s cap), and needs `CYBERNETICS_DATA_API_TOKEN` in the environment or a `.env` in the directory tree.
```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command",
  "command": "PM_AGENT_CONTACT=\"Agentic Mind (Developer)\" python3 /ABSOLUTE/PATH/TO/project-management/scripts/resume.py --hook"}]}]}}
```
Verify with: `echo '{"cwd":"<repo path>"}' | python3 scripts/resume.py --hook` (prints hook JSON on a match, nothing otherwise).

**Weekly review** via the `schedule` skill: a weekly routine whose prompt is "Run the project-management weekly review: `rollup.py portfolio`, a PDCA status report for every project not GREEN, and `doctor`; do not write anything, list decisions needed." Read-only by design; the user approves any follow-up writes.

**After a session**, the agent should have left every touched task with an honest state and a `## Log` line; `rollup.py project <id>` is a quick self-check (no stale `in-progress` tasks without a log entry).
