"""Read-only data-quality report for the finance tables. Never writes. Called by `fin.py doctor`.

Groups (each finding: severity, count, sample, fix):
  A stale data              last transaction older than 7 days
  B uncategorised           expense/income rows without a category
  C category type mismatch  Income row with an Expense category, or the reverse
  D possible duplicates     same date, type, amount and payee
  E payee defaults          payees without a Default Category (with a proposal when their rows agree)
  F transfers               transfers without a destination account (cannot tell savings from spending)
  G balances                negative balance on a checking/savings/cash account (missing income or accounts)
  H recurring flags         regular payments not flagged Recurring; flagged ones that look stopped
  I unused records          tags, categories, payees with no transactions; no budgets
  J structure               flat category tree (informational)
  K incoming transfers      'TRANSFER .. FROM ..' rows stored as Transfer, counted as money out by the balance formula
"""
import collections, datetime as dt

import findata as D
import fincalc as C


def finding(group, title, severity, items, fix, note=None, count=None):
    return dict(group=group, title=title, severity=severity, count=len(items) if count is None else count,
                sample=items[:10], items=items, fix=fix, note=note)


def run(stale_days=7):
    rows = D.load_txns(None, enrich_categories=True)
    cats, pays, accs, tags, buds = D.categories(), D.payees(), D.accounts(), D.tags(), D.budgets()
    cov = D.coverage()
    out = []

    age = (D.T.today() - cov["last"]).days if cov["last"] else None
    if age is not None and age > stale_days:
        out.append(finding("A", "data is %d days old (last transaction %s)" % (age, cov["last"]), "warn", [str(cov["last"])],
                           "import the latest bank statement; until then use --anchor %s for monthly windows" %
                           D.add_months(cov["last"].replace(day=1), -1 if cov["last"].month == (cov["last"] + dt.timedelta(days=1)).month else 0).strftime("%Y-%m"),
                           count=1))

    unc = [t for t in rows if t.type != "Transfer" and not t.category_id]
    if unc:
        out.append(finding("B", "uncategorised income/expense rows", "warn",
                           ["%s %s %s %s" % (t.id, t.date, t.description[:40], C.r2(t.amount)) for t in unc],
                           "fin.py categorize --to <category> --uncategorized [--payee P] (dry run first)"))

    mis = [t for t in rows if t.type in ("Income", "Expense") and t.category_type and t.category_type != t.type]
    if mis:
        out.append(finding("C", "rows whose category type differs from the row type", "warn",
                           ["%s %s %s %s: %s row, %s category %s" % (t.id, t.date, t.description[:30], C.r2(t.amount), t.type, t.category_type, t.category)
                            for t in mis],
                           "fin.py categorize --to <matching category> --ids <id> (or change the row Type in Teable if the type is wrong)"))

    dups = [d for d in C.duplicates(rows) if not d["reversed_by"]]  # a matching reversal means the bank already corrected it
    if dups:
        out.append(finding("D", "possible duplicate groups (same date, type, amount, payee)", "info",
                           ["%s %s %s %s x%d: %s" % (d["date"], d["type"], d["amount"], d["payee"][:30], d["count"], " ".join(d["ids"])) for d in dups],
                           "check each group against the bank statement; remove a true duplicate with fin.py delete <id> (keep one)",
                           note="repeat purchases on the same day are common; only the user can confirm"))

    by_payee = collections.defaultdict(list)
    for t in rows:
        if t.payee_id and t.type == "Expense":
            by_payee[t.payee_id].append(t)
    props, nodef = [], []
    for pid, p in pays.items():
        if p["default"]:
            continue
        txs = by_payee.get(pid, [])
        cats_used = collections.Counter(t.category for t in txs if t.category)
        if txs and len(cats_used) == 1:
            props.append("%s -> %s (%d rows)" % (p["name"], next(iter(cats_used)), len(txs)))
        elif txs:
            nodef.append("%s: %s" % (p["name"], ", ".join("%s %d" % kv for kv in cats_used.most_common(3))))
    if props or nodef:
        out.append(finding("E", "payees without a Default Category", "info", props + nodef,
                           "fin.py payee-default <payee> --category <category> (proposals list the one category its rows already use)",
                           note="%d with a clear proposal, %d mixed" % (len(props), len(nodef)), count=len(props) + len(nodef)))

    inc = [t for t in rows if C.is_incoming(t)]
    if inc:
        out.append(finding("K", "incoming transfers stored as Transfer (the Current Balance formula counts them as money out)", "warn",
                           ["%s %s %s %s" % (t.id, t.date, t.description[:40], C.r2(t.amount)) for t in inc],
                           "add the source account in finance_Accounts, then on each row set Account = that account and Transfer Account = "
                           "this one (Teable; fin.py has no account editor). Until then fin.py balance shows the corrected figure",
                           note="%s in total; balance understated by twice that" % C.r2(sum(t.amount for t in inc))))
    tr = [t for t in rows if t.type == "Transfer" and not t.transfer_account and not C.is_incoming(t)]
    if tr:
        dest = collections.Counter(t.description.split(" ")[0] + " " + " ".join(t.description.split(" ")[1:3]) for t in tr)
        out.append(finding("F", "transfers without a destination account", "info",
                           ["%s x%d" % kv for kv in dest.most_common(10)],
                           "if a destination is your own account, add it in finance_Accounts and set Transfer Account in Teable; otherwise leave as external",
                           note="%s in total; not counted as cost (D-1)" % C.r2(sum(t.amount for t in tr)), count=len(tr)))

    for acc in accs.values():
        if acc["type"] in ("Checking", "Savings", "Cash") and acc["balance"] is not None and acc["balance"] < 0:
            fixed = C.r2(acc["balance"] + 2 * sum(t.amount for t in inc if t.account_id == acc["id"]))
            out.append(finding("G", "negative Current Balance on %s" % acc["name"], "warn",
                               ["Current Balance %s; corrected for incoming transfers %s" % (C.r2(acc["balance"]), fixed)],
                               "fix group K first; if still negative, import the missing income/accounts or check the Opening Balance", count=1))

    rec = C.recurring(rows, cov["last"]) if cov["last"] else []
    unflagged = [r for r in rec if r["inferred"] and not r["flagged"] and r["status"] != "stopped"]
    stopped = [r for r in rec if r["flagged"] and r["status"] == "stopped"]
    if unflagged or stopped:
        out.append(finding("H", "recurring flags out of date", "info",
                           ["not flagged: %s %s %s/month" % (r["payee"], r["cadence"], r["typical"]) for r in unflagged] +
                           ["looks stopped: %s (last %s)" % (r["payee"], r["last"]) for r in stopped],
                           "set Recurring in Teable (fin.py recurring --all shows the evidence); stopped ones need no change unless cancelled",
                           count=len(unflagged) + len(stopped)))

    used_tags = {x for t in rows for x in t.tags}
    unused = ["tag: %s" % t["name"] for t in tags.values() if t["name"] not in used_tags]
    cat_used = {t.category_id for t in rows}
    unused += ["category: %s" % c["path"] for c in cats.values() if c["id"] not in cat_used]
    pay_used = {t.payee_id for t in rows}
    unused += ["payee: %s" % p["name"] for p in pays.values() if p["id"] not in pay_used]
    if not buds:
        unused.append("budgets: none set")
    if unused:
        out.append(finding("I", "unused records", "info", unused,
                           "tags: fin.py tag <tag> ...; budgets: fin.py budget-suggest then budget-set; remove unused categories/payees in Teable only if not needed"))

    notes = []
    if cats and not any(c["parent"] for c in cats.values()):
        notes.append("category tree is flat (no Parent Category); breakdown --by parent equals --by category")
    if notes:
        out.append(finding("J", "structure", "info", notes, "optional: group categories under parents in Teable", count=len(notes)))

    rank = {"warn": 0, "info": 1}
    out.sort(key=lambda f: (rank[f["severity"]], f["group"] if f["group"] != "K" else "B0"))
    return dict(rows=len(rows), coverage=dict(first=str(cov["first"]), last=str(cov["last"]), age_days=age), findings=out)
