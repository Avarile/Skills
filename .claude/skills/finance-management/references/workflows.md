# Workflows

`fin` = `python3 .claude/skills/finance-management/scripts/fin.py` (or `skill_dev/...` while developing), run from the repo root. Definitions of every figure: `metrics.md`. IDs and API facts: `schema.md`.

## Answer a money question

1. Map the question to one command and a period:

   | Question | Command |
   |---|---|
   | "how much did I spend last month / in August?" | `fin summary last-month` / `fin summary 2026-08` |
   | "monthly, 3-month, 6-month, yearly cost" | `fin cost` (add `--by category --avg` for a per-category table) |
   | "what do I spend on food?" | `fin cost --category Food` or `fin breakdown 6m` |
   | "how much at Woolworths in 6 months?" | `fin search woolworths --period 6m` |
   | "where does my money go?" | `fin breakdown 3m` (`--by payee`, `--by tag`, `--by scope`) |
   | "is spending going up?" | `fin trend` (`--by category`), `fin compare mom` / `yoy` / `3m-avg` |
   | "biggest purchases / payees" | `fin top --by txn`, `fin top --by payee` |
   | "what subscriptions / bills do I have?" | `fin recurring` gives regular bills, regular transfers and payments to people, and annual or irregular bills; `--all` adds stopped ones |
   | "am I on track this month?" | `fin runrate` |
   | "anything odd?" | `fin anomalies`, `fin duplicates` |
   | "business income/expenses this FY", "tax" | `fin fy fy2026`, `fin summary fy2026 --scope business` |
   | "income vs spending by month" | `fin cashflow` |
   | "account balance" | `fin balance` gives the corrected balance at the last transaction, plus the formula figure. Tell the user to check the bank app for today's balance |

2. Read the coverage line first. If it says a period runs past the last transaction, the totals for that period are understated. Say so, and offer `--anchor YYYY-MM` (the last complete month in the data) or a closed range.
3. Answer with the figure, its period and its basis (row count, what counts as cost). Quote amounts exactly as printed. Don't round them again or add up figures from different commands yourself.
4. If a name is ambiguous (exit 3), the CLI lists candidates: pick one with the user, never guess. If a figure looks wrong, cross-check with `search` on the same filters before saying anything is off.

## Categorized search

`fin search <words> [--period P] [--category C] [--payee P] [--tag T] [--type T] [--min N] [--max N] [--account A]`

- Words match the description, notes and payee name (case-insensitive; every word must match).
- The period defaults to all time. The result gives matches by type, net spent, refunds, income, months spanned, the category and payee split, and the newest rows (`--limit`).
- "Excluding X": `--exclude-category X` (uncategorized rows stay).

## Cost windows (the standard report)

`fin cost` prints last month, 3, 6 and 12 complete months, plus month-to-date on its own row. Each row has net spend, per month, per day and refunds.
- `--by category --avg` gives monthly averages per category, side by side, so windows of different lengths can be compared.
- `--include-transfers` adds external transfers to cost (D-1 keeps them out by default).
- `--windows 1,2,3` sets custom windows. `--anchor 2026-08` ends the windows at August when the data is behind.

## Budgets

1. `fin budget-suggest 6m` proposes a monthly amount per category: the median of complete months, rounded up to $10 (`--method avg|p75`).
2. Agree the amounts with the user, then for each one: `fin budget-set 2026-10 --category Food --amount 900` (dry run), then add `--yes`. Running it again for the same month and category updates the row; it never adds a second one.
3. `fin budget 2026-10` shows planned vs actual per category (over, near ≥90%, ok, unbudgeted). `fin runrate` projects the month and gives a daily allowance.
Actuals come from category + month; the Budget link on transactions is not used (D-5).

## Write workflows

Every write is a dry run until `--yes`. The preview shows the rows and values and lists blocks:
- a possible duplicate;
- a category type that doesn't match the row type;
- no selector for a bulk change.

Writes are checked against the live field options and read back after saving. Each one leaves an undo file (`fin undo` restores the latest).

| Task | Steps |
|---|---|
| add a transaction | `fin add --date 2026-10-04 --amount 23.50 --desc "COLES ..." --payee Coles` (the category comes from the payee's default if not given) -> check the preview -> `--yes` |
| categorize | `fin categorize --to Food --payee Woolworths --uncategorized` (or `--ids rec..`) -> check the count and sample -> `--yes` |
| teach a payee | `fin payee-default Coles --category Food --yes`, then categorize its rows as the preview suggests |
| tag for tax | `fin tag "Tax Deductible" --category "Subscriptions & Software" --period fy2026` -> `--yes`; `fin untag ...` reverses it |
| remove a duplicate | `fin duplicates` -> confirm with the user which id to drop -> `fin delete <id>` -> `--yes` (goes to the Teable trash; `fin undo` cannot restore a delete) |
| undo | `fin undo` (latest) or `fin undo <file>`, dry run first |

Autonomy (D-6): agents may run every read, `doctor`, and a single-row `categorize` on their own. `add`, any bulk categorize or tag, `budget-set`, `payee-default` and `delete` need the user's OK after they have seen the dry run.

## Doctor and clean-up (D-8)

1. `fin doctor` (read-only) gives groups A-J with counts, samples and a fix command each.
2. Present the groups and propose concrete changes per group (which payee gets which default, which duplicate id goes).
3. Apply only the groups the user approves, each as dry run then `--yes`, and keep the undo file paths.
4. Re-run `fin doctor` and report the counts before and after.
