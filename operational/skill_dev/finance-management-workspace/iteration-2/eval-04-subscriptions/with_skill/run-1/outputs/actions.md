# Actions log — eval-04-subscriptions (with_skill, run-1)

1. Read `skill_dev/finance-management/SKILL.md`. The mapping is "subscriptions, bills, regular transfers" → `recurring [--all]`. No references were needed.
2. `python3 skill_dev/finance-management/scripts/fin.py recurring` (from repo root)
   - Coverage: 1102 rows, data 2025-10-30..2026-09-18 (17 days old). Status is judged as of 2026-09-18.
   - Bills and subscriptions: 8 active, $397.31 per month, $4,767.68 per year
     (Allianz $1,428.36/yr; Allianz ABS $1,407.72/yr; Dodo $935.88; ahm $426.00; Amaysim 4-weekly $326.12; Amazon Prime $119.88; NestJS $88.44; Retell AI $35.28)
   - Regular transfers and payments to people: Aiyun Yu (Personal Transfers), $2,816.00/month, $33,792.00/yr, 1 active
   - Other annual or irregular bills since 2025-10-01: 16 payees, $6,124.12 in total (largest: Doncaster Primary School $1,532.00, Wyndham City Council $1,199.27, VicRoads $955.48)
   - 8 stopped items hidden
3. `python3 skill_dev/finance-management/scripts/fin.py recurring --all`
   - Stopped items: Clink $658/mo (last paid 2026-07-14), Lumo Energy $175, Telstra $93, Postiz $45.49, Twinkl $19.99, Cloudflare $15.74, Retell AI (old) $4.69; transfer TO WANG JUNYANG $2,357.36/mo (Transfer type, stopped 2026-07-09)
4. `python3 skill_dev/finance-management/scripts/fin.py search allianz --period 3m`
   - Checked whether the two Allianz lines are duplicates: 6 rows, two separate monthly charges ($119.03 "TO ALLIANZ INSURE 601078W…" and $117.31 "ALLIANZ INSURANCE ABS SYDNEY"). They are separate, likely two policies.
5. `mkdir -p .../outputs`, then wrote response.md and fixed it after review. Removed two hand-computed sums (an Allianz combined figure and a grouped health total) to follow core rule 1, and corrected the Vercel wording to match the data.
6. Wrote actions.md (this file).

Database writes: none. No `--yes` and no MCP writes.
