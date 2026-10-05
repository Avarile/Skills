I checked your knowledge base first. You already have a **`deployment - caddy`** knowledge type (it currently holds "Caddy - Cache issues"), and no existing entry covers this command on its own. The closest match is a passing `sudo caddy reload` line at the end of "Caddy Server - Config Examples & Static File Serving". So I'll add this as a new, short entry:

**Title:** Caddy - Reload config without downtime
**Type:** deployment - caddy
**Related:** Caddy Server - Config Examples & Static File Serving

```markdown
Reload Caddy's config gracefully, with zero downtime (no dropped connections):

    caddy reload --config /etc/caddy/Caddyfile

- Caddy loads and checks the new config first. If it's invalid, the running config stays in place, so a typo won't take sites down.
- It goes through the admin API (default `localhost:2019`), so Caddy must already be running with the admin endpoint enabled.
- Prefix with `sudo` if the Caddyfile or admin socket needs root.
- If Caddy runs in Docker: `docker exec caddy caddy reload --config /etc/caddy/Caddyfile`
- Optional check before reloading: `caddy validate --config /etc/caddy/Caddyfile`
```

Shall I save it like this? Or would you rather I add it as a line in the existing "Caddy Server - Config Examples" note?
