## Calls made

1. `ToolSearch select:mcp__cyb-data__list_bases,list_tables,query_records,get_table_schema,get_record,get_record_neighbors,list_spaces` -> loaded 7 read-only tool schemas
2. `mcp__cyb-data__list_bases` -> 1 base: data-centre `bseJEuE54y5caWO0Xc8`
3. `mcp__cyb-data__list_tables(baseId=bseJEuE54y5caWO0Xc8)` -> 21 tables; projects `tbliD8gcOTRk9RZ9SmR`, knowledges `tblVTWb1kxXSFPBq4Fq`, knowledge_type `tblWcq6Kof1AFHvbC5e`, tasks `tblOMgDiajqa1moRRjE`
4. `mcp__cyb-data__get_table_schema(projects)` -> found link field `refer_knowledge` `fldCw3cnpw8EWs09C1v` (manyMany, one-way, to knowledges)
5. `mcp__cyb-data__get_table_schema(knowledges)` -> fields title/context/knowledge_type/knowledge_parent/related_knowledge
6. `mcp__cyb-data__query_records(projects, search="Nebula")` -> project `recjwiijjBO4wKg2XAl` "Game Design Nebula-of-Cybernetics" (#33, in-progress, 11 tasks, lead Avarile, no refer_knowledge); search also returned 2 unrelated projects
7. `mcp__cyb-data__query_records(knowledges, search="Nebula", projection=title/type/parent/id/active)` -> search parameter ignored; returned the first 50 entries unfiltered, none relevant
8. `mcp__cyb-data__query_records(knowledges, search="game", same projection)` -> same unfiltered first 50, which confirms the search param has no effect
9. `mcp__cyb-data__query_records(knowledge_type, take=100)` -> 42 types; no game-design type (closest: "WOW" = AzerothCore server ops)
10. `mcp__cyb-data__query_records(knowledges, skip=50, take=300, projection=title/type/parent)` -> remaining 83 entries (133 total); none about game design, Nebula, combat or lore
11. `mcp__cyb-data__get_record_neighbors(projects, recjwiijjBO4wKg2XAl)` -> 11 tasks + lead contact; no knowledge links
12. `mcp__cyb-data__get_table_schema(tasks)` -> tasks also have `refer_knowledge` `fldJzsKyzBaDFt7bHIu`
13. `mcp__cyb-data__get_record(tasks, recTHIT7QmYbj5mf0XM)` -> schema clean-up task (closed); refers to repo files (ship.interface, verify_naming.py); no refer_knowledge
14. `mcp__cyb-data__get_record(tasks, recasNvax1skg7qqIWC)` -> lore task (closed); refers to GamePlay/lore_specification.md, tools/lore_tables.py, verify_lore.py, Reference/lore.ts; no refer_knowledge
15. `Bash mkdir -p .../outputs` -> created output dir

## Proposed writes

None run. I'd only run these if the user picks option 2 and gives the repo path:

1. `mcp__cyb-data__create_records(tableId=tblWcq6Kof1AFHvbC5e, records=[{fldvL1LqKmEAfNKVBCO: "game design - nebula of cybernetics"}])` -> new type id `<TYPE_ID>`
2. `mcp__cyb-data__create_records(tableId=tblVTWb1kxXSFPBq4Fq, records=[{fldROFj15OlD8COVxX0: "Nebula of Cybernetics - Design Doc Index", fldAEK8ULw9urxE0qiF: {id: "<TYPE_ID>"}, fld5tr2rH8oJXLrjUo9: "Repo: <REPO_PATH>\n\n## Design docs\n- GamePlay/lore_specification.md (premise, factions, regions, manufacturer houses)\n- GamePlay/* (8 gameplay docs, checked by verify_gameplay)\n- Reference/lore.ts, ship.interface, player.interface\n\n## Verifiers\n- verify_lore.py (37 checks), verify_naming.py (8 checks), verify_gameplay; 15 verifiers + tsc in total\n\n## Settled decisions\n- 4 authorities: Aurelian Admiralty, Kestrel Charter, Cindral Syndics, Tannhau Pilotage\n- 4 hostile factions: Free Corsairs, Lettered Captains, Gravewatch Warbands, Revenant Line\n- Combat uses rounds (shotsPerRound etc.); repairRatePerTurn keeps 'Turn' (24-h tender rate)"}])` -> new knowledge id `<KNOW_ID>`
3. `mcp__cyb-data__update_record(tableId=tbliD8gcOTRk9RZ9SmR, recordId=recjwiijjBO4wKg2XAl, fields={fldCw3cnpw8EWs09C1v: [{id: "<KNOW_ID>"}]})` -> link it to the project (the field is currently empty, so nothing gets overwritten)
