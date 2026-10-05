## Calls made
- `cat skill_dev/knowledge-management/SKILL.md` + `ls -R` -> read skill; files listed
- `cat references/workflows.md`; `grep` references/schema.md -> pre-flight workflow (`for-work`, then `refer` picks); projects table `tbliD8gcOTRk9RZ9SmR`, title field `fldiDksJhyT8mDAhCBP`
- `kb.py for-work --help` + `grep` kb.py (cmd_for_work, work_record) -> for-work needs a project record id
- REST GET (via kb.T.get_records) projects filter title contains "Nebula" -> 1 record: `recjwiijjBO4wKg2XAl` "Game Design Nebula-of-Cybernetics"
- `kb.py for-work project:recjwiijjBO4wKg2XAl` -> linked 0; suggested Sony Game Account [credentials], K3S - Data: Management [deployment - k8s], Laptop sshkey [credentials]
- REST GET project record `recjwiijjBO4wKg2XAl` (all fields; one call failed first with a TypeError from projection=None, then succeeded) -> status in-progress, 11 tasks (combat R6-R9, schemas/.interface, ship fitting, stations, escort/hauling, lore/factions), description "Design all aspects of the space game 'Nebula of Cybernetics'"
- `kb.py find <q> --any --titles` (first attempt broke because a shell variable was quoted, re-run): nebula -> 0; game -> 2 (Sony Game Account, Laptop sshkey); combat -> 0; space ship -> 0; lore faction -> 0; schema interface -> 0
- `kb.py types` -> 42 types; nothing about game design; one game-related type "WOW" (rec03YZcMFvzCmq7mGE)
- `kb.py type WOW` -> 3 entries: Azerothcore Commands, Install script of install AzerothCore on Debian 13, World of Warcraft Deployment (all about deploying a server)
- `kb.py find <q> --any --titles`: design -> 1 (K3S - Data: Management); mechanic formula -> 0; station orbital planet -> 0; cybernetics -> 4 (2 API keys, 2 new-server entries)

## Proposed writes
none. The user hasn't picked anything, and no relevant entry exists. If the user later picks entries, the command would be:
`python3 skill_dev/knowledge-management/scripts/kb.py refer <ids> --to project:recjwiijjBO4wKg2XAl` (dry run), then the same with `--yes`.
If they pick option 2, the commands would be (after their OK for the new type):
`kb.py capture --title "Nebula of Cybernetics - <Aspect>" --type "game design - nebula-of-cybernetics" --new-type --body-file F --refer project:recjwiijjBO4wKg2XAl` (dry run), then `--yes`.
