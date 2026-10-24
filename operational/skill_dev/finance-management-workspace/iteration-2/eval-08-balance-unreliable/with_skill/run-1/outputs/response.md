**$979.54** in your ANZ Access Advantage account (2992-86276). That's the balance as of your **last recorded transaction on 18 Sep 2026**, not today.

**Before you rely on it:**
- **The data is 17 days old.** Records come in from bank statements, and nothing after 18 Sep has been imported yet, so anything from 19 Sep to today is missing. Check the ANZ app or online banking for your real balance today.
- **Only one account is tracked.** This is the ANZ Access Advantage account only. Other accounts, savings or cards aren't included.
- **Don't use the "Current Balance" field in the table. It's wrong.** It shows **-$49,140.46**. That's because 22 incoming transfers ("TRANSFER .. FROM 807590005", $25,060 in total) are stored as *Transfer*, and the formula counts every Transfer as money going out. The $979.54 figure counts those transfers as money coming in. The two figures match up to Feb 2026 and only drift apart after that.

**How the balance has moved (month-end, corrected):**

| Month end | Balance |
|---|---|
| Oct 2025 (opening $7,932.94 on 29 Oct) | $4,050.29 |
| Dec 2025 | $5,963.58 |
| Feb 2026 | $2,964.26 |
| Apr 2026 | $6,104.53 |
| Jun 2026 | $2,041.69 |
| Jul 2026 | $853.81 |
| Aug 2026 | $383.67 |
| Sep 2026 (to 18 Sep) | $979.54 |

The balance has mostly gone down since April, and it's been under $1,000 for the last three months.

Want me to run `doctor` (group K) to preview a fix for the 22 misclassified transfers? Then the Current Balance field would show the right number. That would only be a preview; nothing changes until you say so.
