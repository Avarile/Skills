**Your ANZ Access Advantage (2992-86276) balance is about $979.54. That figure is as of 18 Sep 2026, the date of your last recorded transaction.** It's my own calculation. The database's "Current Balance" field shows something different and wrong.

### Why you shouldn't trust the database's own figure

The `Current Balance` field on the account shows **-$49,140.46**. That's wrong for an everyday account, and the cause is a bookkeeping error:

- The `Signed Amount` formula makes every **Transfer** negative, as if money always left the account.
- 22 of your 72 transfers are actually money **coming in** from your other account ("TRANSFER xxxxxx FROM 807590005"). Together they add up to **$25,060.00**.
- So those inflows are subtracted when they should be added. That makes the balance $50,120.00 too low (2 × $25,060).

| | Amount |
|---|---|
| Opening balance (29 Oct 2025) | $7,932.94 |
| Income (51 txns) | +$179,367.72 |
| Expenses (979 txns) | -$63,346.24 |
| Transfers out (50 txns) | -$148,034.88 |
| Transfers in (22 txns) | +$25,060.00 |
| **Corrected balance (18 Sep 2026)** | **$979.54** |

### Caveats

1. **The data is 17 days old.** Nothing has been recorded after 18 Sep 2026, so anything since then (salary, rent, spending) is missing. For today's real balance, check the ANZ app.
2. **Only this one account is in Teable.** The two accounts you transfer to and from (…013664733557893 and …013148807590005, probably savings) aren't set up, so I can't give you a total cash position.
3. **I checked for duplicates.** There are 8 groups of identical same-day transactions (e.g. two "PAYMENT FROM MRS XIAOLAN WANG" of $5,000 on 2 Jan, and a $19.05 Woolworths charge that was later reversed). They look like real repeated transactions, not import errors, so I left them in. If any are duplicates, the balance changes by that amount.
4. The opening balance of $7,932.94 is taken as recorded. I couldn't check it against a statement.

### Want me to fix the stored balance?

I haven't changed anything. Here is what I'd do, in the way the table is already designed to work. The `Incoming Transfer Total` rollup adds the amount of any transaction where an account is the **Transfer Account**.

1. Add the savings account …013148807590005 (and …013664733557893 if you still use it) to `finance_Accounts`. I'd need its opening balance and date from you.
2. For the 22 "TRANSFER … FROM 807590005" records: set **Account** = the savings account and **Transfer Account** = ANZ Access Advantage. They then count as +$25,060 into checking and as outflows from savings.
3. For the outgoing "TRANSFER … TO 0131488…/0136647…" records: set **Transfer Account** = the matching savings account, so its balance is right too.
4. Then re-read `Current Balance`. Checking should show $979.54.

**Shall I go ahead with steps 1–3? If so, what are the opening balance and date for the savings account(s) ending 807590005 (and 664733557893)?**
