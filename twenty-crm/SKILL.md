---
name: twenty-crm
description: Use when adding, editing, looking up, or bulk-importing Person records in the self-hosted Twenty CRM at crm.avarile.com -- covers create/update/get/delete for a single Person, batch create/upsert, and find-by-email/find-by-name lookups.
---

# Twenty CRM

## Overview
A zero-dependency Python client and CLI over the `/rest/people` and
`/rest/batch/people` REST endpoints of the self-hosted Twenty CRM instance at
`crm.avarile.com`. Twenty stores several Person fields as nested objects
(`name`, `emails`, `phones`, `linkedinLink`, `xLink`) — this skill turns that
into flat keyword arguments and a CLI, so callers never hand-assemble the
nested shape.

## When to Use
- Asked to add, update, look up, delete, or bulk-import Person/contact
  records in this CRM
- Building an agent workflow that needs programmatic access to Person data

## Setup
Needs an API token, checked in this order from the environment then from
`twenty-crm/.env`: `TWENTY_CRM_APITOKEN`, `TWENTY_CRM_API_TOKEN`,
`TWENTY_API_KEY`, `CRM_API_TOKEN`, `API_TOKEN`. Base URL is checked the same
way (`TWENTY_CRM_URL`, `TWENTY_CRM_BASE_URL`, `CRM_URL`, `TWENTY_BASE_URL`)
and otherwise defaults to `https://crm.avarile.com`. `parse_dotenv` accepts
both `KEY=value` and `KEY: value` lines.

**The `.env` file is not checked in** (this repo's `.gitignore` ignores every
`.env` anywhere, and the harness that authored this skill is itself blocked
from writing one). Create it yourself:
```
twenty-crm/.env
TWENTY_CRM_APITOKEN=<your API token>
TWENTY_CRM_URL=https://crm.avarile.com
```
Or export `TWENTY_CRM_APITOKEN` in your shell instead — either source works.

If requests fail with `403 Forbidden` from a script but work fine from
`curl`, that's a WAF blocking Python's default `Python-urllib/x.y` User-Agent
— `client.py` already sends a browser-like one, verified against the live
instance. If requests fail with `CERTIFICATE_VERIFY_FAILED`, that's a local
Python/OpenSSL cert-bundle gap (common on Homebrew Python installs on
macOS) — `client.py` falls back to the system CA bundle (`/etc/ssl/cert.pem`)
automatically.

## Quick Reference (CLI)
Run from the repo root. Every subcommand prints one JSON document to stdout;
on failure, a plain-text message goes to stderr and the exit code is 1.

| Command | Purpose |
|---|---|
| `create --first-name X --last-name Y [--email ...] [--job-title ...] [--city ...] [--company-id ...] [--phone-number ...]` | create one person |
| `update PERSON_ID [--first-name ...] [--email ...] ...` | partial update — only passed fields change |
| `get PERSON_ID` | fetch one person |
| `delete PERSON_ID` | delete one person |
| `find-by-email EMAIL` | exact-match lookup, returns one person or `null` |
| `find-by-name [--first-name ...] [--last-name ...]` | lookup by name, returns a list |
| `list` | every person, paginates automatically |

```bash
python3 twenty-crm/src/cli.py create --first-name Ada --last-name Lovelace --email ada@example.com --job-title CTO
python3 twenty-crm/src/cli.py update 0652727c-4c92-4811-9acb-29d4983acd20 --city Sydney
python3 twenty-crm/src/cli.py find-by-email ada@example.com
```

## Implementation
- `src/client.py` — HTTP client (stdlib `urllib` only), `.env` loader,
  cursor pagination via `iter_people`. Also exposes `create_person`,
  `update_person`, `delete_person`, `batch_create_people` for direct
  low-level (raw nested-shape) access if a task needs it.
- `src/people.py` — flat-argument helpers built on `client.py`:
  `create_person`, `update_person`, `get_person`, `delete_person`,
  `batch_create_people`, `find_person_by_email`, `find_people_by_name`,
  `list_all_people`. Importable directly instead of via the CLI:
  `from people import create_person`.
- `src/cli.py` — argparse dispatcher for the table above.

`people.py`'s `build_person_fields` only includes keys for arguments you
actually pass, so the same function backs both `create_person` (full record)
and `update_person` (partial patch) without a separate code path.

## Common Mistakes
- Passing a full name string instead of `--first-name`/`--last-name`
  separately: Twenty's `name` field is `{firstName, lastName}`, not a single
  string.
- Expecting `find-by-email`/`find-by-name` to fuzzy-match: both use Twenty's
  `[eq]` filter operator, so matches must be exact (case-sensitive).
- Combining multiple `find-by-name` clauses expecting OR semantics: Twenty's
  comma-separated filter clauses are AND'd together (verified against the
  live instance), so `--first-name Ada --last-name Turing` together matches
  nobody unless one person has both names.
- Re-running `batch-create` without `upsert=True` (the `people.py` default):
  Twenty's batch endpoint without `upsert` creates duplicates rather than
  matching existing records by email.

## Testing
```bash
python3 -m unittest discover -s twenty-crm/tests -v
```
All HTTP calls are mocked — no network access or real API token required.
