## Calls made
- ToolSearch select: cyb-data list_tables, query_records, get_table_schema, get_record_neighbors
- cyb-data list_tables (base bseJEuE54y5caWO0Xc8)
- cyb-data get_table_schema projects (tbliD8gcOTRk9RZ9SmR)
- cyb-data get_table_schema knowledges (tblVTWb1kxXSFPBq4Fq)
- cyb-data query_records projects, search "k3s", projection title/context/progress/refer_knowledge/is_active
- cyb-data query_records knowledges, take 200, projection title/knowledge_type/knowledge_parent/is_active (no context bodies, no credentials read)

## Proposed writes
Not executed; to be run only after the user confirms the selection. Exact call, using the strong matches:
- update_record: tableId tbliD8gcOTRk9RZ9SmR, recordId recNEeZTYI9Z2KQyvXm, fields { fldCw3cnpw8EWs09C1v (refer_knowledge): [ {id: recQRRNd3EAQ5arufg1}, {id: recVJ2Zys9euu8JHsJQ}, {id: recXh3R4KsS4ZGiMUD8}, {id: rec9TTSDoktu59fT89i}, {id: recMhxaQLBPrGzNdDeZ} ] } (add any probable entries the user approves)
Confirm with the user: which tier (strong only vs. strong + probable) and whether to include the TEMP script and MicroK8S guide.
