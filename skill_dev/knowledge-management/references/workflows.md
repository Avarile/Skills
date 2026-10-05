# Workflows

`kb.py` = `python3 .claude/skills/knowledge-management/scripts/kb.py` (or `skill_dev/...` while developing). IDs and API facts: `schema.md`.

## find (answer a question from the knowledge base)
1. `kb.py find <2-3 distinctive words>`. Aliases are on (k8s finds k3s/kubernetes). Too many hits: add a word or `--type <domain>`. None: `--any`, other words, or `kb.py types` to browse.
2. Pick the best 1-2 results by title, type and snippet. `kb.py get <id>`; if the entry is long (`find` shows its size), `get <id> --toc`, then `--section "<heading>"`.
3. Answer from the entry text, quote commands exactly, and name the entry (title + id). If the entry looks outdated or contradicts itself, say so.
4. Not found after 2-3 tries: say so plainly and offer to capture the answer once it is known.

## get a secret
The user asked for a specific credential: `kb.py find <service> --type credential` (aliases cover password/api key), `get <id>` or `type <name>` for the type-level `credentials` value. Show only what was asked. Never paste it into other records, files, commits or messages.

## capture (save new knowledge)
1. Draft the entry with `entry-format.md`: title `<Subject> - <Aspect>`, one-line summary, `## When to use`, `## Steps` or `## Reference`, `## Caveats`, `## Sources`. Write the body to a temp file.
2. Pick the type with `taxonomy.md` (`kb.py types`). Use an existing one.
3. Dry-run: `kb.py capture --title "..." --type "..." --body-file F [--parent ID] [--related ID ...] [--refer project:ID]`.
4. Read the preview:
   - `BLOCKED: exact title exists` -> `append` to that entry instead (or `--allow-duplicate` only if the user wants a separate entry).
   - `similar:` entries -> check them; if one covers the topic, `append` instead.
   - `no single type matches` -> pick from the candidates, or ask the user before `--new-type`.
   - `secret?:` warnings -> tell the user; suggest a credential type.
5. Human mode: show the preview (title, type, links, warnings) and wait for OK. Agent mode: proceed when nothing above fired.
6. `--yes`. Report title, type and the new id.

## append (add an update)
`kb.py append <id> --text-file F` adds `### YYYY-MM-DD` + text under `## Updates` (creates the section if absent); `--section "## Caveats"` targets another `##` section; `--no-date` skips the date heading. It aborts if the entry changed between preview and write. To correct text in place, edit only that part (read-modify-verify with `get` + MCP `update_record`, then `get` again).

## organise (one entry)
`kb.py link <id> --type "<type>"` (move), `--title "<new>"`, `--parent <hub id>` / `--no-parent` (series), `--related <id ...>` / `--unrelate <id ...>` (both sides). Re-parenting needs the user's OK.

## series hub (doctor group D)
1. Capture a short hub entry (`<Series>`; body: what the series achieves, the ordered list of steps with ids).
2. `kb.py link <step id> --parent <hub id> --yes` for each step (count first, user's OK).
3. `kb.py tree <hub id>` to verify.

## knowledge for work (with project-management)
- **pre-flight (plan):** `kb.py for-work project:<id> [--terms <domain words>]`. Show linked + up to 5 suggestions (title + type). Link only the user's picks: `kb.py refer <ids> --to project:<id> --yes` (or `task:<id>`).
- **during work:** an agent that relied on an entry may `refer` it to its task.
- **trace:** `kb.py trace <id>` lists goals, projects and tasks using an entry (check before archiving or rewriting it).
- **close (lessons):** `kb.py capture --title "Lessons - <project>" --type "project - lessons" --body-file lessons.md --related <plan entries> --refer project:<id>`; the type is created on first use with `--new-type` only after the user agrees.

## archive
`kb.py archive <id>` (preview shows how many work records reference it; links are kept), then `--yes` after the user's OK. `--restore` reverses it. Hard delete only on the user's explicit request, via the Teable UI or MCP `delete_records` (goes to trash).

## taxonomy changes
`kb.py type-set "<domain>" --create`, `kb.py type-set "<child>" --parent-type "<domain>"`, `--title`, `--description`. Each needs the user's OK; for many types, list them all with a count first, then apply one by one with `--yes` and finish with `kb.py types`.

## doctor and clean-up
1. `kb.py doctor` (read-only). Present findings by group with counts: A type tree, B untyped, C wrong type, D series without hub, E temp/empty/untitled, F near-duplicates; G (secrets outside credential types) and H (link coverage) are information.
2. Propose concrete changes per group (which type, which hub title, which entry survives a merge). Get the user's OK per group.
3. Apply with the fix commands shown (`link`, `type-set`, `archive`, `append`, `capture`), each dry-run then `--yes`.
4. Re-run `doctor` and report the before/after counts.

## Merging near-duplicates (group F)
1. `get` both; decide with the user which survives (usually the newer or more complete).
2. `append` the unique parts of the other into the survivor (`--section "## Updates"` or a named section).
3. `trace` the other; `refer` its work links to the survivor.
4. `archive` the other and `link` it `--related` to the survivor so old links still lead somewhere.
