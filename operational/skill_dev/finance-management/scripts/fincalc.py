"""Pure finance calculations over findata.Txn rows (no IO). Definitions: references/metrics.md.

    import findata as D, fincalc as C
    p12 = D.resolve_period("12m")
    rows = D.load_txns(C.span(p12, D.resolve_period("mtd")), enrich_categories=True)
    C.summarize(rows)                         # income, expense, refunds, net spend, transfers, savings rate
    C.cost_windows(rows, today=...)           # 1 / 3 / 6 / 12 complete months + MTD, totals and monthly averages
    C.monthly_series(rows, p12, group_by="category")
    C.compare(rows_a, pa, rows_b, pb, group_by="category")

Cost (D-1/D-2): Expense amounts minus Refunds; Transfers only with include_transfers. Every function that
returns money rounds to cents at the end, never in between.
"""
import collections, datetime as dt, re, statistics

import findata as D

REFUND_CATEGORIES = {"refunds"}


def is_refund(t):
    return t.type == "Income" and (t.category or "").split(" > ")[-1].strip().lower() in REFUND_CATEGORIES


def is_internal(t):
    """Transfer between two tracked accounts: moves money, never cost or income."""
    return t.type == "Transfer" and bool(t.transfer_account)


_FROM, _TO = re.compile(r"\bFROM\b"), re.compile(r"\bTO\b")


def is_incoming(t):
    """A Transfer that brought money IN from an untracked account ("TRANSFER 509564 FROM 807590005").
    The data model has no inbound type: `Signed Amount` makes every Transfer negative, so these rows are
    counted as outflows by the Accounts formulas. Detected from the bank description (verified 2026-10-05:
    22 rows, $25,060)."""
    if t.type != "Transfer" or t.transfer_account:
        return False
    d = t.description.upper()
    return bool(_FROM.search(d)) and not _TO.search(d)


def is_outgoing(t):
    """External transfer out: a Transfer that is neither internal nor incoming."""
    return t.type == "Transfer" and not is_internal(t) and not is_incoming(t)


def cost_value(t, include_transfers=False):
    """Contribution of one row to cost (net spend): +Expense, -Refund, +external Transfer if asked, else 0."""
    if t.type == "Expense":
        return t.amount
    if is_refund(t):
        return -t.amount
    if include_transfers and is_outgoing(t):
        return t.amount
    return 0.0


def income_value(t):
    return t.amount if t.type == "Income" and not is_refund(t) else 0.0


def r2(x):
    return round(x + 0.0, 2) if x is not None else None


def span(*periods):
    """Smallest Period covering all given periods (one fetch for several windows)."""
    return D.Period(min(p.start for p in periods), max(p.end for p in periods), " + ".join(p.label for p in periods))


def within(txns, period):
    return [t for t in txns if period.start <= t.date < period.end]


# ---------- totals ----------

def summarize(txns, period=None, include_transfers=False):
    exp = sum(t.amount for t in txns if t.type == "Expense")
    ref = sum(t.amount for t in txns if is_refund(t))
    inc = sum(income_value(t) for t in txns)
    tr_ext = sum(t.amount for t in txns if is_outgoing(t))
    tr_in = sum(t.amount for t in txns if is_incoming(t))
    tr_int = sum(t.amount for t in txns if is_internal(t))
    net_spend = exp - ref + (tr_ext if include_transfers else 0)
    out = dict(income=r2(inc), expense=r2(exp), refunds=r2(ref), net_spend=r2(net_spend),
               transfers_out=r2(tr_ext), transfers_in=r2(tr_in), internal_transfers=r2(tr_int),
               net_cash_flow=r2(inc + ref + tr_in - exp - tr_ext),
               savings_rate=r2(100 * (inc - net_spend) / inc) if inc else None,
               count=len(txns), count_by_type=dict(collections.Counter(t.type for t in txns)),
               include_transfers=include_transfers)
    if period:
        out.update(period=period.to_dict(), monthly_avg=r2(net_spend / period.months) if period.months else None,
                   daily_avg=r2(net_spend / period.days) if period.days else None)
    return out


