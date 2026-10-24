# Your subscriptions and regular bills

**Source:** all 1,102 transactions in `finance_Transactions` (ANZ Access Advantage). They run from 30 Oct 2025 to **18 Sep 2026**, the last import. I didn't rely only on the `Recurring` checkbox, because it was only ever set on transactions up to April 2026. Instead I looked for payees charged on a regular cycle. "Per year" is the current charge × how often it bills. For bills that come irregularly or once a year, it's what you actually paid in the last 12 months. All amounts are AUD.

## Bottom line

| Group | Per year | Per month |
|---|---:|---:|
| Monthly bills and subscriptions (excluding rent) | **$4,766** | $397 |
| Annual and irregular bills | **$3,477** | $290 |
| **Bills and subscriptions total** | **$8,242** | **$687** |
| Rent (likely; see note) | $33,792 | $2,816 |
| **Including rent** | **$42,034** | **$3,503** |

Pure software and media subscriptions come to about **$962/yr**. Only about $243 of that is billed monthly. The rest is annual or irregular charges (Claude, JetBrains, Vercel, Cloudflare, Apple).

---

## 1. Active monthly bills and subscriptions

| What | Payee | Current charge | Cycle | Per year | Last charged |
|---|---|---:|---|---:|---|
| Rent (likely) * | Aiyun Yu | $2,816.00 | monthly, around the 1st | $33,792.00 | 30 Aug 2026 |
| Insurance policy 1 (601078W…) | Allianz | $119.03 | monthly, around the 6th | $1,428.36 | 7 Sep 2026 |
| Insurance policy 2 ("ABS") | Allianz | $117.31 | monthly, around the 14th | $1,407.72 | 14 Sep 2026 |
| Internet | Dodo | $77.99 | monthly, around the 10th | $935.88 | 10 Sep 2026 |
| Health insurance | ahm | $35.50 | monthly, around the 19th | $426.00 | 19 Aug 2026 |
| Mobile | Amaysim | $25.00 | every 28 days (13 per year) | $325.00 | 7 Sep 2026 |
| Amazon Prime | Amazon | $9.99 | monthly, around the 24th | $119.88 | 23 Aug 2026 |
| NestJS (US$5) | NestJS | about $7.29 | monthly, around the 6th | about $87 | 7 Sep 2026 |
| Retell AI (US$2) | Retell AI | about $2.94 | monthly, around the 10th | about $35 | 10 Sep 2026 |
| **Subtotal excluding rent** | | | | **$4,765.53** | |

\* This is $2,816/month to Aiyun Yu, categorised as *Personal Transfers*. It works out to exactly $650/week × 52 ÷ 12, which looks like rent on your Doncaster home. If it isn't rent, take it out of the totals.

## 2. Annual and irregular bills (last 12 months)

| What | Payee | Paid in last 12 months | Pattern | Next likely |
|---|---|---:|---|---|
| Council rates (15 Seabird Dr rental) | Wyndham City Council | $1,199.27 | 1 payment, 26 Nov 2025 | Rates instalments start around 30 Sep. None seen yet this year. |
| Car registration | VicRoads | $875.48 | annual, 27 Jan 2026 | Jan 2027. You also got a $174.26 rego rebate in June. |
| Water | Yarra Valley Water | $440.54 | quarterly, varies ($41, $139, $260) | Probably around Oct 2026 |
| Claude subscription | Anthropic | $340.00 | 1 charge, 1 Jul 2026 | Looks like an annual plan, so Jul 2027 |
| Car insurance (MOTP policy) | CGU | $241.92 | 1 charge, 24 Jul 2026 | Probably Jul 2027 |
| JetBrains licences | JetBrains | $188.59 | $134.37 in Jan + $54.22 in Feb | Jan–Feb 2027 |
| Vercel (about US$21–23 each) | Vercel | $129.43 | 4 charges, irregular (Jan, Apr, Jul, Sep) | At this pace it could be about $165/yr |
| Domains, probably | Cloudflare | $31.48 | 2 × US$10.46 (Dec, Apr) | Dec 2026, Apr 2027 |
| Apple subscription | Apple | $29.99 | 1 charge, 10 Feb 2026 | Feb 2027, if it's annual |
| **Subtotal** | | **$3,476.70** | | |

**Family/school fees** aren't in the totals above: Doncaster Primary $1,532 (Feb), Eastern Chinese Language School $850 (Jan), Doncaster Kindergarten $75. That's $2,457 for the year. Adding them brings everything to about **$44,491/yr**.

## 3. Charges that have stopped (not in the totals)

| What | Was | Last charged | Notes |
|---|---:|---|---|
| Clink direct debit (*Rent & Housing*) | $658/mo (about $7,896/yr) | 14 Jul 2026 (final $162.79) | Looks paid out or closed |
| Lumo Energy (electricity) | $175/mo (about $2,100/yr) | 2 Jan 2026 | **I can't see any electricity or gas bill after this.** If you're paying one from another account or card, it's missing from this data. |
| Telstra | $93/mo | 29 Dec 2025 | Stopped |
| Postiz (US$29) | about $45/mo | 18 Dec 2025 | Stopped |
| Twinkl | $19.99/mo | 11 Feb 2026 | Stopped |
| Second NestJS subscription | about $7.40/mo | 16 Apr 2026 | You had two US$5 subscriptions until April; now there's one |

## Things worth checking

- **Two Allianz policies at about $236/month together ($2,836/yr).** This is your biggest bill after rent. Check what each one covers. One may be landlord insurance on the Point Cook rental.
- **Electricity and gas.** Nothing since Lumo stopped in January.
- **Retell AI charged twice in June** (1 Jun and 10 Jun, about $2.90 each).
- **OpenAI $16.08 on 17 Aug 2026** (US$11). There's only one charge so far. If it's a new subscription it'll show again around 17 Sep; if not, it was probably a one-off API top-up.
- **Not counted:** a fixed **$2,357.36/month transfer to "Wang Junyang"**, recorded as a *Transfer*. It was paid monthly Nov–May and in July; June, Aug and Sep are missing. A fixed amount like that looks like a loan or mortgage repayment. If it is one, it's another **$28,288/yr**.
- **Your data's recurring markers are out of date.** The `Recurring` box is only ticked on 71 transactions, all from April 2026 or earlier. The "Recurring / Subscription" tag isn't used on any transaction.

Do you want me to tidy that up? I would tick `Recurring` (Monthly) and add the "Recurring / Subscription" tag on the May–Sep 2026 charges from Allianz, ahm, Dodo, Amaysim, Amazon Prime, NestJS and Retell AI. I'll show you the full list of records before I change anything.
