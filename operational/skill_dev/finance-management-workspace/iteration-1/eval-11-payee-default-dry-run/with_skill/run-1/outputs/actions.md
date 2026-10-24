1. Read `skill_dev/finance-management/SKILL.md` (mode: human; `payee-default` needs a dry run plus user confirmation under D-6).
2. `fin.py payee-default --help`, plus grep of `references/workflows.md` for payee-default. Usage: `payee-default <payee> --category <C> [--yes]`. The workflow is "teach a payee" with a dry run first, and `payee-default` needs the user's OK.
3. `fin.py payee-default Woolworths --category Food` (DRY RUN, exit 0). Output: default category (none) -> Food; 0 of 234 transactions have another or no category; nothing written.
4. `fin.py breakdown all --by payee --text woolworths`: there is only one matching payee, "Woolworths". 234 rows, $3,505.32 net, data range 2025-10-30..2026-09-18.
5. `fin.py breakdown all --by category --payee Woolworths`: Food has 233 rows ($3,524.37) and Refunds has 1 row (-$19.05).
6. `fin.py search --payee Woolworths --category Refunds`, plus grep of fin.py's payee-default logic. The Refunds row is a single Income row on 2026-08-28 for $19.05. The preview only counts rows whose type matches the category (Expense), so the refund is correctly left out of the "0 other" count.
7. grep for Default Category usage in scripts and references. `findata.add` uses the payee's Default Category when no category is given, and doctor group E reports payees without one.
8. Wrote response.md and actions.md. No database writes (`--yes` was never used).