def cost(txns, period, include_transfers=False):
    rows = within(txns, period)
    tot = sum(cost_value(t, include_transfers) for t in rows)
    return dict(window=period.label, start=period.start.isoformat(), end=period.last.isoformat(), months=round(period.months, 2),
                net_spend=r2(tot), expense=r2(sum(t.amount for t in rows if t.type == "Expense")),
                refunds=r2(sum(t.amount for t in rows if is_refund(t))),
                monthly_avg=r2(tot / period.months) if period.months else None,
                daily_avg=r2(tot / period.days) if period.days else None,
                count=sum(1 for t in rows if cost_value(t, include_transfers)))


def window_periods(windows=(1, 3, 6, 12), today=None, anchor=None, mtd=True):
    ps = [D.resolve_period("%dm" % n, today=today, anchor=anchor) for n in windows]
    if mtd and not anchor:
        ps.append(D.resolve_period("mtd", today=today))
    return ps


def cost_windows(txns, windows=(1, 3, 6, 12), today=None, anchor=None, include_transfers=False, mtd=True):
    """Cost for each trailing window of complete months (D-3), plus month-to-date. `txns` must cover the
    widest window (fetch once with span(*window_periods(...)))."""
    return [cost(txns, p, include_transfers) for p in window_periods(windows, today, anchor, mtd)]


# ---------- grouping and series ----------

def key_fn(group_by):
    keys = {
        "category": lambda t: t.category or ("(transfer)" if t.type == "Transfer" else "(uncategorised)"),
        "parent": lambda t: (t.category or "(uncategorised)").split(" > ")[0],
        "payee": lambda t: t.payee or "(no payee)",
        "account": lambda t: t.account or "(no account)",
        "scope": lambda t: t.scope,
        "type": lambda t: t.type,
        "month": lambda t: t.date.strftime("%Y-%m"),
        "weekday": lambda t: t.date.strftime("%a"),
        "description": lambda t: t.description,
    }
    if group_by == "tag":
        return None
    if group_by not in keys:
        raise ValueError("unknown group %r; use %s, tag" % (group_by, ", ".join(keys)))
    return keys[group_by]


def group_values(txns, group_by, value=cost_value, include_transfers=False):
    """{group: (total, count)} for rows with a non-zero value. Tags: a row counts under each of its tags."""
    out = collections.defaultdict(lambda: [0.0, 0])
    kf = key_fn(group_by)
    for t in txns:
        v = value(t, include_transfers) if value is cost_value else value(t)
        if not v:
            continue
        for k in ((t.tags or ("(untagged)",)) if group_by == "tag" else (kf(t),)):
            out[k][0] += v
            out[k][1] += 1
    return out


def months_in(period):
    m, out = D.month_start(period.start), []
    while m < period.end:
        out.append(m.strftime("%Y-%m"))
        m = D.add_months(m, 1)
    return out


def monthly_series(txns, period, group_by=None, include_transfers=False, top=None):
    """Month x group matrix of cost, zero-filled. Returns {months, series: {group: [..]}, total: [..]}.
    `top` keeps the N largest groups and folds the rest into "(other)"."""
    months = months_in(period)
    idx = {m: i for i, m in enumerate(months)}
    series = collections.defaultdict(lambda: [0.0] * len(months))
    total = [0.0] * len(months)
    kf = key_fn(group_by) if group_by and group_by != "tag" else None
    for t in within(txns, period):
        v = cost_value(t, include_transfers)
        if not v:
            continue
        i = idx[t.date.strftime("%Y-%m")]
        total[i] += v
        if group_by:
            for k in ((t.tags or ("(untagged)",)) if group_by == "tag" else (kf(t),)):
                series[k][i] += v
    if top and len(series) > top:
        keep = sorted(series, key=lambda k: -sum(series[k]))[:top]
        other = [sum(series[k][i] for k in series if k not in keep) for i in range(len(months))]
        series = {k: series[k] for k in keep}
        series["(other)"] = other
    order = sorted(series, key=lambda k: (k == "(other)", -sum(series[k])))
    return dict(months=months, series={k: [r2(v) for v in series[k]] for k in order}, total=[r2(v) for v in total])


def rolling_avg(values, n=3):
    out = []
    for i in range(len(values)):
        w = values[max(0, i - n + 1):i + 1]
        out.append(r2(sum(w) / len(w)) if len(w) == n else None)
    return out


