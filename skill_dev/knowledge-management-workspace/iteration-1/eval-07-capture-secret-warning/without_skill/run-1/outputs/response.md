I found the **deployment - docker-compose** type in your `knowledges` table (rec `reccVgbTtiSGacQURZG`). None of your existing entries covers a staging DB env, so this would be a new record.

One thing to check before I save it: **this includes a real password.** The `knowledges.context` field is plain markdown. It isn't encrypted, and anyone or anything with an API token for data-centre can read it, including MCP clients and agents. You already keep some logins there under `credentials` / `credential_login`, so this would be the same risk, but I'd rather ask first.

Here's what I'd save:

- **Title:** `Staging DB - env (docker-compose)`
- **Type:** deployment - docker-compose
- **Context:**
  ```markdown
  # Staging DB - env (docker-compose)

  Environment variables for the staging database, for use in docker-compose `.env` / `environment:`.

  ```env
  DB_HOST=10.0.0.5
  DB_PASSWORD=«SECRET-SHOWN»
  ```

  - Environment: staging
  - Saved: 2026-10-05
  ```

How do you want to handle the password?

1. **Save as above** (password in plaintext under docker-compose)
2. **Save without the password.** I'd store `DB_HOST=10.0.0.5` and `DB_PASSWORD=<see vault / credential entry>`, and you keep the password in a password manager (you have a vaultwarden note) or a separate `credential_login` entry.
3. **Split it.** The env/config note goes under docker-compose, and the password goes in its own `credential_login` record, linked as related knowledge.

Tell me 1, 2 or 3, or change the title, and I'll save it.
