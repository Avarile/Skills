**I found 9 possible duplicate groups (11 extra rows), but the records point to genuine repeat charges, not double imports. So I haven't deleted anything.** I'd want you to check the two income pairs against your ANZ statement first.

Scope: all time, 1,102 rows, data runs 2025-10-30 to 2026-09-18 (17 days old). A group means the same date, type, amount and payee.

| # | Date | Type | Amount | Payee | Rows | My read |
|---|---|---|---|---|---|---|
| 1 | 2025-11-25 | Expense | $1.00 | Aaron Sansoni Foundation | 3 | Likely real: three separate $1 EFTPOS donations |
| 2 | 2025-11-26 | Expense | $1.00 | Aaron Sansoni Foundation | 2 | Likely real, same pattern as the day before |
| 3 | 2026-01-02 | **Income** | **$5,000.00** | Xiaolan Wang | 2 | **Check this one.** Two separate statement lines, but it's large |
| 4 | 2026-01-12 | **Income** | **$2,143.00** | Runfang Wang | 2 | **Check this one.** Same as above |
| 5 | 2026-04-14 | Expense | $3.00 | Woolworths (Doncaster) | 2 | Likely real: two small purchases |
| 6 | 2026-07-03 | Expense | $2.50 | Coles | 2 | **Not a duplicate.** Two different stores (Sth Melbourne and Doncaster) |
| 7 | 2026-08-10 | Expense | $24.00 | Melbourne Airport | 2 | Likely real, e.g. parking or two items |
| 8 | 2026-08-10 | Expense | $4.00 | Innovative Retail (Box Hill Sth) | 2 | Likely real: probably two vending machine purchases |
| 9 | 2026-08-28 | Expense | $19.05 | Woolworths (Doncaster) | 2 | Possible double tap. Check the statement |

**Why I think they're real:**
- Every row in a group came in **in the same import, as consecutive statement lines** (same import time, back-to-back record numbers). That means the bank statement itself lists the charge twice. A re-import of the same statement would show up as rows from different imports.
- I checked all 1,102 rows for the same description and amount within 3 days across different imports and **found 0**. The three imports (2026-08-16, 08-23 and 09-19) cover date ranges that don't overlap. So no statement was loaded twice.
- If a pair is wrong, the cause is on the bank side (for example, a payment received twice and later reversed), not in your data entry. Deleting one would make the records disagree with the statement.

**What matters most:** groups 3 and 4. If either is a mistake, your income from Client Payments is overstated by $5,000.00 or $2,143.00. The rest add up to a few dollars each.

**If you confirm any of them are really doubled,** I'd remove one row from each pair and keep the earlier record:
- Group 3: drop `recEqcK3iunBjCQPpNQ`, keep `recV5qjHlupOsEY7r48`
- Group 4: drop `receHRQ6Kx5LQ0RhHlW`, keep `recCy7nSXk62z3dB5dM`
- Group 9: drop `recdZkbNhiwTRevUlsJ`, keep `recET9lh22CZhJvQdMW`

For each one I'd run `fin.py delete <id>` as a dry run, show you the preview, and only then run it with `--yes`. Deleted rows go to the Teable trash, and `fin undo` can't bring them back. I tried to run the dry run for groups 3 and 4 now, but the session's permission check blocked it. So nothing was previewed or changed.

Changed: nothing.

Which groups, if any, should I remove after you've checked your ANZ statement? My suggestion is none, unless the statement shows the $5,000 or $2,143 payment was reversed or only arrived once.