def trend_stats(values):
    """Simple description of a monthly series: mean, median, min, max, last vs mean, slope per month."""
    vals = [v or 0.0 for v in values]
    if not vals:
        return {}
    n = len(vals)
    xbar, ybar = (n - 1) / 2, sum(vals) / n
    den = sum((i - xbar) ** 2 for i in range(n))
    slope = sum((i - xbar) * (v - ybar) for i, v in enumerate(vals)) / den if den else 0.0
    return dict(mean=r2(ybar), median=r2(statistics.median(vals)), min=r2(min(vals)), max=r2(max(vals)),
                last=r2(vals[-1]), last_vs_mean_pct=r2(100 * (vals[-1] - ybar) / ybar) if ybar else None,
                slope_per_month=r2(slope))


# ---------- compare ----------

def compare(txns_a, period_a, txns_b, period_b, group_by=None, include_transfers=False, normalize=None):
    """A vs B (A is the period of interest, B the baseline). normalize: 'monthly' divides each side by its
    months (default when the periods differ in length), 'total' compares raw totals."""
    if normalize is None:
        normalize = "monthly" if abs(period_a.months - period_b.months) > 0.01 else "total"
    da = period_a.months if normalize == "monthly" else 1
    db = period_b.months if normalize == "monthly" else 1

    def groups(txns, p):
        rows = within(txns, p)
        if not group_by:
            return {"total": [sum(cost_value(t, include_transfers) for t in rows), len(rows)]}
        return group_values(rows, group_by, include_transfers=include_transfers)

    ga, gb = groups(txns_a, period_a), groups(txns_b, period_b)
    out = []
    for k in set(ga) | set(gb):
        a, b = ga.get(k, [0.0, 0])[0] / da, gb.get(k, [0.0, 0])[0] / db
        out.append(dict(group=k, a=r2(a), b=r2(b), delta=r2(a - b), delta_pct=r2(100 * (a - b) / b) if b else None))
    out.sort(key=lambda x: -abs(x["delta"]))
    ta, tb = sum(v[0] for v in ga.values()) / da, sum(v[0] for v in gb.values()) / db
    return dict(a=period_a.to_dict(), b=period_b.to_dict(), normalize=normalize, group_by=group_by,
                total=dict(a=r2(ta), b=r2(tb), delta=r2(ta - tb), delta_pct=r2(100 * (ta - tb) / tb) if tb else None),
                rows=out)


def compare_preset(name, today=None, anchor=None):
    """Named comparisons -> (period_a, period_b). mom: last month vs the one before; yoy: last month vs the
    same month a year earlier; 3m-avg: last month vs the average of the 3 months before it; qoq: last 3
    complete months vs the 3 before."""
    a = D.resolve_period("last-month", today=today, anchor=anchor)
    if name == "mom":
        return a, D.Period(D.add_months(a.start, -1), a.start, D.add_months(a.start, -1).strftime("%Y-%m"))
    if name == "yoy":
        s = D.add_months(a.start, -12)
        return a, D.Period(s, D.add_months(s, 1), s.strftime("%Y-%m"))
    if name in ("3m-avg", "vs-3m"):
        s = D.add_months(a.start, -3)
        return a, D.Period(s, a.start, "avg of %s..%s" % (s.strftime("%Y-%m"), D.add_months(a.start, -1).strftime("%Y-%m")))
    if name == "qoq":
        q = D.resolve_period("3m", today=today, anchor=anchor)
        s = D.add_months(q.start, -3)
        return q, D.Period(s, q.start, "3 months %s..%s" % (s.strftime("%Y-%m"), D.add_months(q.start, -1).strftime("%Y-%m")))
    raise ValueError("unknown comparison %r; use mom, yoy, 3m-avg, qoq or two periods" % name)


# ---------- breakdowns, top, search ----------

VALUES = {"cost": cost_value, "income": lambda t, _=False: income_value(t), "amount": lambda t, _=False: t.amount}


