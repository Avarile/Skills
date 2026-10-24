## Calls made
1. ToolSearch `select:mcp__cyb-data__list_bases,list_tables,query_records,get_table_schema,get_record,list_spaces` -> loaded schemas
2. mcp__cyb-data__list_bases -> one base: data-centre (bseJEuE54y5caWO0Xc8)
3. mcp__cyb-data__list_tables(bseJEuE54y5caWO0Xc8) -> 21 tables; knowledges = tblVTWb1kxXSFPBq4Fq
4. mcp__cyb-data__get_table_schema(tblVTWb1kxXSFPBq4Fq) -> fields title (fldROFj15OlD8COVxX0), context (fld5tr2rH8oJXLrjUo9), created/updated, is_active, id, knowledge_type, parent, related
5. mcp__cyb-data__query_records(knowledges, search="kubernetes node labels") -> output too large, saved to file; turned out to be the first 50 records unfiltered (search not applied)
6. mcp__cyb-data__query_records(knowledges, search="kubernetes") -> identical output to #5 (search ignored), 50 records, hasMore=true
7. Bash: python parse of saved JSON, regex on kubernetes|k8s|k3s|kubectl|label -> hits in K3S - Cheatsheet (#47), K3S - Create new service (#46), K3S HomeLab/Data/Migration (#43-45), MicroK8S (#21), Onyx (false positive)
8. mcp__cyb-data__query_records(knowledges, skip=50, take=100, projection=title/id/is_active/deleted_at) -> remaining 83 records; one more candidate: K3s-Infras (#130)
9. Bash: python extract of lines matching label|nodeSelector|affinity|taint with context -> node-label commands in #47 (sections 3 and 20) and #46 (section 12: `kubectl label node workstation role=infra`)
10. mcp__cyb-data__get_record(recMhxaQLBPrGzNdDeZ "K3s-Infras") -> infra endpoints/credentials («SECRET-SHOWN»), no node labels
11. Bash: python print of node-management sections of #47 and #46, and node-related lines of #43/#44/#45/#21 -> confirmed content quoted in response; no other label mentions

## Proposed writes
none
