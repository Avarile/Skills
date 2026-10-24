# Actions log — eval-07-partial-month / without_skill / run-1

1. `ls references/` and `grep -c CYBERNETICS_DATA_API_TOKEN .env`: found 6 finance_* API docs. The token exists (it was not printed).
2. ToolSearch `select:mcp__cyb-data__list_tables,get_table_schema,query_records,list_bases`: loaded the schemas. I didn't use them in the end; REST was simpler for bulk reads.
3. `cat references/finance_Transactions` plus the start of finance_Categories and finance_Accounts: got the table IDs and fields. Transactions are tblylfLkXFkYH2qB0ZQ, with fields Date, Type (Income/Expense/Transfer), Amount, Signed Amount (formula), Category, Account and Transfer Account. Each request returns at most 1000 records.
4. Bash curl GET (read-only), take=1000, for Transactions, Accounts, Categories, Budgets and Tags. Got tx 1000 (hit the cap), acc 1, cat 24, bud 0, tags 3.
5. Bash curl to page through Transactions with skip=0 and skip=1000: 1000 + 102 = **1,102 transactions**, all unique. (The `rm` glob warning didn't matter.)
6. Python inspection failed: acc.json had a different structure. I suspected a shared scratchpad being overwritten by a parallel run.
7. `head` of acc.json/cat.json to confirm the structure.
8. Re-downloaded all tables (GET only) into a unique scratch subdirectory `scratchpad/eval07_nosk_r1/`: tx 1,102, acc 1, cat 24, bud 0, tags 3.
9. Python check of coverage:
   - One account: ANZ Access Advantage (2992-86276).
   - Date range is 2025-10-30 to **2026-09-18**. No October records.
   - createdTime batches: 2026-08-16 (600), 2026-08-23 (412), **2026-09-19 (90)**.
   - September (UTC date): 64 records (58 Expense, 4 Transfer, 2 Income), dated 1–18 Sept only. Expense total $1,123.79.
   - Monthly expense totals: Mar 7,981.95; Apr 1,966.05; May 4,964.40; Jun 8,167.64; Jul 5,872.83; Aug 6,696.11.
10. Python check of time storage: 30 of the 19 Sept batch are stored at T14:00Z (Melbourne midnight); everything else is at T00:00Z. I converted to Melbourne local dates. The records that cross the 31 Aug / 1 Sept boundary are a Transfer of $5,200 and Income of $5,388.31, not expenses. In local dates September has 66 records (1–18 Sept), and the expense total is unchanged.
11. Python September breakdown (local dates), Expense only:
   - **Total $1,123.79, 58 transactions.**
   - Food 586.51 (43), Insurance 236.34 (2), Utilities 102.99 (2), Dining & Takeaway 59.40 (4), Shopping 55.50 (2), Subscriptions & Software 43.05 (3), Travel & Accommodation 30.00 (1), Vehicle & Rego 10.00 (1).
   - No uncategorised expenses.
   - Transfers to 013148807590005: 5,200 + 1,500 + 3,000 + 2,000 out, and 1,000 back on 9 Sept. The incoming one has Signed Amount −1000, which is a data issue.
   - Income: 5,388.31 + 5,388.31 + 1,643.04 = 12,419.66.
12. Python comparison of days 1–18 with full months (local dates):
   - Days 1–18: Mar 4,644.59; Apr 1,426.12; May 4,485.26; Jun 4,838.81; Jul 1,925.63; Aug 2,029.02.
   - Mar–Aug averages: 5,941.50 for full months and 3,224.91 for days 1–18. Nov–Aug averages: 6,213.98 full and 3,776.43 for days 1–18.
   - Biggest August expense: 2,816 TO AIYUN YU on 31 Aug.
13. Python list of Personal Transfers and Rent: the 2,816 TO AIYUN YU appears around the month boundary every month (01-Dec … 30-Aug). The Clink rent direct debit (658, around the 14th) last appeared in Jul at 162.79, so none is expected in September.
14. Wrote response.md and actions.md (this file).

No database writes were made. All API calls were GET.
