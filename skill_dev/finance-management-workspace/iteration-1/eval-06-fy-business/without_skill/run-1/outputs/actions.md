# Actions log — eval-06 FY2026 business income/expenses (without skill)

1. `ls references/` + `grep -c CYBERNETICS_DATA_API_TOKEN .env` — found API docs for the 6 finance tables; token present (not printed).
2. `cat references/finance_Transactions finance_Categories finance_Accounts` — got table IDs and field IDs. Transactions has Type (Income/Expense/Transfer), Amount, Date, Category link, and a read-only Scope. Categories have Type and Scope (Personal/Business/Shared).
3. Wrote scratch script `fetch.py` (in session scratchpad): GET all records from each finance table via the Teable REST API (`take=1000`, paginated). First run → HTTP 403 (urllib default User-Agent blocked).
4. Re-ran with a curl-style User-Agent → tx 1102, acc 1, cat 24, pay 127, tag 3, bud 0.
5. JSON parse failed because the file handle wasn't closed; fixed with a `with` block, re-fetched and validated (same counts).
6. Inspected data: 1 account (ANZ Access Advantage, Scope=Personal, opening balance date 2025-10-29). Business-scope categories: Business Income, Client Payments (Income); Business Expenses, Subscriptions & Software (Expense). Transaction dates run from 2025-10-30 to 2026-09-18. All 1102 transactions have Scope=Personal (inherited from the account).
7. Aggregated FY2026 (2025-07-01..2026-06-30): 802 transactions. By category scope: Business Income 17 / $91,431.27; Client Payments 12 / $41,708.00; Business Expenses 1 / $407.50; Subscriptions & Software 37 / $596.36. Transfers 49 / $124,877.52 (excluded). No Tax Deductible tags in FY2026. No negative amounts.
8. Listed each business transaction and summarised transfers. Business Income is a fortnightly "PAY" of $5,378.31 from BusinessAI Group (15) and Sansoni Management (2). Client Payments are 12 personal payments dated 2–12 Jan 2026. Subscriptions include Amazon Prime and Apple.
9. Keyword scan of non-business categories for likely business costs: Telstra $186.00 (Utilities), JB Hi-Fi $29.00, Officeworks $1.44.
10. Final totals: business income $133,139.27 (29 tx); business expenses $1,003.86 (38 tx); net $132,135.41. Amazon Prime + Apple = $89.93 (7 tx), so expenses without them = $913.93. Stricter view (wages and personal subscriptions excluded): income $41,708.00, expenses $913.93, net $40,794.07. FY2027 so far (context only): Business Income 6 / $32,329.86, Business Expenses 1 / $379.92, Subs 12 / $473.85.
11. Wrote response.md and actions.md. No database writes were made.
