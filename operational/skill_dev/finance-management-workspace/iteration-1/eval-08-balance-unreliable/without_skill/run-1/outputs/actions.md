# Actions log (eval-08-balance-unreliable, without_skill, run-1)

All reads only. No database writes.

1. `ToolSearch select:list_tables,query_records,get_table_schema,list_bases`: loaded the cyb-data MCP tools.
2. `mcp__cyb-data__list_bases`: found base data-centre `bseJEuE54y5caWO0Xc8`.
3. `mcp__cyb-data__list_tables(bseJEuE54y5caWO0Xc8)`: finance_Accounts = `tblJLklwpGwbrfDlwIz`, finance_Transactions = `tblylfLkXFkYH2qB0ZQ`.
4. `mcp__cyb-data__get_table_schema(finance_Accounts)`: Current Balance = Opening Balance + Net Activity. Net Activity = Own Txn Total (rollup) + Incoming Transfer Total (rollup).
5. `mcp__cyb-data__get_table_schema(finance_Transactions)`: Signed Amount = IF(Type in {Expense, Transfer}, -Amount, Amount). Every Transfer counts as an outflow.
6. `mcp__cyb-data__query_records(finance_Accounts)`: 1 account, "ANZ Access Advantage (2992-86276)", Personal Checking, Opening $7,932.94 @ 2025-10-29, Own Txn Total -$57,073.40, Incoming Transfer Total $0, **Current Balance -$49,140.46**.
7. `ls references/` and `grep` for the variable names in .env (values not printed): found the API docs and the token variable name.
8. `head references/finance_Transactions`: read the REST read/pagination syntax.
9. `curl GET /api/table/tblylfLkXFkYH2qB0ZQ/record` (take=1000, skip 0..3000) saved to scratchpad: 1,102 transactions (1000 + 102).
10. `python3 an.py` (analysis): all 1,102 on the ANZ account. Transfer Account never set. Types: 979 Expense / 72 Transfer / 51 Income. All amounts positive. Dates 2025-10-30 to **2026-09-18**. None before the opening date, none in the future. Sums: Income $179,367.72, Expense $63,346.24, Transfer $173,094.88. Signed sum -$57,073.40. 8 same-day/amount/description duplicate groups (9 extra rows, $7,196.05).
11. `python3 an2.py`: transfers "FROM" = 22 rows / **$25,060.00** (inflows from …807590005). Transfers "TO" = 50 rows / $148,034.88. DB formula balance -$49,140.46. **Corrected balance $979.54**. Notes contain only the statement type and effective date, no bank balances.
12. `python3` (notes/duplicate check): no balance info in Notes. Duplicates have the same statement type. The $19.05 Woolworths duplicate has a matching "REV VISA DEBIT PURCHASE" $19.05. Judged as genuine repeats.
13. `python3` (statement type cross-check): ACCOUNT_TRANSFER and MBANKING_FUNDS_TRANSFER are used for both directions, so the description ("FROM") is the only direction signal. Using the statement type alone reproduces -$49,140.46.
14. `curl GET /api/table/tblJLklwpGwbrfDlwIz/field`: confirmed Own Txn Total = sum(Signed Amount) via Account, and Incoming Transfer Total = sum(Amount) via Transfer Account. This is the basis for the proposed fix (re-link the inbound transfers).
15. `mkdir -p` the outputs directory. Wrote response.md and actions.md.

Key figures: DB Current Balance -$49,140.46; corrected $979.54 as of 2026-09-18 (17 days stale); inbound transfers mis-signed $25,060.00 (error $50,120.00).