def breakdown(txns, by="category", value="cost", include_transfers=False):
    """Rows {group, total, count, share (% of all groups), avg (per row), first, last}, largest first.
    value: cost (net spend), income, or amount (raw, every type)."""
    fn = VALUES[value]
    kf = key_fn(by)
    acc = collections.defaultdict(lambda: dict(total=0.0, count=0, first=None, last=None))
    for t in txns:
        v = fn(t, include_transfers)
        if not v:
            continue
        for k in ((t.tags or ("(untagged)",)) if by == "tag" else (kf(t),)):
            g = acc[k]
            g["total"] += v
            g["count"] += 1
            g["first"] = min(g["first"] or t.date, t.date)
            g["last"] = max(g["last"] or t.date, t.date)
    grand = sum(g["total"] for g in acc.values()) if by != "tag" else sum(fn(t, include_transfers) for t in txns)
    rows = [dict(group=k, total=r2(g["total"]), count=g["count"], share=r2(100 * g["total"] / grand) if grand else None,
                 avg=r2(g["total"] / g["count"]), first=g["first"].isoformat(), last=g["last"].isoformat())
            for k, g in acc.items()]
    rows.sort(key=lambda r: -r["total"])
    return rows


def top(txns, by="payee", n=10, value="cost", include_transfers=False):
    """Largest groups (by=payee/category/...) or, with by='txn', the largest single rows by Amount among
    rows that count for `value` (cost: expenses and, if asked, external transfers)."""
    if by == "txn":
        fn = VALUES[value]
        rows = [t for t in txns if fn(t, include_transfers) > 0]
        rows.sort(key=lambda t: -t.amount)
        return [t.to_dict() for t in rows[:n]]
    return breakdown(txns, by, value, include_transfers)[:n]


def search_summary(txns, period=None, include_transfers=False, split=5):
    """What a search matched: counts, money by role, date range, monthly average, category and payee split."""
    s = summarize(txns, period, include_transfers)
    out = dict(count=len(txns), count_by_type=s["count_by_type"], spent=s["net_spend"], expense=s["expense"],
               refunds=s["refunds"], income=s["income"], transfers_out=s["transfers_out"],
               first=min(t.date for t in txns).isoformat() if txns else None,
               last=max(t.date for t in txns).isoformat() if txns else None)
    if period and txns:
        # average over the months actually spanned by the matches inside the period, not the whole period
        first, last = max(period.start, min(t.date for t in txns)), min(period.last, max(t.date for t in txns))
        months = (last.year - first.year) * 12 + last.month - first.month + 1
        out.update(months_spanned=months, spent_per_month=r2(s["net_spend"] / months))
    out["by_category"] = breakdown(txns, "category", "amount")[:split]
    out["by_payee"] = breakdown(txns, "payee", "amount")[:split]
    return out


# ---------- recurring and subscriptions ----------

CADENCES = [("weekly", 7, 2), ("fortnightly", 14, 3), ("4-weekly", 28, 1), ("monthly", 30.4375, 5), ("quarterly", 91.3, 10),
            ("yearly", 365.25, 20)]  # first match wins: 4-weekly (27-29 day median) is checked before monthly
FREQ_DAYS = {"Weekly": 7, "Monthly": 30.4375, "Yearly": 365.25}


def _cadence(days):
    for name, length, tol in CADENCES:
        if abs(days - length) <= tol:
            return name, length, tol
    return None, None, None


def _amount_key(t):
    return t.payee or t.description.strip().upper()


def _transfer_key(t):
    """Destination of a transfer from its description, without the per-transfer receipt number."""
    d = re.sub(r"^TRANSFER\s+\d+\s+", "", t.description.strip().upper())
    return t.payee or d


