# Actions log: eval-01-cost-windows (without_skill, run-1)

1. `ls references/` and `grep -c CYBERNETICS_DATA_API_TOKEN .env`: found 6 finance_* API reference docs; token present (not printed).
2. `cat references/finance_Transactions finance_Categories finance_Accounts`: got table IDs (Transactions tblylfLkXFkYH2qB0ZQ, Categories tblp2Jvb2g90PN3fX4d, Accounts tblJLklwpGwbrfDlwIz) and fields (Date, Type Income/Expense/Transfer, Amount (always positive), Category, Signed Amount, Recurring...).
3. Bash/curl GET (read-only) of all Transactions (take=1000, skip 0/1000/2000/3000), Categories and Accounts into the scratchpad. Results: 1,102 transactions (1000 + 102), 24 categories, 1 account (ANZ Access Advantage, opening balance 7,932.94 on 2025-10-29).
4. Python inspection: dates from 2025-10-30 to 2026-09-18. Types: Expense 979, Transfer 72, Income 51. All Scope = Personal. No negative amounts. Every Expense has a category. Recurring flag is set on 71 records (Monthly) only.
5. Python monthly totals by type. Expense per month: Oct25 82.65 (5 txns, partial), Nov 4,910.00, Dec 9,310.48, Jan 4,733.78, Feb 7,536.56, Mar 7,981.95, Apr 1,966.05, May 4,964.40, Jun 8,167.64, Jul 5,872.83, Aug 6,696.11, Sep 1,123.79 (58 txns, data ends 18 Sep, so partial).
6. Python check of Transfers (all to own accounts …3557893/…7590005, "TO WANG JUNYANG" 8 txns 18,858.88, plus "FROM 807590005"). Excluded them from costs. Personal Transfers category: monthly 2,816 to Aiyun Yu (1 Jun AND 30 Jun, 31 Jul, 30 Aug; no Sep one yet). Refunds total 360.77.
7. Python window calc (Expense only):
   - Aug 2026: 6,696.11 (Personal Transfers 2,816; Food 1,564.78; Shopping 1,353.10)
   - Jun–Aug 2026: 20,736.58 (PT 11,264)
   - Mar–Aug 2026: 35,648.98 (PT 19,712)
   - Nov25–Aug26 (10 full months): 62,139.80 (PT 28,695; business scope 1,814.58)
   - All data: 63,346.24
   - Rolling to 2026-10-05: 1M 1,043.91 | 3M 12,889.91 | 6M 28,770.39 | 12M 63,346.24
   - Sep 1–18 partial: 1,123.79
8. Python averages/annualised: Aug 6,696.11/mo; 3M 6,912.19/mo; 6M 5,941.50/mo; 10M 6,213.98/mo, annualised 74,567.76. Excluding personal transfers: 3,880.11; 9,472.58 (3,157.53/mo); 15,936.98 (2,656.16/mo); 33,444.80 (3,344.48/mo, annualised 40,133.76).
9. Wrote response.md and actions.md (this file). No database writes were made.
