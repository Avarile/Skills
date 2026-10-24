**Decisions needed**
- I have not assigned anything yet. My preview step (the read-only dry-run of `assign.py set`) was blocked by the permission classifier, so I don't have the task count or know whether any CHECK/ACT task already belongs to someone else.
- Please allow the dry-run, or tell me to go ahead using MCP reads instead. I'd then show you: how many CHECK and ACT tasks the k3s project has, which ones change, which are already Anastasia's, and which are held by someone else (those are skipped unless you confirm a reassign).
- I also haven't confirmed that "Anastasia" resolves to exactly one contact, or that "k3s" matches exactly one active project. If either is ambiguous I'll list the candidates and ask.

**What I will do after your confirmation**
1. Dry-run: `assign.py set --to Anastasia --project k3s --phase CHECK,ACT`. I'll add `--unassigned-only` if you don't want to take over anyone else's tasks.
2. Report the counts and wait for your OK, since this is a bulk update.
3. Apply it with `--yes`, then read the result back and show the changed rows.

Nothing has been written.
