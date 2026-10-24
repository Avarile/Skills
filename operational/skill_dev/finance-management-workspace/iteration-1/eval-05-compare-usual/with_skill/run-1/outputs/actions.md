# Actions log: eval-05 "Did I spend more than usual in August?"

1. Read `skill_dev/finance-management/SKILL.md`. Human mode. Headline = net spend (D-2); Personal Transfers count as cost (D-1).
2. `fin.py compare --help`, then `fin.py summary 2026-08`. Coverage: 128 rows, data 2025-10-30..2026-09-18, so August is complete. Expenses $6,696.11, Refunds $19.05, **Net spend $6,677.06**, transfers out $17,600 (excluded).
3. `fin.py compare 3m-avg --anchor 2026-08 --by category`. Aug $6,677.06 vs May–Jul avg $6,332.80: **+$344.26 (+5.4%)**. Shopping +$1,284.98, Food +$647.20, Dining +$278.42, Personal Transfers -$938.67, Rent & Housing -$492.93 (Aug $0), Utilities -$132.09, Business -$126.64, Subscriptions -$108.50.
4. `fin.py trend 2025-11..2026-08`. Monthly net spend ranged $1,966.05 (Apr) to $8,987.01 (Dec). Mean $6,177.90, median $6,274.94. Aug is +8.1% vs the mean.
5. `fin.py compare --a 2026-08 --b 2025-11..2026-07 --normalize monthly`. $6,677.06 vs $6,122.44/mo: **+$554.62 (+9.1%)**.
6. `fin.py compare 3m-avg --anchor 2026-08 --exclude-category "Personal Transfers"`. $3,861.06 vs $2,578.13: **+$1,282.93 (+49.8%)**.
7. `fin.py search --period 2026-08 --category Shopping`. 14 rows, $1,353.10. JB Hi-Fi $999.00 on 2026-08-31.
8. `fin.py search --period 2026-08 --category "Rent & Housing"`. 0 rows. `search --period 2026-05..2026-07 --category "Rent & Housing"`: 3 Clink debits (May $658, Jun $658, Jul $162.79), $1,478.79 in total.
9. `fin.py compare --a 2026-08 --b 2025-11..2026-07 --normalize monthly --exclude-category "Personal Transfers" --by category --top 6`. $3,861.06 vs $3,247.00/mo: **+$614.06 (+18.9%)**. Food $1,564.78 vs $764.09, Shopping vs $193.92, Dining $406.72 vs $195.38.
10. `fin.py breakdown 2026-08 --by payee --category Food`. Woolworths $643.39 (29 rows), Coles $276.88, No 1 Asian Mart $276.47 (1 row), KFL Convenience $241.56.
11. Wrote response.md and actions.md. No database writes and no --yes. changed: nothing.