def _recurring_item(key, rows, as_of, min_count, regularity, stability, new_days):
    """One candidate group -> item dict, or None when it is neither inferred nor flagged."""
    rows = sorted(rows, key=lambda t: t.date)
    flagged = any(t.recurring for t in rows)
    days = sorted({t.date for t in rows})
    gaps = [(b - a).days for a, b in zip(days, days[1:])]
    cad = length = tol = None
    regular = 0.0
    if len(gaps) >= max(1, min_count - 1):
        cad, length, tol = _cadence(statistics.median(gaps))
        if cad:
            regular = sum(1 for g in gaps if abs(g - length) <= tol or abs(g - 2 * length) <= tol) / len(gaps)
    amounts = [t.amount for t in rows]
    med = statistics.median(amounts)
    cv = (statistics.pstdev(amounts) / med) if med and len(amounts) > 1 else 0.0
    inferred = bool(cad) and regular >= regularity and cv <= stability and len(days) >= min_count
    if not (inferred or flagged):
        return None
    if not inferred:  # flagged only: trust the row's frequency, not a noisy median gap
        freq = next((t.frequency for t in rows if t.frequency), "Monthly")
        length = FREQ_DAYS.get(freq, 30.4375)
        cad, tol = freq.lower(), dict(Weekly=2, Monthly=5, Yearly=20).get(freq, 5)
    typical = statistics.median(amounts[-3:])
    nxt = rows[-1].date + dt.timedelta(days=round(length))
    overdue = (as_of - nxt).days
    status = "active" if overdue <= tol else ("late" if overdue <= length else "stopped")
    earlier = amounts[:-1]
    prev = statistics.median(earlier[-3:]) if earlier else None
    change = None
    if prev and abs(amounts[-1] - prev) > max(0.5, 0.02 * prev):
        change = dict(previous=r2(prev), now=r2(amounts[-1]), pct=r2(100 * (amounts[-1] - prev) / prev))
    monthly = typical * 30.4375 / length
    kind = "transfer" if rows[-1].type == "Transfer" or (rows[-1].category or "").endswith("Personal Transfers") else "bill"
    return dict(payee=key, kind=kind, category=rows[-1].category, cadence=cad, typical=r2(typical), monthly=r2(monthly),
                annual=r2(monthly * 12), count=len(rows), first=rows[0].date.isoformat(), last=rows[-1].date.isoformat(),
                next_expected=nxt.isoformat(), status=status, price_change=change,
                new=(as_of - rows[0].date).days <= new_days, flagged=flagged, inferred=inferred,
                amount_cv=r2(cv), regularity=r2(regular), ids=[t.id for t in rows])


def recurring(txns, as_of, min_count=3, regularity=0.75, stability=0.25, new_days=90):
    """Recurring charges among Expense rows: inferred (same payee, regular interval, stable amount) or flagged
    `Recurring`. A payee is split by description when it is irregular as a whole, or when several regular
    plans explain >= 80% of its rows, so two policies with the same payee become two items. `as_of` is the date the data is complete to (use
    coverage()['last'], not today). Item: payee, category, cadence, typical, monthly, annual, count, first,
    last, next_expected, status (active / late / stopped), price_change, new, flagged, inferred, ids."""
    groups = collections.defaultdict(list)
    for t in txns:
        if t.type == "Expense":
            groups[_amount_key(t)].append(t)
        elif is_outgoing(t):  # regular transfers out (loan, savings, family): reported as kind "transfer"
            groups["transfer: " + _transfer_key(t)].append(t)
    args = (as_of, min_count, regularity, stability, new_days)
    out = []
    for key, rows in groups.items():
        item = _recurring_item(key, rows, *args)
        subs = collections.defaultdict(list)
        for t in rows:
            subs[t.description.strip().upper()].append(t)
        if len(subs) > 1:
            parts = [_recurring_item("%s · %s" % (key, d.title()[:32]), r, *args) for d, r in subs.items() if len(r) >= 2]
            parts = [p for p in parts if p and p["inferred"]]
            covered_share = sum(p["count"] for p in parts) / len(rows)
            # split when the payee as a whole is irregular, or when regular plans explain most of its rows
            if parts and (item is None or not item["inferred"] or (len(parts) > 1 and covered_share >= 0.8)):
                covered = {i for p in parts for i in p["ids"]}
                rest = [t for t in rows if t.id not in covered]
                leftover = _recurring_item(key, rest, *args) if rest else None
                out += parts + ([leftover] if leftover and leftover["flagged"] else [])
                continue
        if item:
            out.append(item)
    out.sort(key=lambda r: (r["status"] == "stopped", r["kind"] == "transfer", -r["monthly"]))
    return out


BILL_CATEGORIES = {"Utilities", "Insurance", "Council & Government", "Vehicle & Rego", "Subscriptions & Software",
                   "Education & Childcare", "Rent & Housing", "Health & Wellness"}


