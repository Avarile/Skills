## Calls made
- `cat skill_dev/knowledge-management/SKILL.md` + `ls -R` -> read skill: archive needs user confirmation; write commands are dry-run unless --yes.
- `cat references/workflows.md` + grep schema.md -> archive workflow: trace before archiving, dry-run, then --yes after user OK; soft archive (is_active false + deleted_at).
- `python3 skill_dev/knowledge-management/scripts/kb.py find temp --all` -> 11 matches; exact title "temp" = recKeYy9bxAXG9F3h2K [TEMP - Records], 2026-09-22, 2.0k chars (also "K3S - Migration setup script - TEMP" recukPJGr1EjdCI21G1, not targeted).
- `python3 skill_dev/knowledge-management/scripts/kb.py get temp` -> resolved uniquely to recKeYy9bxAXG9F3h2K; body = draft Okta SSO / Meta business account message; no secrets.
- `python3 skill_dev/knowledge-management/scripts/kb.py find temp --all --titles --limit 30` -> confirmed only one entry titled exactly "temp".
- `python3 skill_dev/knowledge-management/scripts/kb.py trace recKeYy9bxAXG9F3h2K` -> referenced by 0 work records.
- `python3 skill_dev/knowledge-management/scripts/kb.py tree recKeYy9bxAXG9F3h2K` -> no parent, no children, related: none.
- `python3 skill_dev/knowledge-management/scripts/kb.py archive recKeYy9bxAXG9F3h2K` (dry run) -> "archive temp (recKeYy9bxAXG9F3h2K) DRY RUN: nothing written", exit 0.

## Proposed writes
After the user confirms (not yet given):
- `python3 skill_dev/knowledge-management/scripts/kb.py archive recKeYy9bxAXG9F3h2K --yes` (sets is_active=false and deleted_at on knowledges record recKeYy9bxAXG9F3h2K; CLI reads back to verify)
