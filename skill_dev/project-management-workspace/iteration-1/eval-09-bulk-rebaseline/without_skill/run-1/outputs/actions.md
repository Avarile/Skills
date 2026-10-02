## Calls made
- ToolSearch select: cyb-data list_tables, get_table_schema, query_records, get_record_neighbors
- list_tables(base bseJEuE54y5caWO0Xc8)
- get_table_schema(tasks tblOMgDiajqa1moRRjE)
- query_records(projects tbliD8gcOTRk9RZ9SmR, search "Website Refresh")
- query_records(tasks, search "Step", projection title/progress/dates/project/active/context, take 100)
- query_records(tasks, search "Step", skip 100, take 100)
- Bash: mkdir -p outputs dir (and write response.md / actions.md)

## Proposed writes
Not executed; need user confirmation. Tool: mcp__cyb-data__update_record on tasks (tblOMgDiajqa1moRRjE), field fldaOhjcXqdiF3IRVB1 (context). Each call replaces only the first "Due:" line and keeps the rest of the text unchanged:
- recgYBq6AfDGq8TeWLu (Step 07): "Due: 2026-10-01" -> "Due: 2026-10-06"
- recE67kh7XwSFwnfUc9 (Step 08): "Due: 2026-10-08" -> "Due: 2026-10-13" (rest of text kept: "Check progress against the estimate and re-check the top risks.")
- recRIpVszfcWDhefxM5 (Step 09): "Due: 2026-10-13" -> "Due: 2026-10-18"
- rec30teG2CNfBR6WeOl (Step 10): "Due: 2026-10-19" -> "Due: 2026-10-24"
- recutajTbhaKK9vyOMj (Step 11): "Due: 2026-10-26" -> "Due: 2026-10-31"
- reck1J19UpJzSTujit6 (Step 12): "Due: 2026-10-28" -> "Due: 2026-11-02"
- recOfHGHeDD00KV9a07 (Step 13): "Due: 2026-11-02" -> "Due: 2026-11-07"
- recujFZQLOMlIaND6M8 (Step 14): "Due: 2026-11-02" -> "Due: 2026-11-07"
Optional (ask first): update_record on project recPQX68gHFcXnemmSI context, appending a Status Log entry "### 2026-10-03 ... Client moved kickoff; open tasks (Steps 07-14) pushed +5 days."
Confirm with user: calendar-day vs weekday shift, Step 07 already overdue, optional status-log entry.
