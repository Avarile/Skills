## Calls made
1. ToolSearch `select:mcp__cyb-data__list_tables,query_records,get_record,get_table_schema,list_bases` -> schemas loaded
2. mcp__cyb-data__list_bases -> one base: data-centre (bseJEuE54y5caWO0Xc8)
3. mcp__cyb-data__list_tables(bseJEuE54y5caWO0Xc8) -> 21 tables, including knowledges (tblVTWb1kxXSFPBq4Fq)
4. mcp__cyb-data__get_table_schema(tblVTWb1kxXSFPBq4Fq) -> fields: title, context, created_at, updated_at, deleted_at, is_active, id, knowledge_type, knowledge_parent, knowledges, related_knowledge
5. mcp__cyb-data__query_records(knowledges, search="Sony") -> output too large (search did not narrow results; got 50 unrelated records); saved to file
6. Bash: python parse of the saved file to list titles -> first 50 titles, no Sony match
7. mcp__cyb-data__query_records(knowledges, projection=[title], take=500) -> 133 titles; found "Sony Game Account" = recbxCyeE7j3RJafZyH
8. mcp__cyb-data__get_record(knowledges, recbxCyeE7j3RJafZyH) -> type=credentials, id 71, active, created/updated 2026-08-20T03:09Z, context "Sparutus\@gmail.com / Passwd: «SECRET-SHOWN»"

## Proposed writes
none
