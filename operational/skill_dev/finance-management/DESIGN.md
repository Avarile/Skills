# finance-management skill: design (draft for approval, 2026-10-05)

Modelled on `knowledge-management`: stateless, one CLI over the Teable REST API, dry-run writes, read-back, and a report-only doctor. It also adds an importable Python function layer, so other scripts and agents can call the calculations directly.

## 1. What is there today (live probe, 2026-10-05, read-only)

| Table | ID | Rows | Notes |
|---|---|---|---|
| finance_Transactions | `tblylfLkXFkYH2qB0ZQ` | 1102 | 2025-10-30 .. 2026-09-18; Expense 979, Transfer 72, Income 51 |
| finance_Accounts | `tblJLklwpGwbrfDlwIz` | 1 | ANZ Access Advantage (Checking, Personal) |
| finance_Categories | `tblp2Jvb2g90PN3fX4d` | 24 | 19 Expense, 5 Income; flat (no Parent Category used); 3 Business-scoped |
| finance_Payees | `tblpyC3PfoG0DN8dQ2t` | 127 | Default Category mostly empty |
| finance_Tags | `tblhOQKXpSzr0Ezh8rR` | 3 | Recurring / Subscription, Tax Deductible, Reimbursable; **0 tagged transactions** |
| finance_Budgets | `tblDk3iXFz5YiYUkwz6` | 0 | Actual Spent is a rollup over *linked* transactions; no transaction has a Budget link |

Relationships: Transaction -> Account, Transfer Account, Category, Payee, Budget (many-to-one), Tags (many-to-many). Category -> Parent Category (self). Payee -> Default Category. Budget -> Category (month + planned amount).

Facts that shape the design:

- `Amount` is always positive. `Signed Amount` (formula) is -Expense, -Transfer, +Income.
- `Transactions.Scope` is a lookup from the Account, so it is **Personal on every row**. The real personal/business split lives on `Categories.Scope` (Personal, Business, Shared).
- All 72 Transfers have no Category, no Payee and no Transfer Account. They total 173k, mostly outgoing to two destinations ("TO WANG JUNYANG", "TRANSFER ... TO 01366473355").
- Dates are mixed: 1072 rows stored at `T00:00Z` and 30 at `T14:00Z` (Melbourne midnight). Converting to Australia/Melbourne gives the right local date for both. Month boundaries depend on getting this right.
- The account's Current Balance is **-49,140**: income into this account is missing, or the money comes from accounts that aren't tracked. Balance features must say this.
- Data ends 2026-09-18, 17 days before today. Every report needs to show the data coverage.
- 8 possible duplicate groups (same date, amount and description). 2 Income rows use Expense categories (Vehicle & Rego, Personal Transfers).
- 71 rows are flagged Recurring (all Monthly). The main ones are Allianz, NestJS, Amaysim, Retell AI, Clink, ahm, Twinkl, Dodo, Amazon Prime and Lumo.

Verified API behaviours:
- The server-side `filter` works: date `isOnOrAfter`/`isBefore` with a Melbourne `exactDate`, `isWithIn pastNumberOfDays`, and link `isAnyOf`. One month of expenses comes back in 0.2 s.
- `GET /api/table/<id>/aggregation?field[sum][]=<fieldId>&filter=...` returns server-side sums. It matched the client-side sum for 2026-08 expenses exactly (6,696.11), so the acceptance test uses it as an independent cross-check.
- `groupBy` works on the record endpoint (group counts only, not sums).
- The generated docs' plain `search=` is wrong (from the KM project), so the skill uses `filter` + `contains`.
- Python's default user agent gets HTTP 403; `teable.py` already handles this.

## 2. Scope

**In:** fast filtered reads; cost and income calculations over standard periods; categorised search; breakdowns, trends and comparisons; recurring and subscription analysis; budgets vs actuals; anomaly and duplicate detection; balance and cash-flow; an Australian FY and tax view; safe writes (add, categorise, tag, budget, payee default); a report-only doctor; `--json` for agents.

**Out (v1):** bank statement import and parsing (proposed for a later project), multi-currency, charts and dashboards (they can come later through an artifact), schema changes, investment and mortgage valuation, and editing the synced `cybernetics-workspace` skill.