def irregular_bills(txns, as_of, recurring_items, months=12, categories=BILL_CATEGORIES):
    """Bills paid in the last `months` that are not regular: annual renewals, quarterly or variable bills,
    one-off fees in bill-like categories. Excludes payees already listed by recurring()."""
    start = D.add_months(as_of.replace(day=1), -months + 1) if months else dt.date(1900, 1, 1)
    covered = {i for r in recurring_items for i in r.get("ids", [])}
    g = collections.defaultdict(list)
    for t in txns:
        if t.type == "Expense" and t.date >= start and t.id not in covered and (t.category or "").split(" > ")[-1] in categories:
            g[_amount_key(t)].append(t)
    out = []
    for k, rows in g.items():
        rows.sort(key=lambda t: t.date)
        out.append(dict(payee=k, category=rows[-1].category, paid=r2(sum(t.amount for t in rows)), count=len(rows),
                        first=rows[0].date.isoformat(), last=rows[-1].date.isoformat(),
                        amounts=[r2(t.amount) for t in rows][-4:]))
    out.sort(key=lambda r: -r["paid"])
    return dict(since=start.isoformat(), items=out, total=r2(sum(r["paid"] for r in out)))


# ---------- run-rate ----------

def run_rate(txns, month, as_of, baseline=None, budget_total=None, include_transfers=False):
    """Spending pace for `month` (a Period) up to `as_of`: spent, daily burn, projected month total, and the
    projection against a baseline monthly figure (e.g. trailing 3m average) and the budget total."""
    end = min(as_of, month.last)
    elapsed = (end - month.start).days + 1
    if elapsed <= 0:
        return dict(month=month.label, elapsed_days=0, spent=0.0, note="no data in this month yet")
    spent = sum(cost_value(t, include_transfers) for t in txns if month.start <= t.date <= end)
    daily = spent / elapsed
    projected = daily * month.days
    out = dict(month=month.label, as_of=end.isoformat(), elapsed_days=elapsed, month_days=month.days, spent=r2(spent),
               daily=r2(daily), projected=r2(projected))
    if baseline is not None:
        out.update(baseline=r2(baseline), vs_baseline=r2(projected - baseline),
                   vs_baseline_pct=r2(100 * (projected - baseline) / baseline) if baseline else None)
    if budget_total:
        out.update(budget=r2(budget_total), budget_left=r2(budget_total - spent),
                   daily_allowance=r2((budget_total - spent) / max(1, month.days - elapsed)))
    return out


# ---------- budgets (D-5: actuals from category + month, not the Budget link) ----------

def budget_vs_actual(txns, month, budget_rows, categories, include_transfers=False):
    """Rows per category for one month: planned, actual, remaining, % used, status (over / near / ok /
    unbudgeted). `budget_rows` from findata.budgets(); `categories` from findata.categories()."""
    actual = collections.defaultdict(float)
    for t in within(txns, month):
        v = cost_value(t, include_transfers)
        if v:
            actual[t.category_id or "(none)"] += v
    planned = collections.defaultdict(float)
    for b in budget_rows.values():
        if b["month"] == month.start and b["category"]:
            planned[b["category"]] += b["planned"]
    rows = []
    for cid in set(actual) | set(planned):
        a, p = actual.get(cid, 0.0), planned.get(cid)
        name = categories.get(cid, {}).get("path") or ("(uncategorised)" if cid == "(none)" else cid)
        used = r2(100 * a / p) if p else None
        status = "unbudgeted" if p is None else ("over" if a > p else "near" if a >= 0.9 * p else "ok")
        rows.append(dict(category=name, category_id=cid, planned=r2(p) if p is not None else None, actual=r2(a),
                         remaining=r2(p - a) if p is not None else None, used_pct=used, status=status))
    rows.sort(key=lambda r: ({"over": 0, "near": 1, "ok": 2, "unbudgeted": 3}[r["status"]], -r["actual"]))
    tp = sum(planned.values())
    ta = sum(r["actual"] for r in rows if r["planned"] is not None)
    return dict(month=month.label, rows=rows, planned_total=r2(tp), actual_budgeted=r2(ta),
                actual_total=r2(sum(actual.values())), budgets=len(planned))


