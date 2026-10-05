## Calls made

1. `ToolSearch select:mcp__cyb-data__list_tables,query_records,get_record,get_table_schema,update_record,list_bases`: schemas loaded.
2. `mcp__cyb-data__list_bases`: one base, `data-centre` (bseJEuE54y5caWO0Xc8).
3. `mcp__cyb-data__list_tables(baseId=bseJEuE54y5caWO0Xc8)`: 21 tables. Knowledge table is `knowledges` (tblVTWb1kxXSFPBq4Fq).
4. `mcp__cyb-data__get_table_schema(tblVTWb1kxXSFPBq4Fq)`: fields include title fldROFj15OlD8COVxX0, context fld5tr2rH8oJXLrjUo9 (longText/markdown), is_active fldZKMuaBBPd6tIzSG3, deleted_at fldNS9SNNWG07NnBZhE, knowledge_type fldAEK8ULw9urxE0qiF.
5. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, search="Caddy")` with no projection: output too large (311k chars), saved to a tool-results file.
6. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, search="Caddy", projection=[title,is_active,deleted_at,id,updated_at], take=100)`: 100 records, hasMore=true. Search did not actually filter. "Caddy - Cache issues" (recIOMDhfaSCkEAghOj, id 39, active) is among them.
7. `Bash grep` for Caddy titles in the saved output: 5 Caddy titles. The only cache-related one is "Caddy - Cache issues".
8. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, projection=[title], skip=100, take=500)`: 33 more records, hasMore=false. No other Caddy or cache notes.
9. `mcp__cyb-data__get_record(tblVTWb1kxXSFPBq4Fq, recIOMDhfaSCkEAghOj)`: full note. knowledge_type is "deployment - caddy". context is a Caddyfile cache-header example plus an explanation of Next.js cache busting. No existing mention of /var/lib/caddy.

## Proposed writes

One write after the user confirms. `update_record` replaces the whole cell, so the value is the existing context exactly as returned by call 9, followed by the appended section:

```
mcp__cyb-data__update_record(
  tableId  = "tblVTWb1kxXSFPBq4Fq",
  recordId = "recIOMDhfaSCkEAghOj",
  fields   = {
    "fld5tr2rH8oJXLrjUo9": "<existing context, byte-for-byte as read>" +
      "\n\n## Update 2026-10-05\n\nClearing Caddy's data directory also fixed the issue:\n\n    /var/lib/caddy/.local/share/caddy\n"
  }
)
```

No other fields change: title, knowledge_type, is_active and links stay as they are. Afterwards I would read the record again with `get_record` to check that the append landed and the original text is intact.
