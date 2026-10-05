## Calls made

1. `ToolSearch select:mcp__cyb-data__list_spaces,list_bases,list_tables,query_records,get_table_schema,get_record,get_record_neighbors`: loaded 7 read-only cyb-data tool schemas.
2. `mcp__cyb-data__list_bases`: 1 base, `data-centre` (bseJEuE54y5caWO0Xc8).
3. `mcp__cyb-data__list_tables(baseId=bseJEuE54y5caWO0Xc8)`: 21 tables; knowledge lives in `knowledges` (tblVTWb1kxXSFPBq4Fq).
4. `mcp__cyb-data__get_table_schema(tblVTWb1kxXSFPBq4Fq)`: fields title, context (markdown), knowledge_type link, knowledge_parent, related_knowledge, is_active, deleted_at, etc.
5. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, search="k3s")`: output too large (311 KB) and saved to file. The `search` param seemed to have no effect, since it returned the first 50 records unfiltered.
6. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, search="backup")`: returned output identical to call 5, which confirmed that search does not filter.
7. `Bash: cmp + head` on the two saved outputs: identical; previewed JSON.
8. `Bash: python parse of saved page 1`: listed 50 titles and flagged k3s/backup hits. Relevant: #45 "K3S - Data: Management" (recVJ2Zys9euu8JHsJQ), #44 "K3S initite on HomeLab", #43 "K3S - Migration setup script - TEMP", #46 "K3S - Create new service", #47 "K3S - Cheatsheet", #19 "Database - Regular Backup Scripts (MariaDB Crontab)".
9. `mcp__cyb-data__query_records(tblVTWb1kxXSFPBq4Fq, skip=50, take=100, projection=[title,type,id,is_active])`: remaining 83 records (hasMore=false). Only k3s hit: #130 "K3s-Infras" (recMhxaQLBPrGzNdDeZ, Infra - services, 2026-08-31).
10. `Bash: python print recVJ2Zys9euu8JHsJQ`: full "K3S - Data: Management" note covering hostPath layout under /home/avarile/k3s-data, tar backup example, service-native exports, rollout-restart after restore, and "no automated backup" caveat.
11. `Bash: python grep backup/snapshot/etcd in other K3S records`: found Cheatsheet §25 Backup & Restore (SQLite/etcd), migration notes (pg_dump, redis --rdb, rsync), and the gitignored secrets note.
12. `Bash: python show sections` of the migration TEMP note, HomeLab note (lines 0-80, 190-220) and Cheatsheet lines 1139-1176: read details. HomeLab stack lists MinIO, which is absent from the data note.
13. `mcp__cyb-data__get_record(tblVTWb1kxXSFPBq4Fq, recMhxaQLBPrGzNdDeZ)`: "K3s-Infras" credentials note with endpoints at 192.168.0.103 for Postgres, Redis, MySQL, MongoDB, RabbitMQ, MinIO, Meilisearch, Qdrant, plus Plane/Twenty/Gitea/Vaultwarden. It contains passwords/keys (values «SECRET-SHOWN» in the tool result; deliberately NOT echoed in the reply).

## Proposed writes

none. The question was a read-only recall/how-to.

(I offered the user an optional follow-up but did not run it: after a yes, I would `mcp__cyb-data__update_record` on tblVTWb1kxXSFPBq4Fq / recVJ2Zys9euu8JHsJQ, field `fld5tr2rH8oJXLrjUo9` (context), adding MySQL, MongoDB, MinIO and Vaultwarden to the data-layout table and backup section. Exact text would be drafted and confirmed with the user first.)
