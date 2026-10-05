# Actions log: eval-09-exclude-payee (with_skill, run-1)

1. Read `skill_dev/finance-management/SKILL.md`. Chose human mode; periods `12m` = trailing complete months (D-3); headline = net spend (D-2); `--exclude-payee` filter available.
2. `python3 skill_dev/finance-management/scripts/fin.py summary 12m --exclude-payee "Aiyun Yu"` (exit 0)
   - Period 2025-10-01..2026-09-30, 1091 rows; data 2025-10-30..2026-09-18; coverage warnings at both ends
   - Expenses $35,186.24, Refunds $360.77, **Net spend $34,825.47**, $2,902.12/month, Transfers out $173,094.88 (excluded from cost)
3. `fin.py summary 12m` (no filter, for comparison) (exit 0)
   - 1102 rows; Expenses $63,346.24, Net spend $62,985.47
4. `fin.py search --period 12m --payee "Aiyun Yu" --include-transfers` (exit 0)
   - 11 matches, all Expense / Personal Transfers, 2025-12-01..2026-08-31, total $28,160.00 (matches the 11-row, $28,160 difference)
5. `fin.py search aiyun --period 12m --include-transfers` (exit 0): same 11 rows, so no Aiyun payments sit under another payee name
6. `fin.py breakdown 12m --by category --exclude-payee "Aiyun Yu"` (exit 0)
   - Total $34,825.47 over 19 groups; Food $9,039.16, Rent & Housing $5,426.79, Shopping $3,197.96, Insurance $3,185.13, Education & Childcare $2,536.96, Dining $2,251.96, Utilities $2,124.45; remaining Personal Transfers $535.00 (3 rows); Refunds -$360.77
7. `fin.py summary 2025-11..2026-08 --exclude-payee "Aiyun Yu"` (exit 0), the fully covered window
   - 1018 rows, no coverage warning; Net spend $33,619.03, $3,361.90/month
8. Wrote response.md and actions.md (the heredoc write timed out in the shell but both files were written; checked with ls). No database writes were made.
9. Edited response.md: corrected the period line, since `12m` includes September 2026 and October 2026 is the excluded month-to-date. Also removed a hand-computed "Everything else" row (rule 1: no hand-computed money). Every figure in the response now comes straight from CLI output.
