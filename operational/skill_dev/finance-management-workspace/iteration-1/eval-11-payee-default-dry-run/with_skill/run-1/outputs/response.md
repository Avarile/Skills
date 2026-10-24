Ready to set **Food** as Woolworths' default category. Nothing has been written yet. Here's the dry run:

```
Payee Woolworths: default category (none) -> Food
  0 of its 234 transaction(s) have another or no category
DRY RUN: nothing written.
```

What this changes:
- **Woolworths has no default category right now.** After this it will be Food.
- **Your existing rows don't need any changes.** All 233 Woolworths purchases (Oct 2025 to Sep 2026) are already in Food, so no bulk recategorise is needed.
- **One row will stay as it is.** A $19.05 Woolworths refund on 2026-08-28 is an Income row in **Refunds**. That's correct, because refunds are subtracted from net spend. The default only applies to expense rows, so this refund isn't touched.
- **Where the default is used:** any Woolworths transaction added without a category will go to Food. Bank-statement import isn't built yet, so imported rows won't pick it up automatically. To keep those consistent later, run `categorize --to Food --payee Woolworths --type Expense`. The `--type Expense` part keeps that refund out.

A file will be saved so this can be undone (`fin.py undo`).

Should I go ahead and set Woolworths' default category to Food?
