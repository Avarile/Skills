I checked your knowledge base first. There's no dedicated entry for reloading Caddy. The closest one is **Caddy Server - Config Examples & Static File Serving** (`recFfUwBOXZH65aBe02`, type `deployment - web server`), and it only has a passing line: "Restart the Caddy Server: `sudo caddy reload`". It doesn't give the `--config` form or say anything about downtime.

So I'd save this as a short new entry, filed under your existing **`deployment - caddy`** type (`reclMCYETdgQJ6oBZrv`). It's the most specific type you have, and it currently holds one entry, "Caddy - Cache issues". No new type is needed.

**Proposed entry**
- **Title:** Caddy - Reload config without downtime
- **Type:** deployment - caddy
- **Related (linked both ways):** Caddy Server - Config Examples & Static File Serving (`recFfUwBOXZH65aBe02`), Caddy - Cache issues (`recIOMDhfaSCkEAghOj`)
- **Body:**

  > Reload Caddy's configuration in place, without stopping the server or dropping connections.
  >
  > ## When to use
  > - After editing `/etc/caddy/Caddyfile` and you want the change live with no downtime.
  >
  > ## Steps
  > 1. Reload the config:
  >    ```bash
  >    caddy reload --config /etc/caddy/Caddyfile
  >    ```
  >
  > ## Caveats
  > - If the new config is invalid, the reload fails and Caddy keeps running on the old config.
  >
  > ## Sources
  > - Related: Caddy Server - Config Examples & Static File Serving (recFfUwBOXZH65aBe02)

One thing to flag: I couldn't run the preview (dry run) of the save, because my permission settings blocked the command. That means the duplicate and secret checks haven't run yet. I don't expect them to find anything, since no entry has this title and the body has no secrets. I'll run the preview again just before saving.

**Shall I save it like this?** Or would you prefer:
1. a different type, such as `deployment - web server`, where the config-examples entry lives, or
2. no new entry, just a dated update added to "Caddy Server - Config Examples & Static File Serving"?
