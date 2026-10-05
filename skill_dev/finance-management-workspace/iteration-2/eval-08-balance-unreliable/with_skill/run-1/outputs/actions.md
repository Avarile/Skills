1. Read `skill_dev/finance-management/SKILL.md`. Core rule 3: use `fin.py balance`, not the Current Balance field. Tell the user it covers one account only, up to the last transaction, and to check their bank.
2. `python3 skill_dev/finance-management/scripts/fin.py balance`
   - Account: ANZ Access Advantage (2992-86276), opening $7,932.94 on 2025-10-29
   - Corrected balance at the last transaction: **$979.54**. Formula (Current Balance field): **-$49,140.46**
   - Warning: 22 incoming transfers ($25,060.00) stored as Transfer and subtracted by the formula (doctor group K)
   - Month-end corrected balances: 2025-10 $4,050.29, 2025-11 $6,551.33, 2025-12 $5,963.58, 2026-01 $5,261.06, 2026-02 $2,964.26, 2026-03 $1,871.32, 2026-04 $6,104.53, 2026-05 $4,083.78, 2026-06 $2,041.69, 2026-07 $853.81, 2026-08 $383.67, 2026-09 $979.54
3. `python3 skill_dev/finance-management/scripts/fin.py balance --json` (same figures: final 979.54, formula_balance -49140.46, incoming_transfers 22). Piped into the next command so both ran in one call.
4. `python3 skill_dev/finance-management/scripts/fin.py summary mtd` (to get the data coverage date)
   - Coverage: data 2025-10-30..2026-09-18 (17 days old). 0 rows in Oct 2026 MTD. Last transaction 2026-09-18.
5. Wrote response.md and actions.md. No database writes, no `--yes`, no MCP calls.
