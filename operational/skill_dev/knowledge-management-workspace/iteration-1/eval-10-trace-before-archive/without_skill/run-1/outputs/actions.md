## Calls made

1. `ToolSearch select:mcp__cyb-data__list_tables,query_records,get_table_schema,get_record,get_record_neighbors,list_bases,list_spaces` -> schemas loaded
2. `mcp__cyb-data__list_spaces` -> one space: Work (spc1V7zXKTD999538hf)
3. `mcp__cyb-data__list_bases` -> one base: data-centre (bseJEuE54y5caWO0Xc8)
4. `mcp__cyb-data__list_tables(bseJEuE54y5caWO0Xc8)` -> 21 tables; knowledges = tblVTWb1kxXSFPBq4Fq, knowledge_type = tblWcq6Kof1AFHvbC5e
5. `mcp__cyb-data__get_table_schema(tblVTWb1kxXSFPBq4Fq)` -> fields: title, context, created_at, updated_at, deleted_at (fldNS9SNNWG07NnBZhE, date), is_active (fldZKMuaBBPd6tIzSG3, checkbox, default true), id, knowledge_type, knowledge_parent, knowledges (children), related_knowledge
6. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, search="temp", projection=[title,id,is_active,deleted_at,links], take 50)` -> search did not filter (returned rows 1-51, hasMore). Found title "temp" = recKeYy9bxAXG9F3h2K (#49, type TEMP - Records), plus "K3S - Migration setup script - TEMP" (#43, same type)
7. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, skip=50, take=200)` -> remaining 83 rows, no other title matching "temp" exactly. All 133 rows are is_active=true, so the table has no earlier archives to copy a convention from
8. `mcp__cyb-data__get_record(tblVTWb1kxXSFPBq4Fq, recKeYy9bxAXG9F3h2K)` -> title "temp", is_active true, created 2026-06-10, updated 2026-09-22, context = a draft email requesting info for Okta SSO on Meta business accounts (no secrets in it)
9. `mcp__cyb-data__get_record_neighbors(bseJEuE54y5caWO0Xc8, tblVTWb1kxXSFPBq4Fq, recKeYy9bxAXG9F3h2K)` -> one neighbor only: knowledge_type "TEMP - Records" (recbMjt3s269h8rOHLO) via fldAEK8ULw9urxE0qiF; no parent/children/related links; truncated=false
10. `mcp__cyb-data__get_table_schema(tblc5RVuBn9hW5u3bk3)` (auditlog) -> generic log table (title/context/generated_by_contact); no clear convention requiring a log row for an archive, so none proposed

## Proposed writes

Soft-archive (no hard delete), executed because the user explicitly asked to archive this one unambiguous record. It is reversible.

```
mcp__cyb-data__update_record(
  tableId  = "tblVTWb1kxXSFPBq4Fq",
  recordId = "recKeYy9bxAXG9F3h2K",
  fields   = {
    "fldZKMuaBBPd6tIzSG3": false,                      // is_active
    "fldNS9SNNWG07NnBZhE": "2026-10-05T00:00:00.000Z"  // deleted_at (archive date)
  }
)
```

Then verify with `mcp__cyb-data__get_record(tblVTWb1kxXSFPBq4Fq, recKeYy9bxAXG9F3h2K, projection=[fldZKMuaBBPd6tIzSG3, fldNS9SNNWG07NnBZhE])`.

No other writes. Leave the type link in place, and do not touch #43 "K3S - Migration setup script - TEMP" unless the user asks.
