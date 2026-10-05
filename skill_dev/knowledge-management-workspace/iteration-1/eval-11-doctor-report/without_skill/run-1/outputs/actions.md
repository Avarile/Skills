# Actions

## Calls made

1. ToolSearch `select:mcp__cyb-data__list_spaces,...list_views` -> loaded 9 read-only cyb-data tool schemas
2. mcp__cyb-data__list_spaces -> 1 space: Work (spc1V7zXKTD999538hf)
3. mcp__cyb-data__list_bases -> 1 base: data-centre (bseJEuE54y5caWO0Xc8)
4. mcp__cyb-data__list_tables {baseId: bseJEuE54y5caWO0Xc8} -> 21 tables; knowledges = tblVTWb1kxXSFPBq4Fq, knowledge_type = tblWcq6Kof1AFHvbC5e
5. mcp__cyb-data__get_table_schema {tblVTWb1kxXSFPBq4Fq} -> fields title, context, created_at, updated_at, deleted_at, is_active, id, knowledge_type (link), knowledge_parent / knowledges (self-link), related_knowledge (m:m self-link; symmetric field fldTvK8TAoC33yBFbqa not present in schema)
6. mcp__cyb-data__get_table_schema {tblWcq6Kof1AFHvbC5e} -> fields incl. unused `credentials` text field, child_types (symmetric fldhCf1NQf4Tl4VDFMN missing) and one-way parent_type
7. mcp__cyb-data__list_views {tblVTWb1kxXSFPBq4Fq} -> Grid view, Form
8. mcp__cyb-data__query_records {tblWcq6Kof1AFHvbC5e, take 200} -> 42 types with linked entries; 4 empty types; only 1 parent_type set
9. mcp__cyb-data__query_records {tblVTWb1kxXSFPBq4Fq, take 200, projection: metadata fields} -> 133 records, hasMore false (output saved to file; parsed with python)
10. Bash python: tabulate metadata -> all is_active=true, no deleted_at, 4 untyped (#69, #96, #110, #131), 1 knowledge_parent link (#73->#72), 0 related_knowledge links, autonumber gaps 48/58/62/66/136-177
11. mcp__cyb-data__query_records {tblVTWb1kxXSFPBq4Fq, skip 0, take 50, projection title/context/id} -> saved to file (297k chars)
12. mcp__cyb-data__query_records {tblVTWb1kxXSFPBq4Fq, skip 50, take 50, projection title/context/id} -> saved to file (59k chars)
13. mcp__cyb-data__query_records {tblVTWb1kxXSFPBq4Fq, skip 100, take 50, projection title/context/id} -> 33 records inline (adult bookmarks #105-127, Career, Python, K3s-Infras with ~15 secrets, llama.cpp, Apple / Cybernetics-CRM / Google / MyGov credentials «SECRET-SHOWN», Linux System Check, Tailscale)
14. Bash python: context length + secret-keyword scan -> empty #61, near-empty #3 (10 chars), #69, #9; private-key blocks in #42; 55 missav.ai bookmark records
15. Bash python: masked excerpts of flagged records -> confirmed secret types (private keys, account passwords, API keys/tokens) without printing values; #49 "temp" is an Okta email draft
16. Bash python: pairwise similarity (difflib) on technical entries -> #7 == #40 (1.0), #6 ~ #41 (0.84), #22 ~ #32 (0.52)
17. Bash python: first lines of #6/#7/#40/#41/#8/#22/#31/#32/#34/#35/#59/#68/#69 -> titles of #6 and #7 are swapped
18. Bash python: literal secret-value detection per record -> secrets in #1, #2, #7, #10, #13-16, #22, #23, #26, #32, #40, #52, #53, #57, #64, #67, #71 (+ page-3: #130, #132, #133, #134, #178)
19. Bash python: password-stem reuse check -> Google-account password stem appears in #13, #18, #22, #26, #53, #57, #67 (+#134); Sony/Gmail/MyGov stems shared (#52, #71, #178); DB password stems reused across #15/#19/#23/#53
20. Bash python: broken Obsidian embeds / chat filler -> #20 (2 image embeds), #54 and #129 (AI chat filler)
21. Bash mkdir outputs dir; Write response.md, actions.md

## Proposed writes

None executed (read-only mode; awaiting user confirmation per batch). Table ids: knowledges = tblVTWb1kxXSFPBq4Fq; knowledge_type = tblWcq6Kof1AFHvbC5e. Field ids: title fldROFj15OlD8COVxX0, context fld5tr2rH8oJXLrjUo9, is_active fldZKMuaBBPd6tIzSG3, deleted_at fldNS9SNNWG07NnBZhE, knowledge_type fldAEK8ULw9urxE0qiF; type title fldvL1LqKmEAfNKVBCO.

Soft-delete below = `update_record {tableId: tblVTWb1kxXSFPBq4Fq, recordId: X, fields: {fldZKMuaBBPd6tIzSG3: false, fldNS9SNNWG07NnBZhE: "2026-10-05T00:00:00Z"}}`.

### Batch 1 - Secrets (only after user confirms values are in Vaultwarden)
- update_record knowledges for each of:
  - recWPmDFSwbJbIVoKCM (#9), recqZfCqajtInlIHzet (#42), recN8QjafSwRROyAiKx (#52), recfHx7dACFCUx0c3OZ (#70), recbxCyeE7j3RJafZyH (#71), reclmpAtezHleTu6H3w (#64), reclMYoysKy9RED81xm (#65), recU49SQVKC9JHBcB0L (#132), recbImbz6PyWPaMFgoC (#133), rec20QDBm6GrO02PFsr (#134), reclS75WbibW6UkQoo8 (#178), recn1oxlt0DlhDmfya5 (#3)
  - set fld5tr2rH8oJXLrjUo9 = "Stored in Vaultwarden -> <item name>" (+ non-secret notes such as URL/username kept, e.g. #65 keep url + base id + MCP setup steps with token replaced by "<token from Vaultwarden>")
- update_record recMhxaQLBPrGzNdDeZ (#130 K3s-Infras): context rewritten keeping endpoints/notes/flags, every password/key replaced with "<Vaultwarden: K3s/<service>>"
- update_record for compose/script docs, replacing literal passwords with ${VAR} placeholders: recjjkJqhOlcT1LGR4j (#1), recrHVpZPhA85MMsXhU (#2), rec2Ug6TCRr1cXEB2DA (#7), recWYk3ggRPh216Kjn8 (#15), rec3Fzo3QbCazp9Vb3R (#16), recensHzE0p2rnRPJIF (#22), recQAnzSLANbLcNGUSS (#23), recXgCbs4Lq0yHhSmlg (#32), recse1nz5Cj1PcM9nNg (#53), rec0MruoUGpkc0dq1nS (#13), recDzYdJgemOBKdwENj (#26), recf8acev7YNADWNodc (#57), recXxgWzuTCBVGTUKFQ (#67), recOD1eXrtFnEkkpcjz (#18), rechmTkIKELmVu4timk (#14), recEoIUtOBMnbTidmox (#19)
- delete_records {tableId: tblVTWb1kxXSFPBq4Fq, recordIds: ["recg1X28d8erjzUJB1m"]} (#10 "env for AARON AI uat - delete later"; hard delete because it is full of keys)
- (user action, not a DB write) rotate Google password, OpenAI keys, AI Gateway key, ElevenLabs key, Cybernetics tokens, K3s service passwords, Vaultwarden admin token

### Batch 2 - Adult bookmarks (55 records, #72-#88, #90-#127) - depends on user's choice
- (a) create_table `media_bookmarks` (title, url, performers, tags) -> create_records copying the 55 rows -> delete_records on the 55 knowledges rows -> delete_records on the 6 knowledge_type rows recE0HKIvhQokKkpjZn, recDTAcdE7yDH2srfHl, recxOYtYswK3DjkiBuv, recmuu41zt3IvBMFrus, reciP5r05J7NwmL9Xzs, recDMQixMn49tUuKR9i
- (b) export to local file, then the same two delete_records calls
- (c) keep, but: delete_records ["rech2Hpkg0pyay4Od4N" (#96 empty dup), "recZzXzWruedCPu2Yoz" (#126 dup of #121)]; update_record recb3YY9ZHA4xDN8Ygv (#80) title = "JUQ-324 Married Woman Personal Trainer Reverse NTR Ryo Ayumi"; update_record recrpK1QfQC40d4eTEX (#110) knowledge_type = recmuu41zt3IvBMFrus

### Batch 3 - Duplicates / mislabels
- update_record recUU9OzVGzIIZn9LuR (#6) title = "new-server-ubuntu-26.04 => basic app"
- update_record rec2Ug6TCRr1cXEB2DA (#7) title = "new-server-ubuntu-26.04 => security"
- soft-delete recg3LHM211E5Dlz6Cy (#40, identical to #7)
- soft-delete recqhcHmCpmtsOqVchC (#41, near-dup of #6)
- (optional, after user review) mark #31-#34 superseded / merge #8, #22, #32; merge #68/#69/#135; merge #59 into #35

### Batch 4 - Stubs / temp
- soft-delete rec0D0Tt2ufpVmyAXyg (#61 empty)
- soft-delete recKeYy9bxAXG9F3h2K (#49 "temp" email draft)
- ask user: fill or delete recn1oxlt0DlhDmfya5 (#3), reczTM2hGHt4tp5ptp3 (#38), rec1EzZvHScsSLv2PuR (#69); keep or retitle recukPJGr1EjdCI21G1 (#43 "...TEMP")
- update_record recCvYJZMMpqc1ckzB9 (#129) and recdzHCO7NI81IthoQl (#54): strip chat filler lines; recM4lYhjRTu8uRkMxS (#20): remove broken ![[Pasted image]] embeds

### Batch 5 - Taxonomy
- update_record knowledge_type (fldAEK8ULw9urxE0qiF):
  - recWPmDFSwbJbIVoKCM (#9) -> reczhbhKHQGqlnQd0Ft (credential_apikey)
  - recqZfCqajtInlIHzet (#42) -> reczHEbFR88wNAevZuy (credential_sshkey)
  - reclmpAtezHleTu6H3w (#64), reclMYoysKy9RED81xm (#65) -> rec0VDy61JX52AJ3e6k (credential_access_token)
  - rec20QDBm6GrO02PFsr (#134), recN8QjafSwRROyAiKx (#52), recbxCyeE7j3RJafZyH (#71), reclS75WbibW6UkQoo8 (#178) -> recrCG7skvK6sWI25Dl (credential_login)
  - recXxgWzuTCBVGTUKFQ (#67 vaultwarden tutorial) -> recha4MvklMZcPnILZU (deployment - new server) or a new self-hosting type (ask)
  - recg3LHM211E5Dlz6Cy (#40, if kept) -> recha4MvklMZcPnILZU
  - recNYcaChmcH4Qlu0W4 (#59 Lazyvim) -> recY59mq0llKHhmPZnZ (development tools - nvim)
  - rec1EzZvHScsSLv2PuR (#69) -> rec1ZApEYzFTzpQFmk8 (Linux - Commands)
  - recGC3HKV6Kph75eqLg (#131 llama.cpp) -> recUmDX4woSHoSr8Xth (general - knowledge) or new "ai - local llm" type (ask)
- delete_records tblWcq6Kof1AFHvbC5e ["recuRxDFsGEyO7u1waQ" (AI Gateway API KEy, empty), "recsRslx79Zu8j0To6G" (family - knowledge, empty; ask)] ; after re-filing, delete rec2wibJ2ccfsAk22i2 (credentials) once it has 0 entries
- rename types (proposal, ask first): WOW -> "gaming - wow server", Career -> "personal - career", Python related -> "development tools - python", TUI control - Tmux -> "development tools - tmux", Infra - services -> "deployment - k3s infra", Linux - Commands -> "linux - commands", k3s - operation -> "deployment - k3s operation", TEMP - Records -> remove after #43/#49 handled
- title typo fixes: recQRRNd3EAQ5arufg1 "K3S initiate on HomeLab"; recoMc5OaPzBrTMeeJd "MacOS Firewall walkthrough"; rec3evbvMTNdvCbSH1T "Tailscale --- Linux"; recn1oxlt0DlhDmfya5 "Wrenai - docker-compose"
- schema (ask, not urgent): drop unused knowledge_type.credentials field (fld1s2dEom17aZIu4nx); repair/remove broken related_knowledge symmetric link and the disconnected child_types/parent_type pair (no MCP tool to delete fields - would need UI)
