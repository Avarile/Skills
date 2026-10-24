## Calls made
- Read project-management/SKILL.md, references/workflows.md, references/schema.md
- ToolSearch select for mcp__cyb-data__query_records, list_tables, get_table_schema (schemas only, no data calls via MCP)
- assign.py tasks --contact Avarile (read-only; output: 2 open, empty sections)
- assign.py workload (read-only)
- assign.py tasks --contact Avarile --json (read-only)
- query.py tasks --filter 'assigned_to isNot x' --count (read-only)
- query.py tasks, projection title/progress/priority/project/assignee/context/is_active, filter assigned_to isNotEmpty (read-only, 12 rows)
- .env sourced only to load the token into the environment; not read or printed

## Proposed writes
none
