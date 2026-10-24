## Calls made
- Read project-management/SKILL.md
- Read references/schema.md
- grep references/workflows.md (lifecycle section) and head of scripts/query.py
- ToolSearch select: query_records, get_table_schema, list_tables (schema load only)
- scripts/query.py on projects table (read): found "k3s Migration" recNEeZTYI9Z2KQyvXm, status preparing
- scripts/query.py on tasks with --search (read): HTTP 400, no data
- mcp__cyb-data__get_record tasks recfnikTFWJOSLkWPAE (read): Step 06 [DO] Wave 1 migration and cutover, backlog, due 2026-11-11

## Proposed writes
Pending the user's evidence and confirmation (task is backlog, never started):
1. mcp__cyb-data__update_record tableId=tblOMgDiajqa1moRRjE recordId=recfnikTFWJOSLkWPAE fields={"fldG7fZN9XhOa0lMy33":"finished_validating","fldn95wbkTqefn18WdO":"2026-10-03"} (optionally "fldj3Xb1g9nUX4iFqE0":"2026-10-03" for started_at). Note underscore spelling; "finished-validating" would silently clear the field. Read back after.
2. cd /Users/avarilewang/Documents/agentSkills && set -a && . ./.env && set +a && python3 .claude/skills/project-management/scripts/write.py ctx-append (record recfnikTFWJOSLkWPAE, section "Log", line "2026-10-03 finished_validating. Evidence: <user's evidence>"), dry-run first, then --yes after confirmation.
