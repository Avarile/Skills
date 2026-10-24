# finance-management

A skill for the `finance_*` tables of the **cybernetics-data** Teable database. It lets an AI agent (Claude Code or similar) or you answer money questions, such as "what did I spend on food in 6 months?", "what are my subscriptions?" and "business income this FY?". The answers come from the database rather than guesswork, and the skill keeps the records tidy with careful writes.

- **Cost over standard windows.** Last month, 3, 6 and 12 complete months, plus month-to-date, in one table, by category if wanted. The figures match the server's own aggregation to the cent (checked by the acceptance test).
- **Categorized search.** Words (description, notes, payee) plus category, payee, tag, type, amount and period filters, with totals, the category and payee split, and the matching rows. A text search takes 2 HTTP calls.
- **Analysis.** Breakdowns, top payees and purchases, trends, comparisons (MoM, YoY, vs 3-month average), recurring payments with price changes, run-rate, budgets vs actuals and suggestions, anomalies, duplicates, cash flow, balance, and the Australian financial year.
- **Careful writes.** Add, categorize, tag, budget-set and payee-default. Each one is a dry run first and is checked against the live select options (a wrong option would silently clear the field). Every write is read back and leaves an undo file.
- **Doctor.** A read-only data-quality report (stale data, mismatched categories, duplicates, payee defaults, transfers, balances, recurring flags, unused records). Each finding comes with a fix command.

## Requirements

- Python 3.9 or newer (standard library only).
- `CYBERNETICS_DATA_API_TOKEN` in the environment or in a `.env` file in the working directory or a parent. Optional `CYBERNETICS_DATA_URL` (default `https://cybernetics.avarile.com`).
- The `cyb-data` MCP server is only needed as a fallback when the token is missing.

## Install

Source: `skill_dev/finance-management/`. Installed copy for Claude Code: `.claude/skills/finance-management/` (a copy, not a link). Re-sync after any change:

```bash
rsync -a --delete --exclude '__pycache__' --exclude 'DESIGN.md' skill_dev/finance-management/ .claude/skills/finance-management/
```

## Use

Ask in plain language ("how much did I spend last month?", "show my subscriptions", "tag the Cloudflare charges as tax deductible") and the skill picks the command. Directly:

```bash
fin=".claude/skills/finance-management/scripts/fin.py"
python3 $fin cost                                  # 1/3/6/12 complete months + MTD
python3 $fin cost --by category --avg --anchor 2026-08
python3 $fin summary fy2026 --scope business
python3 $fin search woolworths --period 6m
python3 $fin search --category Insurance --min 100
python3 $fin breakdown 3m --by payee --top 10
python3 $fin trend --by category
python3 $fin compare yoy --by category
python3 $fin recurring --all
python3 $fin budget-suggest 6m
python3 $fin anomalies
python3 $fin doctor
python3 $fin categorize --to Food --payee Woolworths --uncategorized     # dry run
python3 $fin budget-set 2026-10 --category Food --amount 900 --yes
python3 $fin undo                                  # dry run of the latest undo
```

`--json` on any command gives machine output. Exit codes: 0 ok, 2 blocked or bad input, 3 not found or ambiguous.

As a library:

```python
import sys; sys.path.insert(0, ".claude/skills/finance-management/scripts")
import findata as D, fincalc as C
p = D.resolve_period("6m")
rows = D.load_txns(p, categories=["Food"])
C.cost(rows, p)                       # {'net_spend': ..., 'monthly_avg': ..., ...}
C.breakdown(rows, "payee")[:5]
```

## Decisions baked in (approved 2026-10-05)

- Cost is Expense rows minus Refunds. Transfers are separate (`--include-transfers` adds them).
- `3m` / `6m` / `12m` are complete calendar months, with month-to-date on its own row.
- Personal vs business comes from the category's Scope.
- Budget actuals come from category + month.
- Agents may read anything and categorize one row on their own. Every other write needs the user's OK after the dry run.
- Statement import is not part of v1.

## Things to know

- **Dates:** the server compares date filters as instants, and `Date` holds both UTC-midnight imports and Melbourne-midnight UI entries. The skill sends Melbourne midnight (DST-aware) for both filters and writes. A plain `YYYY-MM-DD` write on a DST-change day is stored as the previous day.
- **Row limit:** `teable.get_records`' default `take=1000` caps the total, not the page size. findata always reads with `take=ALL`.
- **Data gaps:** the data is imported from bank statements, so it can be weeks behind. Every report prints the data range and warns when a period runs past it (`--anchor` helps).
- **Balance:** a Transfer row is money out of its Account and money in to its Transfer Account. Inbound transfers from an account that isn't set up ("TRANSFER .. FROM ..") were stored as plain Transfers and read as outflows (about -$49k). The 807590005 account was added and linked on 2026-10-06; the balance is now $979.54 at the last transaction. `balance` and doctor group K catch any new cases.
- **`teable.py`:** a copy of the project-management helper; `evals/run_flow.py` checks they stay identical.

## Tests

```bash
python3 skill_dev/finance-management/evals/test_calc.py   # offline, fixture rows
python3 skill_dev/finance-management/evals/run_flow.py    # live: reads cross-checked with the server; writes on an
                                                          # inactive [TEST] account, all removed, row counts restored
```

## Layout

```
finance-management/
  SKILL.md               entry point loaded by the agent
  README.md              this file
  DESIGN.md              design as approved (not installed)
  references/            schema, metrics, workflows
  scripts/fin.py         the CLI
  scripts/findata.py     periods, filtered fetch, lookups, name resolution, coverage, writes + undo
  scripts/fincalc.py     pure calculations (cost, breakdowns, search, trend, compare, recurring, budgets, ...)
  scripts/doctor.py      read-only data-quality report
  scripts/teable.py      shared REST helper (copied from project-management)
  evals/test_calc.py     offline unit tests
  evals/run_flow.py      live acceptance test
  evals/evals.json       behavioural prompts with assertions
```