def budget_suggest(txns, period, method="median", round_to=10, include_transfers=False):
    """Suggested monthly budget per expense category from complete months in `period`: median, avg or p75 of
    the monthly totals (months with no spend count as 0), rounded up to `round_to`."""
    ser = monthly_series(txns, period, "category", include_transfers)
    out = []
    for cat, vals in ser["series"].items():
        if cat == "Refunds" or sum(vals) <= 0:
            continue
        v = sorted(vals)
        if method == "avg":
            base = sum(v) / len(v)
        elif method == "p75":
            base = v[min(len(v) - 1, int(round(0.75 * (len(v) - 1))))]
        else:
            base = statistics.median(v)
        sug = -(-base // round_to) * round_to if base > 0 else 0
        out.append(dict(category=cat, suggested=r2(sug), median=r2(statistics.median(v)), avg=r2(sum(v) / len(v)),
                        max=r2(max(v)), months_with_spend=sum(1 for x in v if x > 0), months=len(v)))
    out.sort(key=lambda r: -r["suggested"])
    return dict(method=method, months=ser["months"], rows=out, total=r2(sum(r["suggested"] for r in out)))


# ---------- anomalies and duplicates ----------

def duplicates(txns, reversal_days=3):
    """Groups of rows with the same date, type, amount, payee (or description) and description. Each group
    lists `reversed_by`: rows of the opposite kind for the same amount within `reversal_days` (e.g. a
    double charge plus a "REV VISA DEBIT PURCHASE" refund), which mean the bank already corrected it."""
    g = collections.defaultdict(list)
    for t in txns:
        g[(t.date, t.type, round(t.amount, 2), _amount_key(t), t.description.strip().upper())].append(t)
    out = []
    for k, v in g.items():
        if len(v) < 2:
            continue
        rev = [t for t in txns if abs(t.amount - k[2]) < 0.005 and abs((t.date - k[0]).days) <= reversal_days
               and ((k[1] == "Expense" and is_refund(t)) or (k[1] == "Income" and t.type == "Expense"))]
        out.append(dict(date=k[0].isoformat(), type=k[1], amount=k[2], payee=k[3], count=len(v), ids=[t.id for t in v],
                        descriptions=sorted({t.description for t in v}), reversed_by=[t.id for t in rev]))
    out.sort(key=lambda r: (r["date"], -r["amount"]))
    return out


def _p95(vals):
    v = sorted(vals)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def anomalies(txns, history, k=3.0, min_amount=100.0, min_history=4, new_payee_amount=200.0):
    """Unusually large cost rows in `txns`, judged against `history` (older rows, e.g. the 12 months before):
    amount >= k x the payee's median and above its 95th percentile (>= min_history rows), else the same test
    on the category (>= 2 x min_history rows); first-time payees at or above `new_payee_amount`. Rows below `min_amount` are ignored."""
    by_payee, by_cat = collections.defaultdict(list), collections.defaultdict(list)
    for h in history:
        if h.type == "Expense":
            by_payee[_amount_key(h)].append(h.amount)
            by_cat[h.category].append(h.amount)
    out = []
    for t in txns:
        if t.type != "Expense" or t.amount < min_amount:
            continue
        p, c = by_payee.get(_amount_key(t), []), by_cat.get(t.category, [])
        reason = None
        if len(p) >= min_history:
            m = statistics.median(p)
            if t.amount >= k * m and t.amount > _p95(p):
                reason = "%.1fx the usual %s at this payee (above its 95th percentile %s)" % (t.amount / m, "$%.2f" % m, "$%.2f" % _p95(p))
        elif len(c) >= 2 * min_history:
            m = statistics.median(c)
            if t.amount >= k * m and t.amount > _p95(c):
                reason = "%.1fx the usual %s in %s (above its 95th percentile %s)" % (t.amount / m, "$%.2f" % m, t.category, "$%.2f" % _p95(c))
        if not reason and not p and t.amount >= new_payee_amount:
            reason = "first payment to this payee"
        if reason:
            d = t.to_dict()
            d["reason"] = reason
            out.append(d)
    out.sort(key=lambda r: -r["amount"])
    return out


# ---------- balance and cash flow ----------

def balance_series(txns, account, period=None):
    """End-of-month balance for one account (dict from findata.accounts()): opening balance + its own signed
    rows + transfers into it, the same rule as the Accounts `Current Balance` formula. `txns` must be every
    row touching the account (own rows and rows with it as Transfer Account)."""
    name = account["name"]
    deltas = collections.defaultdict(float)
    fix = collections.defaultdict(float)  # incoming transfers: formula subtracts them, reality adds them
    for t in txns:
        if t.account_id == account["id"]:
            deltas[t.date] += t.signed
            if is_incoming(t):
                fix[t.date] += 2 * t.amount
        if t.type == "Transfer" and t.transfer_account == name:
            deltas[t.date] += t.amount
    days = sorted(set(deltas) | set(fix))
    bal = adj = account["opening"]
    month_end = {}
    for d in days:
        bal += deltas[d]
        adj += deltas[d] + fix[d]
        month_end[d.strftime("%Y-%m")] = (r2(bal), r2(adj))
    months = sorted(month_end)
    if period:
        months = [m for m in months if period.start.strftime("%Y-%m") <= m <= period.last.strftime("%Y-%m")]
    points = [dict(month=m, balance=month_end[m][1], formula_balance=month_end[m][0]) for m in months]
    formula = r2(account["opening"] + sum(deltas.values()))
    final = r2(formula + sum(fix.values()))
    n_in = sum(1 for t in txns if t.account_id == account["id"] and is_incoming(t))
    warnings = []
    if n_in:
        warnings.append("%d incoming transfer(s) (%s) are stored as Transfer, so the Current Balance formula subtracts them; "
                        "corrected balance %.2f vs formula %.2f (fin.py doctor, group K)"
                        % (n_in, "$%.2f" % (sum(fix.values()) / 2), final, formula))
    if final < 0 and account.get("type") in ("Checking", "Savings", "Cash"):
        warnings.append("balance is negative for a %s account even after correction: income or source accounts are missing"
                        % account["type"].lower())
    if account.get("balance") is not None and abs(account["balance"] - formula) > 0.01:
        warnings.append("formula balance %.2f differs from the Current Balance field %.2f" % (formula, account["balance"]))
    lowest = min(points, key=lambda p: p["balance"]) if points else None
    return dict(account=name, opening=account["opening"], opening_date=str(account.get("opening_date")), final=final,
                formula_balance=formula, incoming_transfers=n_in, months=points, lowest=lowest, warnings=warnings)


def cash_flow(txns, period):
    """Per month: income, refunds, expense, net spend, transfers out, net cash flow."""
    out = []
    for m in months_in(period):
        y, mo = int(m[:4]), int(m[5:])
        p = D.Period(dt.date(y, mo, 1), D.add_months(dt.date(y, mo, 1), 1), m)
        s = summarize(within(txns, p))
        out.append(dict(month=m, income=s["income"], refunds=s["refunds"], expense=s["expense"], net_spend=s["net_spend"],
                        transfers_out=s["transfers_out"], transfers_in=s["transfers_in"], net_cash_flow=s["net_cash_flow"]))
    return out


# ---------- financial year / tax ----------

def fy_report(txns, period, tax_tags=("Tax Deductible", "Reimbursable")):
    """Australian FY view: income by category, business-scope expenses by category, tagged totals, and the
    personal/business split. Rows must be enriched (category scope)."""
    biz = [t for t in txns if t.scope in ("Business", "Shared")]
    tagged = {tag: [t for t in txns if tag in t.tags] for tag in tax_tags}
    return dict(period=period.to_dict(), summary=summarize(txns, period),
                income_by_category=breakdown(txns, "category", "income"),
                business_income=r2(sum(income_value(t) for t in biz)),
                business_expenses=breakdown(biz, "category", "cost"),
                business_expense_total=r2(sum(cost_value(t) for t in biz)),
                tagged={tag: dict(total=r2(sum(t.amount for t in rows)), count=len(rows),
                                  by_category=breakdown(rows, "category", "amount")) for tag, rows in tagged.items()},
                by_scope=breakdown(txns, "scope", "cost"))
