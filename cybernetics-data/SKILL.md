---
name: cybernetics-data
description: Use when analyzing personal finance transactions, budgets, accounts, or payees, or the personal knowledge base, stored in the self-hosted Teable instance at cybernetics.avarile.com — covers spending-by-category, monthly cash flow, budget variance, account balances, recurring transactions, top payees, and knowledge-base search/hierarchy queries.
---

# Cybernetics Data

## Overview
A zero-dependency Python client and CLI over the Teable-backed database at
`cybernetics.avarile.com`: 6 finance tables (Accounts, Budgets, Categories,
Payees, Tags, Transactions) and 2 knowledge-base tables (`knowledges`,
`knowledge_type`). Raw endpoint reference lives in `api-docs/`; this skill
turns that into ready-to-call analysis functions and a CLI.

**Not** the Plane-fork project-management `cybernetics` skill at
`projects.avarile.com` (`.claude/skills/cybernetics`, `cyb` CLI, `CYB_*` env
vars) — same name, unrelated service, unrelated tables.

## When to Use
- Asked to summarize spending, budgets, account balances, or cash flow
- Asked to find recurring transactions, top payees, or search transactions
- Asked to search, list, or map relationships in the personal knowledge base
- Building an agent workflow that needs programmatic access to either dataset

## Setup
Needs an API token, checked in this order from the environment then from
`cybernetics-data/.env`: `CYBERNETICS_DATA_APITOKEN`, `CYBERNETICS_DATA_API_TOKEN`,
`CYBERNETICS_API_TOKEN`, `TEABLE_API_TOKEN`, `TEABLE_TOKEN`, `API_TOKEN`. Base
URL is checked the same way (`CYBERNETICS_DATA_URL`, `CYBERNETICS_DATA_BASE_URL`,
`CYBERNETICS_BASE_URL`, `TEABLE_BASE_URL`) and otherwise defaults to
`https://cybernetics.avarile.com`. `parse_dotenv` accepts both `KEY=value` and
`KEY: value` lines.

If requests fail with `403 ... error code: 1010`, that's Cloudflare's WAF
blocking a non-browser User-Agent, not an auth problem — `client.py` already
sends a browser-like one. If requests fail with `CERTIFICATE_VERIFY_FAILED`,
that's a local Python/OpenSSL cert-bundle gap (common on Homebrew Python
installs on macOS) — `client.py` falls back to the system CA bundle
(`/etc/ssl/cert.pem`) automatically.

## Quick Reference (CLI)
Run from the repo root. Every subcommand prints one JSON document to stdout;
on failure, a plain-text message goes to stderr and the exit code is 1.

| Command | Purpose |
|---|---|
| `finance spending-by-category [--type Expense] [--month YYYY-MM]` | totals by category, largest first |
| `finance monthly-cash-flow` | income/expense/transfers/net per month, net reconciles to account balance |
| `finance top-payees [--n 10] [--type Expense]` | biggest payees by spend |
| `finance recurring` | recurring transactions grouped by frequency |
| `finance search QUERY` | full-text search over transactions |
| `finance account-balances` | balance + net activity per account |
| `finance budget-variance [--month YYYY-MM]` | planned vs. actual per budget line |
| `knowledge search QUERY` | full-text search over knowledge entries |
| `knowledge list-types` | all `knowledge_type` entries |
| `knowledge by-type TITLE` | knowledge entries of one type |
| `knowledge tree` | full knowledge hierarchy as nested JSON |

```bash
python3 cybernetics-data/src/cli.py finance spending-by-category --month 2026-08
python3 cybernetics-data/src/cli.py knowledge tree
```

## Implementation
- `src/client.py` — HTTP client (stdlib `urllib` only), `.env` loader,
  pagination via `iter_records`. Also exposes `create_records`,
  `update_record`, `delete_record` for write access if a task needs it.
- `src/schema.py` — table IDs and field-name reference, sourced from `api-docs/`.
- `src/finance.py`, `src/knowledge.py` — analysis functions, importable
  directly instead of via the CLI: `from finance import spending_by_category`.
- `src/cli.py` — argparse dispatcher for the table above.

Every function fetches with `fieldKeyType=name` and reshapes by field
*name* in Python, deliberately avoiding the API's field-ID requirement for
`filter`/`orderBy` — once the data is in hand there's no need for those IDs.

## Common Mistakes
- Passing a full ISO timestamp to `--month`: use `YYYY-MM` only (matched
  against the first 7 characters of the record's date field).
- Expecting `budget-variance` or `account-balances` to compute anything:
  `Actual Spent`, `Variance`, `% Used`, `Current Balance`, and `Net Activity`
  are Teable rollup/formula fields already computed server-side — this skill
  only fetches and reshapes them.
- Assuming `Transfer`-type transactions net to zero: they only do if the
  counterparty is another tracked Account. This dataset has transfers to
  external account numbers with no Transfer Account link at all, so
  `monthly-cash-flow` counts them as real outflows in `net` (broken out
  separately under `transfers` so you can inspect them) — this is what makes
  `net` reconcile with the account's own Current Balance/Net Activity.

## Testing
```bash
python3 -m unittest discover -s cybernetics-data/tests -v
```
All HTTP calls are mocked — no network access or real API token required.
