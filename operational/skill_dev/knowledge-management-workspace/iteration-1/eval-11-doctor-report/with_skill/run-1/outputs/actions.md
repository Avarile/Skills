## Calls made

All run from the repo root; `kb` = `python3 skill_dev/knowledge-management/scripts/kb.py`. All read-only.

1. `cat skill_dev/knowledge-management/SKILL.md` + `ls -R skill_dev/knowledge-management` -> skill instructions read (doctor is read-only, fixes need approval per group).
2. `cat references/workflows.md references/taxonomy.md` -> doctor/clean-up and merge workflows, type naming rules.
3. `kb doctor` -> 133 entries, 42 types, 76 actionable findings (A: 42 no description, 5 proposed parents, 4 non-standard names, 4 empty types; B: 4 untyped; C: 1 wrong type; D: 1 series without hub; E: 1 untitled, 3 temp, 4 empty; F: 7 near-dup pairs; G: 17 secrets outside credential types; H: 0 work links), 5 HTTP calls.
4. `kb doctor --help`; `kb doctor --limit 100` -> full lists for A (42 types) and G (17 entries).
5. (failed: zsh did not word-split `$K`, "no such file or directory") loop of `kb get <id> --max-chars 400` -> no result; re-run below.
6. `kb get <id> --max-chars 400` for recb3YY9ZHA4xDN8Ygv, recKeYy9bxAXG9F3h2K, recukPJGr1EjdCI21G1, recGC3HKV6Kph75eqLg, rec1EzZvHScsSLv2PuR, recn1oxlt0DlhDmfya5 -> untitled entry is JUQ-324 (missav); "temp" is an Okta SSO request draft for Meta; K3S TEMP is a 5.7k migration guide; llama.cpp is 235 chars of commands; health check is 1 smartctl line; Wrenai body is a 10-char password-like string («SECRET-SHOWN»; not shown in the reply).
7. `kb get <id> --toc` for rec2Ug6TCRr1cXEB2DA, recg3LHM211E5Dlz6Cy, recUU9OzVGzIIZn9LuR, recqhcHmCpmtsOqVchC, recensHzE0p2rnRPJIF, recXgCbs4Lq0yHhSmlg, recg1X28d8erjzUJB1m, rec0D0Tt2ufpVmyAXyg -> rec2Ug6 and recg3 have identical headings (security content); recUU9 holds the basic-deps content (so its title and rec2Ug6's are swapped); AARON env is a full .env file; mdadm is 0 chars.
8. `kb get <id> --max-chars 120` for rech2Hpkg0pyay4Od4N, recsiOjIozO1LiYDcWm, recUXZ2IZLFGF39vFBR, recZzXzWruedCPu2Yoz, recrpK1QfQC40d4eTEX -> JUR-629 rech2H is an empty untyped copy; the two JUR-330 entries point to different URLs (uncensored vs subtitled); UMD-892 features Mary Tachibana.
9. `kb types` -> 42 types, 129 typed entries; confirmed existing target types (Linux - Commands, k3s - operation, credential_login, missav_meta_Mary_Tachibana, general - knowledge).

## Proposed writes

None run. Each would be dry-run first (same command without `--yes`), shown to the user, then re-run with `--yes` **after the user approves that group**. Followed by `kb doctor` to report before/after counts.

### Group F (near-duplicates)
```
kb append recqhcHmCpmtsOqVchC --text-file uu9_unique.md --section "## Updates"   # only if `get` of both shows lines unique to recUU9OzVGzIIZn9LuR
kb archive rec2Ug6TCRr1cXEB2DA --yes
kb link rec2Ug6TCRr1cXEB2DA --related recg3LHM211E5Dlz6Cy --yes
kb archive recUU9OzVGzIIZn9LuR --yes
kb link recUU9OzVGzIIZn9LuR --related recqhcHmCpmtsOqVchC --yes
kb archive rech2Hpkg0pyay4Od4N --yes
kb link rech2Hpkg0pyay4Od4N --related recsiOjIozO1LiYDcWm --yes
kb link recensHzE0p2rnRPJIF --related recXgCbs4Lq0yHhSmlg --yes
kb link recQAnzSLANbLcNGUSS --related recse1nz5Cj1PcM9nNg --yes
kb link recUXZ2IZLFGF39vFBR --related recZzXzWruedCPu2Yoz --yes   # optional, user's choice
```
(`trace` not needed: doctor H shows 0 entries referenced by goals/projects/tasks.)

### Group C + D (New Server Init series)
```
kb link recg3LHM211E5Dlz6Cy --type "deployment - new server" --yes
kb capture --title "New Server Init" --type "deployment - new server" --body-file hub.md --yes   # hub.md = purpose + ordered step list with ids
kb link recg3LHM211E5Dlz6Cy --parent <hub id> --yes
kb link rec2fFF09HzGOa2mIdX --parent <hub id> --yes
kb link recqhcHmCpmtsOqVchC --parent <hub id> --yes
kb link recXgCbs4Lq0yHhSmlg --parent <hub id> --yes
kb link recXQfy6FFTVs892WuP --parent <hub id> --yes
kb tree <hub id>
```
(Optional renumbering via `kb link <id> --title "New Server Init - Step N ..." --yes` if the user wants it.)

### Group B + E (untyped / temp / empty / untitled)
```
kb link rec1EzZvHScsSLv2PuR --type "Linux - Commands" --yes
kb link recGC3HKV6Kph75eqLg --type "general - knowledge" --yes
kb link recrpK1QfQC40d4eTEX --type "missav_meta_Mary_Tachibana" --yes
kb link recb3YY9ZHA4xDN8Ygv --title "JUQ-324 Married Woman Personal Trainer Reverse NTR Ryo Ayumi" --yes
kb link recKeYy9bxAXG9F3h2K --title "Okta SSO for Meta Business - Owner Request" --type "general - knowledge" --yes   # or: kb archive recKeYy9bxAXG9F3h2K --yes
kb link recukPJGr1EjdCI21G1 --title "K3S - Migration to Another Machine" --type "k3s - operation" --yes
kb archive recg1X28d8erjzUJB1m --yes   # unless the AARON UAT is still live
kb link recn1oxlt0DlhDmfya5 --title "Wrenai - login" --type "credential_login" --yes   # or append the real compose file
kb archive rec0D0Tt2ufpVmyAXyg --yes   # or: kb append rec0D0Tt2ufpVmyAXyg --text-file mdadm.md --yes
```

### Group A (type tree)
```
kb type-set "deployment" --create --yes
kb type-set "database" --create --yes
kb type-set "search engine" --create --yes
kb type-set "<child>" --parent-type "deployment" --yes      # x6: caddy, docker-compose, k8s, new server, private registry, web server
kb type-set "<child>" --parent-type "database" --yes        # x5: backup, clickhouse, mariadb, postgresql, safety
kb type-set "<child>" --parent-type "search engine" --yes   # x2: meilisearch, qdrant
kb type-set "<child>" --parent-type "credentials" --yes     # x5: AI Gateway API KEy, credential_access_token, credential_apikey, credential_login, credential_sshkey
kb type-set "<child>" --parent-type "missav_meta" --yes     # x4: Mary_Tachibana, Meg_Fujiura, Morinaga_Iroha, NTR
kb type-set "Career" --title "career - knowledge" --yes
kb type-set "Python related" --title "development tools - python" --yes
kb type-set "WOW" --title "gaming - wow" --yes
kb type-set "AI Gateway API KEy" --title "credential_ai_gateway" --yes
kb type-set "<type>" --description "<one line>" --yes        # x42, drafted descriptions shown to the user first
kb types
```

### Groups G, H
None (information only).
