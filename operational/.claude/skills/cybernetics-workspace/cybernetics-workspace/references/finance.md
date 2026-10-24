# Finance (cybernetics-data)

Base `bseJEuE54y5caWO0Xc8`. Six tables that form a small double-entry-style ledger. Everything is in `$`, dates are Australia/Melbourne.

## Contents
- Data model at a glance
- Table and field IDs
- Rules that make the numbers right
- Workflows: add a transaction, transfer, budget check, balance, monthly summary, new payee/category
- Guardrails

## Data model at a glance

```
finance_Accounts  <-- Account / Transfer Account --  finance_Transactions  --> Category (finance_Categories, hierarchical)
                                                          |    |                       ^
                                                          |    +--> Payee (finance_Payees) -- Default Category
                                                          +--> Tags (many-many, finance_Tags)
                                                          +--> Budget (finance_Budgets: one row per Month + Category)
```

Balances and budget results are **computed by the database** from linked transactions. Read them; do not recalculate them by hand and never try to write them.

## Table and field IDs

### `finance_Transactions` - `tblylfLkXFkYH2qB0ZQ`
| Field | ID | Type / options |
|---|---|---|
| Description (primary) | `fldRZcBYKr6w2GWw5lm` | text |
| Date | `fldZIgdLJ79xoDQK5u4` | date `YYYY-MM-DD` |
| Type | `fldIqRcX7gZ1zn9Kmz0` | Income / Expense / Transfer |
| Amount | `flde1ox2n7Q30UUP938` | number, **always positive** |
| Recurring | `fldAiqG7oB0DCPeDL7K` | checkbox |
| Recurring Frequency | `fldTMF1faN48Lrd3vS4` | Weekly / Monthly / Yearly |
| Receipt | `fldlgu9WLxc0FznWjO5` | attachment (not writable via these tools) |
| Notes | `fldW2RsBfTxd362FjfO` | long text |
| Account | `fldcg0wB2iVE8DZCVHm` | link -> Accounts (money leaves/enters here) |
| Transfer Account | `fldIeT7aNuRjEAVlyqL` | link -> Accounts (destination, Transfers only) |
| Category | `fldlU2BpJBZFcNcFhom` | link -> Categories |
| Payee | `fld8WNu5jDIr55RNkSu` | link -> Payees |
| Tags | `fldXRiV3NxrspHNLQFO` | link -> Tags (many-many, array) |
| Budget | `fldVYJYqgs9p2GQSf9a` | link -> Budgets |
| *Scope* | `fldV9EFPhFI8W0OOMbF` | computed (Personal / Business) |
| *Signed Amount* | `flddkw1CxatR4zrvXd0` | computed formula |

### `finance_Accounts` - `tblJLklwpGwbrfDlwIz`
| Field | ID | Type / options |
|---|---|---|
| Name (primary) | `fldSzvd0NAglB9qhsp1` | text |
| Scope | `fldZFxk5O8qT6AF6QV2` | Personal / Business |
| Type | `fldaZgFxywk8cZT9l8V` | Checking / Savings / Credit Card / Cash / Investment / Mortgage |
| Institution | `fldEHOdmX1nYcAaaybH` | text |
| Opening Balance | `fldiOOafvV1UPDJtV1f` | number |
| Opening Balance Date | `fldBjBPMxjYpGxs0yJ5` | date |
| Active | `fldRyzp4jLRtGqUd6gu` | checkbox (use instead of is_active) |
| *Own Txn Total* / *Incoming Transfer Total* / *Net Activity* / *Current Balance* | `fldxGuTHGj0kFXhVEQ0` / `fldShPCh4zNp2NRgBYo` / `fld04GdZkCiVlkrABed` / `fldSTUAw8v0UMcTivzf` | computed |

### `finance_Categories` - `tblp2Jvb2g90PN3fX4d`
| Field | ID | Type / options |
|---|---|---|
| Name (primary) | `flddvHdoGLLLyFYTXlM` | text |
| Type | `fldBazKuxdsorHnlCmZ` | Income / Expense |
| Scope | `flddiHU2kAnTeZG49P4` | Personal / Business / Shared |
| Parent Category | `fldmknXtvhmpIUmjTcP` | link -> Categories (self) |
| *Parent Name*, *Full Path* | `fldYtNHk7iAhQlQHQvd`, `fldZZlGOiOHRb84DjDV` | computed, "Parent > Child" |

### `finance_Payees` - `tblpyC3PfoG0DN8dQ2t`
| Field | ID | Type / options |
|---|---|---|
| Name (primary) | `fldnbT296ypPXkiJkkF` | text |
| Type | `fldJ8YwtDNxCKZvPNVO` | Vendor / Client / Employer / Store / Person / Other |
| Scope | `fldf7p7Ub27gXLzi7nP` | Personal / Business / Both |
| Default Category | `fld6XnWnCCu7GsWfJzh` | link -> Categories |

