## Calls made
- Read project-management/SKILL.md
- Read references/workflows.md (capture section applies)
- Read references/schema.md
- ToolSearch select: query_records, get_table_schema, list_tables
- mcp__cyb-data__query_records projects, search "Inbox" -> 3 projects (Website Refresh, k3s Migration, Inbox recGMngbWlVQCq9jzaC); search appears to return all rows
- mcp__cyb-data__query_records projects, search "staging" -> same 3 projects, none specific to staging
- mcp__cyb-data__get_table_schema tasks -> no due_date field, so Tier 0 (due date goes in context)
- No scripts run, no secrets read, no writes.

## Proposed writes
mcp__cyb-data__create_records on tblOMgDiajqa1moRRjE with one record (fields keyed by field ID):
- fldGqUoXO7oyq6ufX2Y (title): "Renew SSL certificate for staging"
- fld6X3nrMTQlYiV5XSa (belong_project): {"id": "recGMngbWlVQCq9jzaC"}
- fldMTuydiWUFAgtqAPX (priority): "urgent"
- progress left at default backlog; no context/due (none given); no assigned_to
Then get_record to read back title, project, priority, progress. Ask the user to confirm Inbox vs k3s Migration and whether to add a "Due: YYYY-MM-DD" line in fldaOhjcXqdiF3IRVB1 (context).
