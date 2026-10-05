---
name: finance-management
description: Answer questions about the user's money and keep their finance records tidy, from the cybernetics-data finance tables (finance_Transactions, Accounts, Categories, Payees, Tags, Budgets) through the Teable REST API. Use whenever the user or an agent asks what they spent or earned ("how much did I spend last month?", "food cost over 6 months", "what do I pay Allianz a year?"), wants monthly, 3-month, 6-month or yearly cost totals, a breakdown by category, payee or tag, a search for transactions, trends or comparisons, subscriptions, budgets, unusual or duplicate charges, account balance, financial-year or tax totals, or wants to add, categorise or tag transactions or set budgets - even if they never say "finance". Not for CRM deals, opportunities or invoices to clients, and not for project or knowledge records.
---

# Finance Management (cybernetics-data)

The finance tables are the single source of truth; this skill keeps no state. Everything goes through one CLI, run from the repo root so `.env` is found:

```bash
python3 .claude/skills/finance-management/scripts/fin.py <command> ...   # add --json for machine output
```

What each figure means: `references/metrics.md`. Workflows: `references/workflows.md`. IDs and verified API behaviours: `references/schema.md`. Python use: `scripts/findata.py` (fetch, periods, writes) and `scripts/fincalc.py` (pure calculations); their docstrings show the calls.

## Pick a mode

- **Agent mode** (you are doing work in a coding session): use `--json`, quote figures exactly, include record ids for writes, no narration, end with one line `changed: ...` (or `changed: nothing`).
- **Human mode** (the user is asking): give the answer first (figure, period, what counts), then any coverage warning, then a short breakdown if useful. Lead with decisions if a write needs approval.

## Commands

| Need | Command |
|---|---|
| totals for a period | `summary [PERIOD]`: income, expenses, refunds, net spend, transfers, net cash flow, savings rate |
| monthly / 3 / 6 / 12-month cost | `cost [--by category] [--avg] [--windows 1,3,6,12]` (+ MTD row) |
| where the money goes | `breakdown [PERIOD] --by category\|payee\|tag\|scope\|account\|weekday [--value cost\|income\|amount]`, `top --by payee\|category\|txn` |
| find transactions | `search [WORDS] [--period P] [--category C] [--payee P] [--tag T] [--type T] [--min N] [--max N]` |
| change over time | `trend [PERIOD] [--by category]`, `compare mom\|yoy\|3m-avg\|qoq` or `--a P --b P` |
| subscriptions, bills, regular transfers | `recurring [--all]`: monthly/4-weekly bills, regular transfers and payments to people, plus annual or irregular bills paid in the last 12 months |
| this month / budgets | `runrate`, `budget [YYYY-MM]`, `budget-suggest [PERIOD]` |
| odd things | `anomalies [PERIOD]`, `duplicates`, `doctor` (data quality, read-only) |
| money position | `balance`, `cashflow [PERIOD]`, `fy [fy2026]` (Australian FY, business scope, tax tags) |
| writes | `add`, `categorize --to C`, `tag` / `untag`, `budget-set`, `payee-default`, `delete`, `undo` |

Periods: `mtd`, `last-month`, `3m` / `6m` / `12m` (complete calendar months), `30d`, `2026-08`, `qtd`, `ytd`, `2025`, `fy`, `fy2026`, `fytd`, `last-fy`, `all`, `2026-01-15..2026-02-14`, `2026-01..2026-03`. `--anchor YYYY-MM` sets which month counts as the last complete one. Filters work on every report: `--category`, `--exclude-category`, `--payee`, `--exclude-payee`, `--account`, `--tag`, `--type`, `--text`, `--scope personal|business`, `--min`, `--max`, `--recurring`, `--uncategorized`, `--include-transfers`.

Every write is a **dry run unless `--yes`**: run it once, show the preview, then re-run with `--yes`. Writes are checked against live options, read back, and leave an undo file (`fin.py undo`). Exit codes: 0 ok, 2 blocked or bad input, 3 not found or ambiguous.

## Core rules

1. **Use the CLI's numbers; never compute money by hand.** Quote the figure as printed with its period and basis. The approved definitions (2026-10-05):
   - D-1: cost = Expense only. Transfers are reported separately, and `--include-transfers` adds them. The `Personal Transfers` expense category *is* cost.
   - D-2: the headline is **net spend** = expenses minus `Refunds`.
   - D-3: `3m` / `6m` / `12m` mean the trailing **complete** calendar months, with MTD separate.
   - D-4: personal vs business comes from **category** Scope, never `Transactions.Scope`.
   - D-5: budget actuals come from category + month.
2. **Read the coverage line.** Every report states its rows and the data range. If a period runs past the last transaction (data is imported from bank statements and can be weeks behind), say the figure is partial and offer `--anchor` or a closed range. Status in `recurring` is judged against the last transaction, not today.
3. **Balances run only to the last imported transaction.** `balance` shows the balance at that date, so tell the user to check their bank for today's figure. A Transfer is money out unless it has a Transfer Account. Inbound transfers from an account that isn't set up ("TRANSFER .. FROM <acct>") are counted as money in by the CLI but as money out by the Teable `Current Balance` formula. Doctor group K finds them: the fix is to add the other account (inactive if it isn't tracked) and link both directions (done for 807590005 on 2026-10-06; the balance field now reads $979.54).
4. **Never guess a name or id.** Ambiguous or unknown names exit 3 with candidates; ask the user to pick.
5. **Dates are Australia/Melbourne.** The CLI handles the conversion; never slice ISO strings yourself, and never write dates except through the CLI. Plain `YYYY-MM-DD` writes are stored wrongly on DST-change days.
6. **Bulk writes need a selector and a preview.** `categorize` and `tag` refuse to run without `--ids` or a filter, and cap at 500 rows. Show the count and sample before `--yes`.
7. **Privacy.** Financial figures, payee names and account numbers stay in the conversation. Never paste them into commits, task logs, knowledge entries or other tools unless the user asks; log commands and row counts instead.
8. **Not tax advice.** `fy` summarises what is recorded.
9. **No token** (`CYBERNETICS_DATA_API_TOKEN` missing): the CLI exits with a message. Fall back to MCP `mcp__cyb-data__query_records` (no server filter; filter and sum client-side, and say the figures were computed without the CLI).

## Autonomy ceiling (agents, D-6)

| Action | Alone | Confirm with the user |
|---|---|---|
| every report, search, `doctor` | yes | |
| `categorize` one row by id | yes, report the id and undo file | |
| `add`, bulk `categorize`, `tag` / `untag`, `budget-set`, `payee-default` | | after showing the dry run |
| `delete`, data clean-up (D-8), anything over 50 rows | | always, per group |

## With other skills

- **project-management** owns goals, projects and tasks; it does not handle money. Link finance work to a project there, and keep figures out of task logs.
- **knowledge-management** stores how-tos (e.g. how statements are imported); this skill never writes knowledge entries.
- **cybernetics-workspace** (CRM) owns client deals and invoices. `Client Payments` here are only the bank-side record.

## Status

Built in project "Finance Management Skill" (cybernetics-data `recjVfyrbspJxTjpfMl`). Tests: `evals/test_calc.py` (offline), `evals/run_flow.py` (live, isolated `[TEST]` rows, cleaned up). Statement import is out of scope for v1 (D-7).
