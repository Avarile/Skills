Not saved yet. You need to decide one thing first: this env includes a password, and `deployment - docker-compose` isn't a credential type.

**Decision needed: where should the password go?**
1. **As you asked:** one entry under `deployment - docker-compose` with both lines, password included. Note that every entry in that type is readable unredacted, and the password would sit next to the compose configs instead of with your other credentials.
2. **Split it (my recommendation):** keep `DB_HOST=10.0.0.5` and the variable name `DB_PASSWORD` in the docker-compose entry. Put the actual password in a separate entry under `credential_login` (or `credentials`) titled `Staging DB - Password`, and link the two with "related".
3. **All of it under `credentials`** instead of docker-compose.

**What I checked**
- No staging DB env entry exists yet. `find staging` only matched `K3S - Cheatsheet` and `PM2 - Process Manager Commands & Usage`, and neither is related. The 8 entries in `deployment - docker-compose` are all compose files for other stacks, so there's nothing to add this to. It would be a new entry.
- The entry I drafted (option 1):
  - **Title:** `Staging DB - docker-compose env`
  - **Type:** `deployment - docker-compose` (reccVgbTtiSGacQURZG)
  - **Body:** a one-line summary, `## When to use`, `## Reference` with `DB_HOST=10.0.0.5` and `DB_PASSWORD=«SECRET-SHOWN»`, `## Caveats` (staging only) and `## Sources` (from you, 2026-10-05)
  - **Links:** none
- The dry run of the save didn't run: Claude Code's permission check blocked it because the command contains the password in plain text. If you pick option 1 or 3, that check will probably block the save too. You can either allow it once in Claude Code's permission settings, or run the command yourself. Option 2 avoids most of this, because only the separate credential entry holds the password.

Reply 1, 2 or 3, or tell me another title. I'll run the dry run, show you the preview, then save.
