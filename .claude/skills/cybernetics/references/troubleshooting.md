# Troubleshooting

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | success | — |
| 1 | general error | read the message; usually a missing or malformed flag |
| 2 | refused by the safety gate | confirm with the user, then add `--yes` |
| 3 | not found / unresolvable | the hint lists valid values — use one of them |
| 4 | auth failure | token missing, rejected (401) or forbidden (403); run `cyb doctor` |
| 5 | rate limited | 60 req/min exhausted; the client already waits out the reset window once — repeated hits mean the access pattern itself is wrong |

Under `--json`, every error (any exit code) arrives on stderr as
`{"error":{"code","message","hint"}}` — stdout is never used for errors, even
when the command that failed would normally print to stdout on success.

## "no API token configured" (exit 4)

Precedence is the `CYB_TOKEN` env var, then `~/.cybernetics/config.json`
(`token` field), then a gitignored `.env` in the working directory. Set one:

```bash
export CYB_TOKEN='<your token>'
cyb doctor
```

To persist it outside the repo:

```bash
cyb init      # writes ~/.cybernetics/config.json at mode 0600
```

Never commit a token. This repository is public. The CLI never prints a full
token — only a truncated fingerprint.

## "no such state" / "no such label" / "no such member" / "no such project" (exit 3)

The hint lists valid values and, when close enough, suggests the nearest
match. Names are matched case-insensitively. If the value was created moments
ago in the web UI, the local cache may be stale (15-minute TTL per resource
region):

```bash
cyb sync            # rebuilds projects, states and members from scratch
cyb <group> <action> ... --no-cache   # or bypass the cache for one command
```

An empty project list with "no such project" may mean the workspace genuinely
has none yet:

```bash
cyb project create --name "Cybernetics Core" --identifier CYB
```

Identifiers are capped at 10 characters.

## A stale state or member causes a 400, not a 404

Projects, work items and labels are resolved onto a URL path, so a stale
cached UUID for one of those 404s and the CLI refreshes and retries
automatically, once. States and members are body fields (`--state`,
`--assignee` on `item create`/`update`), not path segments, so a stale one
comes back as a 400 validation error instead — the automatic retry does not
apply. Run `cyb sync` and retry the command by hand.

## Rate limited (exit 5)

The client tracks `x-ratelimit-remaining`/`x-ratelimit-reset` and already
pauses once when the budget runs low, then retries. If you hit exit 5
repeatedly in one session, the access pattern is wrong — you are probably
looping per-resource. Replace the loop with `cyb board`, `cyb my`, or a single
bounded `cyb item list --limit N`, and stop increasing `--limit` to work
around it.

## A command that used to work now 404s

The fork may have changed. Re-probe and compare against
`references/api-surface.md`:

```bash
cyb doctor --probe
```