## 3. Layout

```
skill_dev/finance-management/
  SKILL.md                 verbs, routing, core rules, autonomy ceiling (< ~150 lines)
  README.md                install / rsync, examples
  references/schema.md     table + field IDs, enums, verified behaviours
  references/metrics.md    exact definitions: cost, net spend, savings rate, run-rate, period rules
  references/workflows.md  step-by-step for each verb
  scripts/teable.py        identical copy of the project-management helper (diffed by run_flow)
  scripts/findata.py       IO layer: periods, filtered fetch, lookups, normalisation, writes
  scripts/fincalc.py       pure functions over normalised rows (no IO, unit-testable offline)
  scripts/fin.py           the CLI (thin wrapper over findata + fincalc)
  scripts/doctor.py        read-only data-quality report
  evals/run_flow.py        live acceptance test ([TEST] rows, cleaned up, totals cross-checked)
  evals/test_calc.py       offline unit tests for fincalc on fixture rows
  evals/evals.json         behavioural prompts with assertions
```

## 4. Function design

### 4.1 Data layer (`findata.py`)

| Function | Purpose |
|---|---|
| `Txn` (dataclass) | id, date (Melbourne local), type, amount, signed, description, notes, account, category, category_scope, payee, tags, budget, recurring, frequency |
| `resolve_period(spec, today=None)` -> `(start, end, label)` | `month[:YYYY-MM]`, `last-month`, `mtd`, `3m`/`6m`/`12m` (trailing complete months), `last-N-days`, `qtd`, `ytd`, `year:YYYY`, `fy[:YYYY]` (AU Jul-Jun), `fytd`, `YYYY-MM-DD..YYYY-MM-DD` |
| `load_txns(period, *, types, categories, payees, accounts, tags, scope, text, min_amount, max_amount, recurring)` | one server-side filtered query, paged, normalised to `Txn` |
| `lookups()` | categories, payees, accounts, tags, budgets as id <-> name maps (one call each, cached per run) |
| `resolve(kind, ref)` | name / partial / id -> record; ambiguous or missing exits with candidates (never guesses) |
| `coverage()` | first/last transaction date per account (shown on every report) |
| `server_sum(filter)` | aggregation endpoint (used as a cross-check) |

### 4.2 Calculations (`fincalc.py`, pure)

| Group | Functions |
|---|---|
| Totals | `summarize(txns)` -> income, expense, refunds, net spend, transfers out/in, net cash flow, savings rate, count |
| **Cost windows** | `cost(txns, period)` -> total, monthly avg, daily avg; `cost_windows(anchor, windows=(1,3,6,12))` -> one table with the **monthly, 3-month, 6-month and 1-year** totals plus a monthly average for each |
| Breakdowns | `by_category(txns, level="leaf"\|"parent")`, `by_payee`, `by_tag`, `by_account`, `by_scope` (from category scope), `by_weekday`, each with amount, count, share % and avg ticket |
| Trend | `monthly_series(txns, group_by=None)` (month x group matrix, zero-filled), `rolling_avg(series, n)` |
| Compare | `compare(period_a, period_b, group_by)` -> abs/% delta per group; presets: MoM, vs same month last year, vs trailing-3m avg |
| Top | `top(txns, by="payee"\|"category"\|"txn", n=10)` |
| Search | `search(query, period, ...)` -> matching txns + totals + category/payee split ("how much at Woolworths in 6m", "all Uber rides this FY") |
| Run-rate | `run_rate(period=mtd)` -> spent so far, daily burn, projected month end vs trailing-3m avg / budget |
| Recurring | `recurring(txns)` -> flagged + inferred (same payee, regular interval, stable amount), monthly-equivalent and annualised cost, price changes, missed/late, new in the last 90d |
| Budgets | `budget_vs_actual(month)` (actuals computed by category+month, **not** via the Budget link), `budget_suggest(months=6, method="median"\|"avg"\|"p75")` |
| Anomalies | `anomalies(txns)` -> amount > k x category median; `duplicates(txns)` same date+amount+payee/description |
| Balance | `balance_series(account)` from Opening Balance + signed amounts; `cash_flow(period)` (warns when the result contradicts reality, e.g. negative checking balance) |
| Tax / FY | `fy_report(fy)` -> Business-scope categories, income vs expense, `Tax Deductible`/`Reimbursable` tag totals |

