## Calls made
- ToolSearch select:mcp__cyb-data__list_tables,get_table_schema,query_records
- mcp__cyb-data__list_tables (baseId bseJEuE54y5caWO0Xc8)
- mcp__cyb-data__get_table_schema (tasks tblOMgDiajqa1moRRjE)
- mcp__cyb-data__query_records (tasks, take 200; 115 records, saved to a tool-results file)
- Bash: python3 summarising the saved tasks result (local read only)
- mcp__cyb-data__get_table_schema (contacts tbl6730ZOe0zToNrcIr)
- mcp__cyb-data__query_records (contacts, projection title/tasks/is_active)
- Bash: mkdir and write the two output files

## Proposed writes
none (only if the user confirms: create_records on tasks tblOMgDiajqa1moRRjE with title, priority "urgent", progress "backlog", assigned_to set to the chosen contact; the exact record would be agreed with the user first)
