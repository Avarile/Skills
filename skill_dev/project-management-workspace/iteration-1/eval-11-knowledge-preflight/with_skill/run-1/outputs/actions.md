## Calls made
- Read project-management/SKILL.md
- ToolSearch select: query_records, get_table_schema, list_tables, get_record_neighbors
- Bash: grep of references/workflows.md and references/schema.md (knowledge sections)
- mcp__cyb-data__query_records projects (search "k3s", projection title/progress/refer_knowledge/is_active) -> 3 rows, k3s Migration found
- mcp__cyb-data__query_records knowledges (search "k3s", projection title + knowledge_type only, take 50) -> 50 rows, hasMore true; not paged further

## Proposed writes
Only after the user picks (example if all five confirmed):
- mcp__cyb-data__update_record tableId tbliD8gcOTRk9RZ9SmR, recordId recNEeZTYI9Z2KQyvXm, fields {"fldCw3cnpw8EWs09C1v": [{"id":"recQRRNd3EAQ5arufg1"},{"id":"recXh3R4KsS4ZGiMUD8"},{"id":"recVJ2Zys9euu8JHsJQ"},{"id":"rec9TTSDoktu59fT89i"},{"id":"rec0uUoU0Z1EnJuKbE5"}]}, then read back to verify. Confirm which picks first.
