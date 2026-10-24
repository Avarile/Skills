## Calls made
1. `cat skill_dev/knowledge-management/SKILL.md` + `ls -R skill_dev/knowledge-management`: read the skill (human mode; capture = dry-run, preview, OK, then --yes).
2. `cat references/workflows.md references/entry-format.md references/taxonomy.md`: read the capture workflow, entry skeleton and type-choice rules.
3. `python3 skill_dev/knowledge-management/scripts/kb.py find caddy reload`: 2 matches: recFfUwBOXZH65aBe02 (Caddy Server - Config Examples & Static File Serving, deployment - web server) and rec0kZXjWjYHJUDVWKW (Private Docker Registry guide). Neither is a dedicated reload entry.
4. `kb.py find caddy`: 12 matches. Caddy-specific ones: recFfUwBOXZH65aBe02 and recIOMDhfaSCkEAghOj (Caddy - Cache issues, deployment - caddy). The rest are server-setup scripts that install Caddy.
5. `kb.py types`: 42 types. `deployment - caddy` (reclMCYETdgQJ6oBZrv, 1 entry) is the most specific fit; `deployment - web server` (recKFnqunxQUkHcnWGo, 3) is the alternative.
6. `kb.py get recFfUwBOXZH65aBe02 --toc`: 4.2k chars, one heading, "How to serve a static file for a domain".
7. `kb.py get recFfUwBOXZH65aBe02 --json` (grep for "reload"): only mention is "Restart the Caddy Server: `sudo caddy reload`". No --config form and no note on downtime.
8. `kb.py type "deployment - caddy"`: no description; 1 entry, recIOMDhfaSCkEAghOj Caddy - Cache issues.
9. `kb.py find caddy --limit 20 --titles`: same 12 titles. No existing "reload" title, so no exact-title duplicate.
10. Write body to scratchpad caddy-reload.md + `kb.py capture --title "Caddy - Reload config without downtime" --type "deployment - caddy" --body-file <scratchpad>/caddy-reload.md --related recFfUwBOXZH65aBe02 recIOMDhfaSCkEAghOj` (dry run, no --yes): DENIED by the Claude Code auto-mode permission classifier ("External System Writes"). It did not run and I did not retry it.

## Proposed writes
After the user says OK (and after the dry run is allowed and its preview shows no BLOCKED / similar / secret? warnings):

1. Body file `caddy-reload.md`:
```markdown
Reload Caddy's configuration in place, without stopping the server or dropping connections.

## When to use
- After editing `/etc/caddy/Caddyfile` and you want the change live with no downtime.

## Steps
1. Reload the config:
   ```bash
   caddy reload --config /etc/caddy/Caddyfile
   ```

## Caveats
- If the new config is invalid, the reload fails and Caddy keeps running on the old config.

## Sources
- Related: Caddy Server - Config Examples & Static File Serving (recFfUwBOXZH65aBe02)
```

2. Dry run (preview):
`python3 skill_dev/knowledge-management/scripts/kb.py capture --title "Caddy - Reload config without downtime" --type "deployment - caddy" --body-file caddy-reload.md --related recFfUwBOXZH65aBe02 recIOMDhfaSCkEAghOj`

3. Write:
`python3 skill_dev/knowledge-management/scripts/kb.py capture --title "Caddy - Reload config without downtime" --type "deployment - caddy" --body-file caddy-reload.md --related recFfUwBOXZH65aBe02 recIOMDhfaSCkEAghOj --yes`
This creates 1 knowledges record (type reclMCYETdgQJ6oBZrv) and adds related_knowledge on both sides to recFfUwBOXZH65aBe02 and recIOMDhfaSCkEAghOj. Then report the new id.

Alternative if the user picks it: `kb.py append recFfUwBOXZH65aBe02 --text-file caddy-reload-note.md` (then `--yes`) instead of a new entry.
