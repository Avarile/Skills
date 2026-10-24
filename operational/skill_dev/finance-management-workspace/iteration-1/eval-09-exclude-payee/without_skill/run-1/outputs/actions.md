# Actions log — eval-09-exclude-payee (without_skill, run-1)

1. `ls references/` + `grep -o '^[A-Z_]*=' .env` — listed the API reference docs (6 finance tables) and confirmed env var names (CYBERNETICS_DATA_API_TOKEN, CYBERNETICS_DATA_API_URL) without printing values.
2. `cat references/finance_Transactions references/finance_Payees` — got table IDs (Transactions tblylfLkXFkYH2qB0ZQ, Payees tblpyC3PfoG0DN8dQ2t), field IDs and types (Type: Income/Expense/Transfer; Amount; Signed Amount; Payee link; pagination take≤1000).
3. Wrote scratch fetch script (scratchpad/fetch.py) using urllib to GET all records (take=1000, paging) for Transactions, Payees, Categories, Accounts → **HTTP 403 Forbidden**.
4. `curl` test GET on Payees (take=1) with Bearer token → HTTP 200 (403 was caused by urllib's default User-Agent).
5. Re-ran fetch.py with `User-Agent: curl/8.0` → read-only GETs: **tx 1102, payees 127, categories 24, accounts 1**. Saved JSON to the scratchpad.
6. Python analysis: found payee **"Aiyun Yu" (recduQ91W70uAMJpohS, Type Person, 11 linked txns)**. Descriptions with "AIYUN": 10× "TO AIYUN YU" + 1× "TO AIYUN YU WEN ZHANG", all linked to that payee. Data range is **2025-10-30 → 2026-09-18**. Types: Expense 979, Transfer 72, Income 51.
7. Python analysis for the window 2025-10-05..2026-10-05 (all 1102 records fall inside it):
   - Aiyun Yu txns: 11, all Expense / Personal Transfers, total **$28,160** (9×$2,816, $1,300, $1,516); no unlinked "aiyun" descriptions.
   - No zero/negative or missing Expense amounts.
   - All expenses: **$63,346.24 (979 txns)**; excluding Aiyun Yu: **$35,186.24 (968 txns)**. All in Personal scope.
   - Income total $179,367.72 (not used). Listed the 72 Transfer txns (account-to-account, incl. -$18,858.88 "TO WANG JUNYANG"); left them out of spending.
8. Python breakdown of the spending without Aiyun Yu:
   - By category: Food 9,039.16; Rent & Housing 5,426.79; Shopping 3,197.96; Insurance 3,185.13; Education & Childcare 2,536.96; Dining & Takeaway 2,251.96; Utilities 2,124.45; Cash Withdrawal 1,200; Council & Government 1,199.27; Subscriptions & Software 1,070.21; Vehicle & Rego 955.48; Transport 834.02; Business Expenses 787.42; Travel & Accommodation 638.96; Personal Transfers 535; Health & Wellness 125.82; Entertainment 72.65; Donations 5.
   - By month: 2025-10 82.65; 11 4,910.00; 12 3,678.48; 2026-01 4,733.78; 02 4,720.56; 03 2,349.95; 04 1,966.05; 05 2,148.40; 06 2,535.64; 07 3,056.83; 08 3,880.11; 09 1,123.79.
   - Top payees: Clink 5,426.79; Woolworths 3,524.37; Allianz 2,601.46; Coles 1,866.79.
   - Refund-type income: Refunds $360.77 (net spending ≈ $34,825.47); also rego rebate $174.26 and insurance payout $27.
9. Wrote response.md and actions.md (this file). **I made no writes to the database.**
