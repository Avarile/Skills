# Taxonomy: types, parents, series, related

## What each link means

| Link | Meaning | Use it when | Do not use it for |
|---|---|---|---|
| `knowledge_type` (one per entry) | the kind / domain of the entry | always; every entry gets exactly one type | series or grouping of specific entries |
| `knowledge_type.parent_type` | type tree (`deployment` > `deployment - k8s`) | grouping types of one domain | anything on entries; never write `child_types` |
| `knowledge_parent` | the entry is part of a larger document or series | "Step 2" of a guide, a sub-page of a hub | categorising (that is the type) |
| `related_knowledge` | "see also" between entries, any types | entries a reader of one would want next | parent/child relations; write both sides (`kb.py link --related` does) |
| `refer_knowledge` on goals/projects/tasks | this work used or produced this entry | plan pre-flight and close-out lessons | knowledge-to-knowledge links |

## Type naming

- `<domain> - <topic>`, lower case domain, e.g. `deployment - k8s`, `database - mariadb`, `search engine - qdrant`.
- A parent type is the bare domain (`deployment`, `database`, `search engine`, `credentials`). It may hold entries, but prefer the specific child.
- Credential types: `credentials` as parent, `credential_<kind>` children (`credential_apikey`, `credential_login`, `credential_access_token`, `credential_sshkey`). `kb.py` treats any type matching `credential` or `api key` as a credential type.
- Personal media: `missav_meta` as parent, `missav_meta_<name>` children.
- A type's `context` is a one-line description of what belongs in it (empty everywhere today; `doctor` group A lists them).

## Choosing a type (capture)

1. `kb.py types` and pick the most specific existing type. Partial names resolve if unique (`--type caddy`).
2. If the domain exists but the topic does not (e.g. a first Redis entry under `database`), prefer the domain parent or the closest topic, and say which you chose.
3. Propose a new type only when at least two entries would use it, or the user asks. Creating a type needs the user's OK: `kb.py type-set "<domain> - <topic>" --create [--parent-type <domain>] --yes`.
4. Content that is mainly a secret (password, key, token) goes under a credential type; `capture` warns when the body looks like one.

## Current domain map (2026-10-05, before clean-up)

| Domain | Types (entries) |
|---|---|
| deployment | docker-compose (8), new server (11), k8s (4), web server (3), private registry (1), caddy (1) |
| database | mariadb (3), postgresql (2), clickhouse (1), backup (1), safety (1) |
| search engine | qdrant (3), meilisearch (1) |
| credentials | credentials (8), credential_apikey (3), credential_login (2), credential_access_token (0), credential_sshkey (0), AI Gateway API KEy (0) |
| single-type domains | business, ci-cd, cloud, development tools, family, file transfer, general, Infra, k3s, Linux, process manager, TUI control, version control, TEMP |
| outside naming | AI Gateway API KEy, Career, Python related, WOW |
| personal media | missav_meta and 5 `missav_meta_*` |

`kb.py doctor` recomputes this and proposes parents (group A); Step 13 applies approved changes.

## Search aliases (built into `kb.py find`)

k8s = k3s = kubernetes = microk8s = kubectl · postgres = postgresql · mariadb = mysql · nvim = neovim = lazyvim · docker-compose = "docker compose" · wow = "world of warcraft" = azerothcore · credential = credentials = password = "api key" · ssl = tls = certificate · firewall = ufw = iptables = nftables · raid = mdadm. Add a group in `kb.py` `ALIASES` when a miss is caused by a synonym; keep groups specific (no short ambiguous tokens like `pg`).
