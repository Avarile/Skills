## Calls made
- Read project-management SKILL.md
- ToolSearch select: mcp__cyb-data__query_records, get_table_schema, list_tables
- Read references/schema.md
- Read scripts/query.py and scripts/write.py headers (usage only)
- query.py tbliD8gcOTRk9RZ9SmR (all projects, projected fields) -> found "Website Refresh" recPQX68gHFcXnemmSI
- query.py tblOMgDiajqa1moRRjE filter belong_project is recPQX68gHFcXnemmSI (14 tasks; progress, context, is_active)
- mcp get_table_schema tblOMgDiajqa1moRRjE (probe: no due_date field, so Due: line in context)
- query.py tasks filter project + progress isAnyOf backlog,in-progress,onhold (8 open tasks, full context)
- query.py --help (usage check)

## Proposed writes
Awaiting user confirmation (8 records, bulk). No due_date field exists, so for each task: get_record, replace only line 1 of context, update_record with the full context, read back. (write.py bulk-update sets the same value on many records, so it does not fit per-task dates; ctx-append only appends.) Then `write.py ctx-append` a dated "## Log" line "2026-10-03 Due +5d, client moved kickoff" per task (with --yes only after confirmation).

mcp__cyb-data__update_record, tableId tblOMgDiajqa1moRRjE, field fldaOhjcXqdiF3IRVB1 (context), line 1 changes:
- recgYBq6AfDGq8TeWLu: Due: 2026-10-01 -> Due: 2026-10-06
- recE67kh7XwSFwnfUc9: Due: 2026-10-08 -> Due: 2026-10-13 (keep body "Check progress against the estimate and re-check the top risks.")
- recRIpVszfcWDhefxM5: 2026-10-13 -> 2026-10-18
- rec30teG2CNfBR6WeOl: 2026-10-19 -> 2026-10-24
- recutajTbhaKK9vyOMj: 2026-10-26 -> 2026-10-31
- reck1J19UpJzSTujit6: 2026-10-28 -> 2026-11-02
- recOfHGHeDD00KV9a07: 2026-11-02 -> 2026-11-07
- recujFZQLOMlIaND6M8: 2026-11-02 -> 2026-11-07
Not touched: Steps 01-06 (finished_validating).
