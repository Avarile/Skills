# Metrics: what every figure means

Code: `scripts/fincalc.py`. Decisions D-1..D-4 (approved 2026-10-05). `Amount` is always positive; the sign comes from `Type`.

## Row roles

| Row | Rule | Counts as |
|---|---|---|
| Expense | `Type = Expense` | cost (+Amount) |
| Refund | `Type = Income` and category `Refunds` | negative cost (-Amount), not income |
| Income | `Type = Income`, any other category | income |
| Incoming transfer | `Type = Transfer`, no `Transfer Account`, description says `FROM` (not `TO`), e.g. `TRANSFER 509564 FROM 807590005` | transfers in: money in, never cost or income |
| External transfer | `Type = Transfer`, no `Transfer Account`, not incoming | transfers out; cost only with `--include-transfers` |
| Internal transfer | `Type = Transfer` with a `Transfer Account` | never cost or income (money moves between tracked accounts) |

The data model has no inbound type: the `Signed Amount` formula, and with it the account's `Current Balance`, treats every Transfer row as money out of its Account, and as money in for its Transfer Account. An inbound transfer from an unlinked account therefore reads as an outflow. fincalc detects these rows from the description and counts them as money in. Since 2026-10-06 the 48 transfers to and from account 807590005 are linked to an inactive account "ANZ (013148-807590005)", so they are internal: own-account moves, neither cost nor cash flow. The 24 transfers that are still unlinked (e.g. `TO WANG JUNYANG`, `TO 013664733557893`) count as transfers out. Transfers are not cost by default. The `Personal Transfers` **expense category** (money sent to people, booked as Expense) *is* cost (D-1).

## Figures

| Figure | Definition |
|---|---|
| expense | sum Amount of Expense rows |
| refunds | sum Amount of Refund rows |
| **net spend (cost)** | expense - refunds (+ external transfers with `--include-transfers`). The headline (D-2) |
| income | sum Amount of Income rows that are not refunds |
| transfers out | sum Amount of external outgoing transfers |
| transfers in | sum Amount of incoming transfers |
| net cash flow | income + refunds + transfers in - expense - transfers out |
| balance | opening + own rows (signed) + transfers in where Transfer Account = this account, **with incoming transfers counted as money in** (the Teable formula counts them as out; `balance` shows both) |
| recurring | groups of Expense rows (and outgoing transfers) by payee or destination with a regular gap (weekly, fortnightly, 4-weekly, monthly, quarterly, yearly) and a stable amount, or rows flagged Recurring. Monthly equivalent = typical x 30.4375 / cadence days. Bills and payments to people (Personal Transfers) or transfer rows are listed separately |
| irregular bills | Expense rows in bill-like categories (Utilities, Insurance, Council & Government, Vehicle & Rego, Subscriptions & Software, Education & Childcare, Rent & Housing, Health & Wellness) in the last 12 months that are not part of a recurring item: the amount actually paid |
| savings rate | (income - net spend) / income x 100; blank when income is 0. Transfers out are not treated as spending, because they may be savings |
| per month | net spend / months in the period (whole months when month-aligned, else days / 30.4375) |
| per day | net spend / days in the period |
| share % | group net spend / period net spend |

## Periods (D-3)

- `last-month` (`month`, `1m`), `3m`, `6m`, `12m` (`year`) are **trailing complete calendar months**, ending with the month before today's month. `--anchor YYYY-MM` sets that last complete month (use it when the data is behind).
- Month-to-date (`mtd`) is always a separate row, never mixed into a window.
- `fy2026` is the Australian financial year 2025-07-01..2026-06-30; `fy` is the current one, `fytd` is to date, and `last-fy` is the previous one.
- All dates are Australia/Melbourne local dates. A period is [start, end), and the end date shown is the last day included.

## Scope (D-4)

Personal or business comes from `Categories.Scope`. `Shared` categories count in both views. Rows without a category fall back to the account's scope. `Transactions.Scope` is not used, because it is the account's scope and reads Personal on every row.

## Coverage

Every report shows its row count and the data range (first..last transaction, and how old the data is). A period that starts before the first transaction or ends after the last one gets a warning, because its totals and averages are understated. Read "per month" for such windows with care, or use `--anchor`.

## Cross-check

For any period, `findata.server_sum(p, types=["Expense"]) - findata.server_sum(p, types=["Income"], categories=["Refunds"])` must equal `cost(...)["net_spend"]` to the cent (`evals/run_flow.py`).
