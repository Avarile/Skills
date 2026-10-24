## Calls made
- Read project-management/SKILL.md; listed skill dir
- Read references/workflows.md (doctor section) and references/schema.md (grep/head)
- Read head of scripts/query.py and scripts/rollup.py
- rollup.py portfolio --today 2026-10-03 (read-only)
- query.py --count on goals and projects tables (read-only)
- query.py full reads of tasks, projects, goals tables with projections (read-only, saved to scratchpad)
- Local python analysis of the saved JSON
- rollup.py project recPQX68gHFcXnemmSI --today 2026-10-03 (read-only)
- No MCP tools, no secrets read, no writes.

## Proposed writes
All need user confirmation first (counts shown).
1. Archive 89 orphan tasks: `python3 scripts/write.py bulk-update` on tasks with `fld6X3nrMTQlYiV5XSa isEmpty`, set `fldJMclfBagyBukSxoy` = false (dry-run first, then --yes after the user confirms 89 rows; may need an id-based/filtered form).
2. After user names a lead: mcp__cyb-data__update_record on project recNEeZTYI9Z2KQyvXm, `lead_by` fldJKSNWzxTU1K5o83t = {"id": "<contact id>"}.
3. After user supplies a mitigation: edit the CMS API risk row in Website Refresh (recPQX68gHFcXnemmSI) `## Risk Register` via read-modify-verify; and `write.py ctx-append` a `### 2026-10-03 · 🟡 AMBER` entry under `## Status Log`.
4. After user picks owners: assign.py for tasks in Website Steps 09, 10, 13, 14 and k3s tasks (dry-run first).
