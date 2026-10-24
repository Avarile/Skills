# Actions log — eval-05 "Did I spend more than usual in August?" (without skill)

1. `ls references/` and `grep -o '^[A-Z_]*=' .env` → found API docs for the 6 finance tables; .env has CYBERNETICS_DATA_API_TOKEN and CYBERNETICS_DATA_API_URL (token value not printed).
2. `cat references/finance_Transactions; head references/finance_Categories` → Transactions table tblylfLkXFkYH2qB0ZQ. Fields: Date, Type (Income/Expense/Transfer), Amount, Category (link), Payee (link), Scope, Signed Amount. Categories table tblp2Jvb2g90PN3fX4d.
3. Wrote /tmp/fin/fetch.py (read-only GET, paginated take=1000) and ran it → HTTP 403 Forbidden (the default Python User-Agent was blocked).
4. Added a User-Agent header and re-ran → fetched tx=1102 records, categories=24, accounts=1, budgets=0. Saved to /tmp/fin/*.json.
5. python: inspected the record shape, the category list and monthly totals by Type. Expense by month: Nov 4,910; Dec 9,310; Jan 4,734; Feb 7,537; Mar 7,982; Apr 1,966; May 4,964; Jun 8,168; Jul 5,873; **Aug 6,696**; Sep (partial, to 18 Sep) 1,124. Oct 2025 is partial (data starts 30 Oct).
6. python: checked date coverage per month (Nov–Aug are full months; Sep ends 2026-09-18) and built an expense-by-category-by-month table. In August, Food was 1,565, Shopping 1,353, Personal Transfers 2,816, Dining 407, Insurance 272 and Rent & Housing 0.
7. python: baselines over the Nov–Jul (9-month) window:
   - All expenses: Aug 6,696.11 vs mean 6,160.41, median 5,872.83, min 1,966, max 9,310, Feb–Jul mean 6,081.57, May–Jul mean 6,334.96.
   - Excl. Personal Transfers: Aug 3,880.11 vs mean 3,284.97, Feb–Jul mean 2,750.40, May–Jul 2,580.29.
   - Food+Shopping+Dining: Aug 3,324.60 vs mean 1,153.38, Feb–Jul 1,070.95.
   - Food: Aug 1,564.78 vs Feb–Jul 868.14. Shopping: 1,353.10 vs 112.57. Dining: 406.72 vs 90.23.
   - Top August expenses: Aiyun Yu transfer 2,816 (30 Aug), JB Hi-Fi 999 (30 Aug), No 1 Asian Mart 276.47, Allianz 119.03 and 117.31, Dumpling Alley 109.93, Phillip Island Chocolate 102.
8. python: checked Rent & Housing history: Clink 658 in May and Jun, 162.79 in Jul, none in Aug. Listed Jul/Aug Transfer-type records (moves to and from account 013148807590005, excluded from spending). Food transactions in Aug: 63 (Feb–Jul 50–74). Personal Transfers per month: 0–3 payments. August food by payee: Woolworths 643.39, Coles 276.88, No 1 Asian Mart 276.47, KFL 241.56. Feb–Jul monthly average by payee: Woolworths 347, Coles 182, KFL 165, No 1 Asian Mart 56.
9. python: expenses excluding Personal Transfers by month: Nov 4,650; Dec 3,678; Jan 4,734; Feb 4,446; Mar 2,350; Apr 1,966; May 2,148; Jun 2,536; Jul 3,057; **Aug 3,880** (highest since Feb). Personal Transfers total Nov–Aug = 28,695 (≈2,870/mo). Expenses with no category: 0.
10. Wrote response.md and actions.md (this file). No database writes were made.
