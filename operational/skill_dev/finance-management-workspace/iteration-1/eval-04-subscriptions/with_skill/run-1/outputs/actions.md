# Actions log — eval-04-subscriptions, with_skill, run-1

1. Read `skill_dev/finance-management/SKILL.md`. The commands table maps "subscriptions" to `recurring [--all]`.
2. `python3 skill_dev/finance-management/scripts/fin.py recurring` (exit 0)
   - Coverage: all time, 1102 rows, data 2025-10-30..2026-09-18 (17 days old); status judged as of 2026-09-18
   - 9 active, all monthly: Aiyun Yu $2,816.00/mo ($33,792.00/yr, Personal Transfers); Allianz $119.03 ($1,428.36/yr); Allianz ABS $117.31 ($1,407.72/yr); Dodo $77.99 ($935.88); ahm $35.50 ($426.00); Amaysim $25.00 ($300.00); Amazon Prime $9.99 ($119.88); NestJS $7.37 ($88.44); Retell AI $2.94 ($35.28)
   - Active total: $3,211.13/mo, $38,533.56/yr; 7 stopped hidden
3. `fin.py recurring --all` (exit 0)
   - 7 stopped: Clink $658.00/mo (last 2026-07-14), Lumo Energy $175.00 (2026-01-02), Telstra $93.00 (2025-12-29), Postiz $45.49 (2025-12-18), Twinkl $19.99 (2026-02-11), Cloudflare $15.74 (2026-04-27), Retell AI $4.69 (2025-12-10)
4. `grep` in references/*.md for recurring/subscription notes. workflows.md confirms `fin recurring` (`--all` adds stopped items). schema.md: 71 rows flagged Recurring, all Monthly.
5. `fin.py recurring --exclude-category "Personal Transfers"` (exit 0). This got a CLI-computed subtotal without the transfer to a person.
   - 1087 rows; 8 active; **$395.13/mo, $4,741.56/yr**
6. `fin.py search allianz --period 3m --limit 12` (exit 0). This checked whether the two Allianz lines were duplicates.
   - 6 rows, 2026-07..2026-09 (partial warning: no data after 2026-09-18); two different debits each month ($119.03 "TO ALLIANZ INSURE…" around the 6th–7th, $117.31 "ALLIANZ INSURANCE ABS" around the 13th–16th). These are two policies, not duplicates. Net $709.02 over 3 months = $236.34/mo (CLI figure).
7. Wrote outputs/response.md and outputs/actions.md.

No database writes. No other files modified.
