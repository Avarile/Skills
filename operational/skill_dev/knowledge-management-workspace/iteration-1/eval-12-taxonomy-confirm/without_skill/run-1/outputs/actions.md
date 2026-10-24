## Calls made

1. ToolSearch `select:mcp__cyb-data__list_tables,get_table_schema,query_records,list_bases,list_spaces,get_record` -> loaded schemas
2. mcp__cyb-data__list_bases -> 1 base: data-centre (bseJEuE54y5caWO0Xc8)
3. mcp__cyb-data__list_tables(bseJEuE54y5caWO0Xc8) -> 21 tables; knowledge_type = tblWcq6Kof1AFHvbC5e, knowledges = tblVTWb1kxXSFPBq4Fq
4. mcp__cyb-data__get_table_schema(tblWcq6Kof1AFHvbC5e) -> fields: title fldvL1LqKmEAfNKVBCO, context, is_active fldte086UL30roxKKAl, knowledges link, credentials, child_types fldehPY6CjjdpeK3H6j (oneMany, symmetric hidden fldhCf1NQf4Tl4VDFMN), parent_type fld924GlXY0tL5um2wk (manyOne self-link, one-way)
5. mcp__cyb-data__query_records(tblWcq6Kof1AFHvbC5e, take 200) -> 42 types, no existing "deployment" type. Six "deployment - *" types: docker-compose reccVgbTtiSGacQURZG, k8s recwKFT8vCKe1bm9LYn, new server recha4MvklMZcPnILZU, web server recKFnqunxQUkHcnWGo, private registry recdlqefhAQjKZZQeOE, caddy reclMCYETdgQJ6oBZrv. Only existing hierarchy: missav_meta_Ayumi_Ryo.parent_type = missav_meta (child_types unused everywhere)
6. mcp__cyb-data__query_records(system_info tblLAv8Qwl7SMXqYCPD) -> 1 row: base URL https://projects.avarile.com/, api token «SECRET-SHOWN» (not used)
7. mcp__cyb-data__query_records(table_references tbldqfviyb3Fx1YgJlg, search "knowledge_type") -> output too large, saved to a file. Grepped it for parent_type/child_types: no hierarchy conventions documented
8. ToolSearch `select:mcp__cyb-data__create_records,mcp__cyb-data__update_record` -> loaded write schemas (not called)

## Proposed writes

Waiting for the user to confirm, including whether to add the borderline types `k3s - operation` recK65efsm4TPQpUmzH, `Infra - services` recQPtbFE0X9fqR6ddI and `ci-cd - github-actions` recat51HM3YaxmUPFAT. If they're included, each gets the same update as step 2.

1. Create the parent type:
   mcp__cyb-data__create_records(tableId="tblWcq6Kof1AFHvbC5e", records=[{"fields": {"fldvL1LqKmEAfNKVBCO": "deployment", "fldte086UL30roxKKAl": true}}])
   -> returns new record id <NEW_ID>

2. Point each child at the parent (one call per record):
   mcp__cyb-data__update_record(tableId="tblWcq6Kof1AFHvbC5e", recordId="reccVgbTtiSGacQURZG", fields={"fld924GlXY0tL5um2wk": {"id": "<NEW_ID>"}})
   mcp__cyb-data__update_record(tableId="tblWcq6Kof1AFHvbC5e", recordId="recwKFT8vCKe1bm9LYn", fields={"fld924GlXY0tL5um2wk": {"id": "<NEW_ID>"}})
   mcp__cyb-data__update_record(tableId="tblWcq6Kof1AFHvbC5e", recordId="recha4MvklMZcPnILZU", fields={"fld924GlXY0tL5um2wk": {"id": "<NEW_ID>"}})
   mcp__cyb-data__update_record(tableId="tblWcq6Kof1AFHvbC5e", recordId="recKFnqunxQUkHcnWGo", fields={"fld924GlXY0tL5um2wk": {"id": "<NEW_ID>"}})
   mcp__cyb-data__update_record(tableId="tblWcq6Kof1AFHvbC5e", recordId="recdlqefhAQjKZZQeOE", fields={"fld924GlXY0tL5um2wk": {"id": "<NEW_ID>"}})
   mcp__cyb-data__update_record(tableId="tblWcq6Kof1AFHvbC5e", recordId="reclMCYETdgQJ6oBZrv", fields={"fld924GlXY0tL5um2wk": {"id": "<NEW_ID>"}})

3. Verify: mcp__cyb-data__query_records(tblWcq6Kof1AFHvbC5e, search "deployment") and check that all six show parent_type = deployment.

No renames, deletions or knowledge-entry changes unless the user asks for them.