### `finance_Tags` - `tblhOQKXpSzr0Ezh8rR`
| Field | ID | Type / options |
|---|---|---|
| Name (primary) | `fldie2h6YM3fA6WPH0Z` | text |
| Color | `fldZQDvslg2GJfBTE9K` | Light Blue / Blue / Deep Blue / **Organge** (sic, typo in the option) / Green / Deep Red / Light Green |

### `finance_Budgets` - `tblDk3iXFz5YiYUkwz6`
| Field | ID | Type / options |
|---|---|---|
| Month (primary) | `fldzRSk36rF2iLqoc1A` | date shown as `YYYY-MM`; store the 1st of the month |
| Planned Amount | `fldJXYFV5eXNnALW40c` | number |
| Category | `fldfCZXAsjS3nEM0MGW` | link -> Categories |
| *Scope*, *Actual Spent*, *Variance*, *% Used* | `fldWtNgqZiz6JcSAUkB`, `fldCEyMLCffN6AU15n9`, `fldBbkdGPNoAwaD1nMc`, `fldYGBsE6yNmObjpM3B` | computed |

## Rules that make the numbers right

- **Enter Amount as a positive number, always.** The sign comes from Type: `Signed Amount` is negative for Expense and Transfer, positive for Income. Entering a negative amount double-flips it.
- **Type = Transfer needs both Account (source) and Transfer Account (destination).** The destination's balance rises through its *Incoming Transfer Total*; the source falls through *Own Txn Total*. Do not also create a second, mirrored transaction; that would double-count.
- **Category type should match transaction type** (Expense category for Expense, Income category for Income). Transfers normally have no category.
- **Budget results only count linked transactions.** *Actual Spent* is a rollup over the transactions linked in the Budget field, so an expense affects a budget only if its Budget link points at that month's row for that category. When adding an expense, look for a matching budget row (same month, same category) and link it; if none exists, say so instead of silently skipping.
- **Budgets are one row per (Month, Category).** Before creating one, check it doesn't already exist. Store Month as the first day of the month.
- **Scope is inherited or computed** on transactions and budgets. Set Scope on accounts, categories and payees; don't try to write it on transactions/budgets.
- **Recurring is a flag, not an automation.** Setting Recurring + Frequency records intent; nothing creates future rows automatically. Don't promise that it will.
- **Never edit an Opening Balance or Opening Balance Date to "fix" a balance** without saying exactly what changes and getting confirmation.

## Workflows

**Add a transaction** ("$45.20 at Woolworths yesterday, groceries, on my everyday account")
1. Parse: Type (default Expense unless clearly income/transfer), Amount (positive), Date (resolve relative dates against today), Description.
2. Resolve links with `query_records` + `search`: Account, Payee, Category, optional Tags, matching Budget. Payee's *Default Category* can supply the category if the user didn't state one; say you used it.
3. If Account is ambiguous (several matches), ask which one. If a Payee/Category/Tag doesn't exist, offer to create it; do not silently create.
4. Create the record. Read it back and show: Date, Description, Type, Amount, Account, Payee, Category, Signed Amount.

**Transfer** ("moved $500 from Savings to Checking")
- Type = Transfer, Amount = 500, Account = source, Transfer Account = destination. One row. Read back both accounts' *Current Balance* if the user cares about the effect.

**Budget check** ("how am I going on groceries this month?")
- Find the Budget row for the month + category and report *Planned Amount*, *Actual Spent*, *Variance*, *% Used*. If it's missing, say there's no budget row and offer to create one.

**Balance** ("what's in my savings?")
- `query_records` on Accounts with `search`, projection = Name, *Current Balance*. Report the computed value and note the opening balance date it's built from.

**Monthly / category summary**
- No filter argument exists on `query_records`: check `list_views` for an existing month/category view; otherwise page transactions with a `projection` of Date, Type, Amount, Signed Amount, Category, Account, and calculate. State the row count and date range used. Sum *Signed Amount* for net figures; sum *Amount* for gross by Type.

**Create a payee or category (after confirmation)**
- Payee: Name, Type, Scope, and a Default Category if known. Category: Name, Type, Scope, and Parent Category if it's a sub-category (check *Full Path* to avoid duplicates like "Food > Groceries" vs "Groceries").

**Correct a mistake**
- Update the single transaction. For a wrong Type/Amount, show old vs new values and the effect on *Signed Amount*.

## Guardrails

- Finance tables have no `is_active`/`deleted_at`. Do not delete transactions without an explicit instruction; deletion changes balances and budget rollups.
- Bulk imports (e.g. a CSV of statements): show a preview of the first few mapped rows, count the total, check for likely duplicates (same Date + Amount + Payee) against existing rows, then create in batches after confirmation.
- Don't give investment, tax or legal advice from this data. Report figures; note you're not a financial advisor if the user asks for a recommendation.
