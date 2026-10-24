1. Read `skill_dev/finance-management/SKILL.md` (Human mode; D-1 cost = expenses only, D-2 headline = net spend; rule 2: check coverage line).
2. `python3 skill_dev/finance-management/scripts/fin.py summary 2026-09`
   - 66 rows; data 2025-10-30..2026-09-18 (17 days old); WARNING: no data after 2026-09-18 (19–30 Sep missing/partial)
   - Income $12,419.66; Expenses $1,123.79; Refunds $0.00; Net spend $1,123.79; Transfers out $12,700.00; Net cash flow -$1,404.13; rows Expense 58 / Income 3 / Transfer 5
3. `fin.py breakdown 2026-09 --by category`
   - Food $586.51 (52.2%), Insurance $236.34, Utilities $102.99, Dining & Takeaway $59.40, Shopping $55.50, Subscriptions & Software $43.05, Travel & Accommodation $30.00, Vehicle & Rego $10.00; total $1,123.79
4. `fin.py summary 2026-09-01..2026-09-18` (covered range only)
   - Net spend $1,123.79; per day $62.43; no coverage warning
5. `fin.py cost --windows 1,3,6 --anchor 2026-08`
   - 2026-08 $6,677.06; Jun–Aug $20,716.55 ($6,905.52/month); Mar–Aug $35,623.46 ($5,937.24/month)
6. `fin.py breakdown 2026-08 --by category`
   - Personal Transfers $2,816.00 (1 row, 42.2%), Food $1,564.78, Shopping $1,353.10, ...; total $6,677.06
7. `fin.py summary 2026-08-01..2026-08-18` (like-for-like comparison)
   - Net spend $2,029.02; per day $112.72
8. Wrote response.md and actions.md. No database writes.
