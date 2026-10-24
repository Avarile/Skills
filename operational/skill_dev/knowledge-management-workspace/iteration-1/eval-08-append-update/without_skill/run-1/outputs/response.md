Found it: **Caddy - Cache issues** (knowledges #39, `recIOMDhfaSCkEAghOj`, type "deployment - caddy"). It's the only note on Caddy cache issues. The others that mention Caddy are setup and config guides.

This section goes at the very end of the note. Everything already in it (the Caddyfile cache-header example and the Next.js explanation) stays as it is:

```markdown
## Update 2026-10-05

Clearing Caddy's data directory also fixed the issue:

    /var/lib/caddy/.local/share/caddy
```

I haven't saved it yet. Say "go" and I'll write it. Nothing else in the note changes, only the `context` field.

One thing worth knowing: that directory is Caddy's storage for TLS certificates, ACME account keys, OCSP staples and the autosaved config. It doesn't hold HTTP response cache. When you wipe it, Caddy requests all its certificates again on the next start, so do it sparingly or you can hit Let's Encrypt rate limits. I can add a line saying that to the note too if you want.