### 4.3 Writes (`findata.py`, all dry-run unless `--yes`, validated, read back)

| Function | Rule |
|---|---|
| `add_txn(...)` | payee -> its Default Category if none given; select values checked against live options (a bad value silently clears a field); duplicate check |
| `categorize(ids \| rule, category)` | single or rule-based (payee / description contains); preview count; previous values saved to an undo file |
| `tag / untag(ids \| rule, tag)` | adds to the tag array, never replaces it |
| `budget_set(month, category, amount)` | upsert one Budget row per category per month |
| `payee_default(payee, category)` | sets the Default Category so later adds and imports categorise automatically |
| `undo(file)` | restores the previous values from an undo file |

### 4.4 CLI (`fin.py`, human text by default, `--json` / `--csv`)

`summary [period]` · `cost [--windows 1,3,6,12] [--by category]` · `breakdown --by category|payee|tag|scope|account [period]` · `trend [--months 12] [--by category]` · `compare a b` · `top` · `search <terms> [--category --payee --tag --type --min --max] [period]` · `runrate` · `recurring` · `budget [month]` / `budget-suggest` / `budget-set` · `anomalies` · `balance` · `fy [YYYY]` · `doctor` · writes: `add`, `categorize`, `tag`, `untag`, `payee-default`, `undo`.

Every report starts with a single line giving the period, the number of rows it uses, and the data coverage (for example "data to 2026-09-18, 17 days old").

### 4.5 Doctor (read-only)

Uncategorised non-transfers · income/expense category mismatch · possible duplicates · payees without a Default Category · transfers with no destination · stale data (last txn > 7 days) · negative balance / missing income · inconsistent date storage · recurring flags vs inferred subscriptions · unused tags/budgets · flat category tree. Each finding comes with a fix command.

## 5. Decisions needed (gate Step 02)

1. **What counts as "cost"?** Proposal: Expense type only. Transfers are reported on a separate line and excluded unless `--include-transfers`. The "Personal Transfers" expense category stays in cost.
2. **Refunds:** report gross expense, plus "net spend" = expense minus the `Refunds` income category. Proposal: the headline figure is net spend.
3. **Period meaning:** proposal: "3 months" = the last 3 *complete* calendar months, with month-to-date shown separately. The alternative is rolling 90 days to today.
4. **Personal vs business:** take it from `Categories.Scope` (Shared counts in both views), because `Transactions.Scope` is always Personal.
5. **Budgets:** compute actuals by category+month in code, ignoring the empty Budget link. Proposal: no link syncing in v1.
6. **Write autonomy for agents:** reads, doctor and single-row categorise can run alone; add, bulk categorise, tag, budget-set and payee-default need confirmation.
7. **Statement import:** out of scope for v1 (a follow-up project)?
8. **Data clean-up (Step 14):** fix duplicates, the 2 mismatched categories and the payee defaults, only per group with your OK?

## 6. Risks

| Risk | L | I | Mitigation |
|---|---|---|---|
| Wrong totals from semantics (transfers, refunds, double counting) | M | H | `metrics.md` defines every figure; run_flow cross-checks against the server aggregation endpoint |
| Off-by-one at month boundaries (mixed UTC/Melbourne date storage) | M | H | normalise to Melbourne local date; boundary fixtures in `test_calc.py` |
| Incomplete data (one account, negative balance, data 17 days old) gives misleading answers | H | M | coverage line on every report; balance features warn; doctor flags it |
| A bad select value silently clears a field on write | M | M | validate against live options; read back after every write |
| Bulk recategorisation mistakes | L | H | dry-run, count, confirm, undo file |
| `teable.py` drifts between skills | M | L | identical copy; run_flow diffs it |
| Financial data leaves the machine (figures in commits, logs, other tools) | L | H | rule in SKILL.md; no figures in task logs, only command + row counts |
