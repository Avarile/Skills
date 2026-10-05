# Entry format

Write entries so they can be used cold, months later, by the user or an agent.

## Title

`<Subject> - <Aspect>`, specific and searchable: `MariaDB - Docker Deployment (Master/Slave)`, `Caddy - Cache issues`, `K3S - Create new service`. Put the tool or system first; avoid `temp`, `notes`, dates as the whole title. Series: `<Series> - Step N <what>` (and link each step to a hub entry with `knowledge_parent`).

## Body skeleton (Markdown)

```markdown
One or two sentences: what this is and the situation it is for.

## When to use
- the trigger or symptom; environment / versions it was verified on

## Steps            (how-to, deployment)    or  ## Reference (cheatsheet, config)
1. ...
   ```bash
   command
   ```

## Caveats
- what breaks, what to check first, known gotchas

## Sources
- links, repo paths, related entries

## Updates
### 2026-10-05
- dated additions go here (kb.py append)
```

Headings matter: `kb.py get --toc` / `--section` rely on them for long entries.

## Kinds and their main section

| Kind | Main section | Typical type |
|---|---|---|
| how-to / runbook | `## Steps` | `deployment - *`, `database - *` |
| cheatsheet | `## Reference` grouped by task | `* - operation`, `Linux - Commands` |
| config / compose file | `## Reference` with the file, then `## Caveats` | `deployment - docker-compose` |
| troubleshooting | `## Symptom`, `## Cause`, `## Fix` | the system's type |
| decision record | `## Context`, `## Decision`, `## Consequences` | `general - knowledge` or the system's type |
| lessons (project close) | `## Lessons` bullets, `## Estimation` | `project - lessons` (created on first close, with the user's OK) |
| credential | short: what it is for, where it is used; the secret value | `credentials` / `credential_*` |

## Updating

- Add new facts with `kb.py append <id>` (dated `### YYYY-MM-DD` under `## Updates`); do not rewrite the whole body.
- Correcting a specific part is a read-modify-verify edit of that part only.
- Superseded entries: append a pointer to the replacement, link them with `--related`, then archive the old one (with the user's OK).
