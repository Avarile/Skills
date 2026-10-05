# Schema reference (captured 2026-10-05)

Base `bseJEuE54y5caWO0Xc8` ("data-centre"), same base as goals/projects/knowledges. IDs are stable unless the user restructures a table. On "field not found": `GET /api/table/<id>/field`, continue with fresh IDs, and tell the user this file is stale.

## REST API

Base URL `https://cybernetics.avarile.com`, token `CYBERNETICS_DATA_API_TOKEN` (env or `.env`; never print it). `GET /api/table/<tableId>/record` with `fieldKeyType=id`, `take` (<=1000), `skip`, repeated `projection[]=<fieldId>`, JSON `filter`, `orderBy`. `scripts/findata.py` wraps all of it.

### Verified behaviours (2026-10-05, live, read-only)

- **Date filters compare instants, not local days.** `{"mode":"exactDate","exactDate":<ISO>,"timeZone":"Australia/Melbourne"}` with `isOnOrAfter` / `isBefore` (half-open [start, end)) matches by the literal instant, whatever `timeZone` says. With `YYYY-MM-DDT00:00:00.000Z` (UTC midnight) the 30 Melbourne-midnight rows land on the previous day (12/12 missed). Sending **Melbourne midnight as a UTC instant** (`findata.instant`, DST-aware: `2026-08-23T14:00:00.000Z` for local 2026-08-24) matched local dates on all 18 boundary and Melbourne-midnight days tested, and month sums match client-side local-date sums to the cent (Jul/Aug/Sep 2026). `findata.load_txns` also re-filters client-side by local date. `isWithIn pastNumberOfDays` works but is not used. One month of expenses: 116 rows, 0.19 s. (`teable.parse_filter`'s `date:` shorthand uses UTC midnight, so it has the same off-by-one for Melbourne-midnight dates; findata does not use it.)
- **`teable.get_records(take=1000)` default caps the total at 1000 rows**, not the page size (1102 transactions -> 1000 returned). Always pass `take=findata.ALL`.
- Other filters verified: `Type isAnyOf [Income, Transfer]` (123), `Amount isGreaterEqual 1000` (113), `Category isEmpty` (72 = all transfers), `Recurring is true` (71), nested `and(or(Description contains, Notes contains, Payee contains))`. **`contains` on a link field matches the linked record's title** (`Payee contains "wool"` -> 234), so text search covers payee names in the same call.
- **Link filters**: `isAnyOf [recId, ...]` on many-to-one links (Category, Payee, Account); `hasAnyOf` on many-to-many (Tags).
- **Server aggregation**: `GET /api/table/<id>/aggregation?field[sum][]=<fieldId>&filter=<json>` -> `{"aggregations":[{"fieldId":..,"total":{"value":6696.11,"aggFunc":"sum"}}]}`. Matched the client-side sum of 2026-08 expenses exactly. Passing `field` as a JSON string gives HTTP 400. Used as an independent cross-check, not as the main path (one call per figure).
- **groupBy** (`groupBy=[{"fieldId":..,"order":"asc"}]` on the record endpoint) returns `extra.groupPoints` with counts only, no sums. Not used.
- The generated API docs' plain `search=` returns HTTP 400 (it is a tuple); use `filter` + `contains` (case-insensitive).
- Default Python-urllib User-Agent gets HTTP 403; `teable.py` sends a curl UA.
- **Mixed date storage**: 1072 transactions read back at `T00:00:00.000Z` (UTC midnight, imported), 30 at `T14:00:00.000Z` (Melbourne midnight, entered in the UI). Both convert to the intended local date with `teable.local_date` (Melbourne). Never slice the ISO string for the date.
- **Date writes:** a plain `YYYY-MM-DD` is stored as Melbourne midnight on most days, but **on a DST-change day the offset is wrong**: `2026-10-04` (DST starts that morning) was stored as `2026-10-03T13:00:00.000Z`, which is 3 Oct 23:00 local (verified live 2026-10-05). `findata` writes dates as explicit Melbourne-midnight instants (`instant()`, DST-aware), and they read back correctly.
- **Aggregation for coverage:** `field[earliestDate][]` / `field[latestDate][]` on Date returns the first and last transaction in one call (`min`/`max` are rejected for dates).
- **Write shapes verified (run_flow, 2026-10-05):** POST/PATCH `/record` with `fieldKeyType=id`, `typecast=false`; many-to-one `{"id"}`, many-to-many `[{"id"}]`, clear with `null`; bulk PATCH takes per-record `fields`; `DELETE /record?recordIds=` goes to the trash. Account rollups (`Current Balance`) update immediately for new rows.
- **An invalid select option silently clears the field** (verified on tasks 2026-10-02). Validate against the live choices below before writing; read back.
- Unchecked checkboxes read as missing/`null`. `Recurring` default false; `Accounts.Active` default true.

## finance_Transactions `tblylfLkXFkYH2qB0ZQ` (1102 rows)

| Field | ID | Type / notes |
|---|---|---|
| Description (primary) | `fldRZcBYKr6w2GWw5lm` | bank statement text, e.g. `COLES 7682 STH MELBOURNE` |
| Date | `fldZIgdLJ79xoDQK5u4` | date, Melbourne; see mixed storage above |
| Type | `fldIqRcX7gZ1zn9Kmz0` | select `Income`, `Expense`, `Transfer` |
| Amount | `flde1ox2n7Q30UUP938` | number, **always positive**, currency 2dp |
| Recurring | `fldAiqG7oB0DCPeDL7K` | checkbox |
| Recurring Frequency | `fldTMF1faN48Lrd3vS4` | select `Weekly`, `Monthly`, `Yearly` |
| Receipt | `fldlgu9WLxc0FznWjO5` | attachment |
| Notes | `fldW2RsBfTxd362FjfO` | long text; imports hold `Statement type: ...; Effective date: YYYY-MM-DD` |
| Account | `fldcg0wB2iVE8DZCVHm` | many-to-one -> Accounts (reverse `fld5aM7gN7NhK7AYuVM`) |
| Transfer Account | `fldIeT7aNuRjEAVlyqL` | many-to-one -> Accounts, the destination of a Transfer (reverse `flddwaQQ81OY23P2Jbt`) |
| Category | `fldlU2BpJBZFcNcFhom` | many-to-one -> Categories |
| Payee | `fld8WNu5jDIr55RNkSu` | many-to-one -> Payees |
| Tags | `fldXRiV3NxrspHNLQFO` | many-to-many -> Tags |
| Budget | `fldVYJYqgs9p2GQSf9a` | many-to-one -> Budgets (unused; D-5) |
| Scope | `fldV9EFPhFI8W0OOMbF` | read-only lookup of **Account.Scope**, not the category's; Personal on every row |
| Signed Amount | `flddkw1CxatR4zrvXd0` | formula `IF(Type in (Expense, Transfer), -Amount, Amount)` |

## finance_Accounts `tblJLklwpGwbrfDlwIz` (1 row)

| Field | ID | Type / notes |
|---|---|---|
| Name (primary) | `fldSzvd0NAglB9qhsp1` | e.g. `ANZ Access Advantage (2992-86276)` |
| Scope | `fldZFxk5O8qT6AF6QV2` | select `Personal`, `Business` |
| Type | `fldaZgFxywk8cZT9l8V` | select `Checking`, `Savings`, `Credit Card`, `Cash`, `Investment`, `Mortgage` |
| Institution | `fldEHOdmX1nYcAaaybH` | text |
| Opening Balance | `fldiOOafvV1UPDJtV1f` | number |
| Opening Balance Date | `fldBjBPMxjYpGxs0yJ5` | date |
| Active | `fldRyzp4jLRtGqUd6gu` | checkbox, default true |
| finance_Transactions | `fld5aM7gN7NhK7AYuVM` | reverse of Transactions.Account |
| finance_Transactions (linked) | `flddwaQQ81OY23P2Jbt` | reverse of Transactions.Transfer Account |
| Own Txn Total | `fldxGuTHGj0kFXhVEQ0` | rollup sum(Signed Amount) of own transactions |
| Incoming Transfer Total | `fldShPCh4zNp2NRgBYo` | rollup sum(Amount) of transfers into this account |
| Net Activity | `fld04GdZkCiVlkrABed` | Own Txn Total + Incoming Transfer Total |
| Current Balance | `fldSTUAw8v0UMcTivzf` | Opening Balance + Net Activity (all time, not as of a date) |

## finance_Categories `tblp2Jvb2g90PN3fX4d` (24 rows, flat)

| Field | ID | Type / notes |
|---|---|---|
| Name (primary) | `flddvHdoGLLLyFYTXlM` | |
| Type | `fldBazKuxdsorHnlCmZ` | select `Income`, `Expense` |
| Scope | `flddiHU2kAnTeZG49P4` | select `Personal`, `Business`, `Shared`: the source of personal/business (D-4) |
| Parent Category | `fldmknXtvhmpIUmjTcP` | many-to-one self link (unused today) |
| finance_Categories | `fldQADwmtwhv2Qe0UCa` | children, reverse |
| Parent Name | `fldYtNHk7iAhQlQHQvd` | lookup |
| Full Path | `fldZZlGOiOHRb84DjDV` | formula `Parent > Name` or `Name` |
| finance_Payees / finance_Budgets / finance_Transactions | `fldPKGGlI8LBZ9GOO5F` / `fld3qDsS1na7qJVvPZ1` / `fld2hxfGgtrPZk5h8cW` | reverses |

## finance_Payees `tblpyC3PfoG0DN8dQ2t` (127 rows)

| Field | ID | Type / notes |
|---|---|---|
| Name (primary) | `fldnbT296ypPXkiJkkF` | normalised merchant, e.g. `Woolworths` |
| Type | `fldJ8YwtDNxCKZvPNVO` | select `Vendor`, `Client`, `Employer`, `Store`, `Person`, `Other` |
| Scope | `fldf7p7Ub27gXLzi7nP` | select `Personal`, `Business`, `Both` |
| Default Category | `fld6XnWnCCu7GsWfJzh` | many-to-one -> Categories |
| finance_Transactions | `fldnu4hjQgCGdofNWv3` | reverse |

## finance_Tags `tblhOQKXpSzr0Ezh8rR` (3 rows, 0 tagged transactions)

| Field | ID | Type / notes |
|---|---|---|
| Name (primary) | `fldie2h6YM3fA6WPH0Z` | `Recurring / Subscription`, `Tax Deductible`, `Reimbursable` |
| Color | `fldZQDvslg2GJfBTE9K` | select `Light Blue`, `Blue`, `Deep Blue`, `Organge` (sic), `Green`, `Deep Red`, `Light Green` |
| finance_Transactions | `fldTX2wREzbxeaKDl06` | reverse (many-to-many) |

## finance_Budgets `tblDk3iXFz5YiYUkwz6` (0 rows)

| Field | ID | Type / notes |
|---|---|---|
| Month (primary) | `fldzRSk36rF2iLqoc1A` | date, shown `YYYY-MM`; write the 1st of the month |
| Planned Amount | `fldJXYFV5eXNnALW40c` | number |
| Category | `fldfCZXAsjS3nEM0MGW` | many-to-one -> Categories |
| Scope | `fldWtNgqZiz6JcSAUkB` | read-only lookup of Category.Scope |
| finance_Transactions | `fld0MY2qyEpHKu2xqqP` | reverse of Transactions.Budget |
| Actual Spent | `fldCEyMLCffN6AU15n9` | rollup sum(Amount) of **linked** transactions only; ignored (D-5) |
| Variance / % Used | `fldBbkdGPNoAwaD1nMc` / `fldYGBsE6yNmObjpM3B` | formulas on Actual Spent; ignored |

## Views

Only "Grid view" per table: Transactions `viwMnxkykx6th4GzISr`, Accounts `viwXTqw9mTb4BrYDLYw`, Categories `viwOu4A70cLNjCWgg5E`, Payees `viwZZwB28wMiQ0QGRyg`, Tags `viwByxGjZwOJKU65sTn`, Budgets `viw2AVUTydc5h9tFRNJ`.

## Link write shapes

Reads return `{ "id": "recXXX", "title": "..." }`. Many-to-one write `{ "id": "recXXX" }`; many-to-many write `[{ "id": "recXXX" }, ...]` (the whole array: read, add, write); clear with `null`.

## State notes (2026-10-05)

- 1102 transactions, 2025-10-30 .. 2026-09-18 (data 17 days old at capture). Expense 979 / Transfer 72 / Income 51.
- Accounts: ANZ Access Advantage (checking, opening 7,932.94 on 2025-10-29, active). On 2026-10-06 an inactive account `ANZ (013148-807590005)` (`recYocOdVLGTJD26I1t`) was added. Its 22 incoming transfers (`TRANSFER .. FROM 807590005`, $25,060) now have Account = it and Transfer Account = ANZ, and 26 outgoing transfers (`TO 013148807590005`, $74,300) have Transfer Account = it. ANZ Current Balance went from -49,140.46 to **979.54** (it had counted the inbound rows as money out). Undo files are in `~/.cache/finance-management/undo/20261006-0001*`.
- Transfers have no Category or Payee. 48 are linked to account 807590005 (see above). 24 are still unlinked outgoing transfers (e.g. `TO WANG JUNYANG`, `TRANSFER ... TO 013664733557893`).
- Clean-up 2026-10-05: 2 Income rows moved from Expense categories to Refunds, and 112 payees got a Default Category. Duplicate check: 8 same-day groups, all consecutive lines of one import (the bank statement lists them twice). The Woolworths $19.05 pair was reversed by the bank the same day. None was deleted.
- 71 rows flagged Recurring, all Monthly. No tags used. No budgets. No parent categories.
