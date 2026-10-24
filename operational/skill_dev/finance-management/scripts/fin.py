#!/usr/bin/env python3
"""Finance CLI for cybernetics-data (finance_* tables) over the Teable REST API.

Cost = expenses minus refunds; transfers are separate unless --include-transfers (references/metrics.md).
Periods: mtd | last-month | 3m | 6m | 12m (complete months) | 30d | 2026-08 | qtd | ytd | 2025 | fy | fy2026 |
fytd | last-fy | all | 2026-01-15..2026-02-14 | 2026-01..2026-03. --anchor YYYY-MM moves "last complete month".

Report
  fin.py summary [PERIOD]                          income, expense, refunds, net spend, transfers, savings rate
  fin.py cost [--windows 1,3,6,12] [--by category] [--avg]   1/3/6/12-month cost + MTD in one table
  fin.py trend [PERIOD=12m] [--by category] [--top 8]        month-by-month cost
  fin.py compare mom|yoy|3m-avg|qoq | --a P --b P [--by category]
  fin.py breakdown [PERIOD=last-month] [--by category|parent|payee|tag|scope|account|weekday|type] [--value cost|income|amount]
  fin.py top [PERIOD=12m] [--by payee|category|txn] [-n 10]
  fin.py search [WORDS ...] [--period all] [--category ..] [--payee ..] [--min N] [--limit 30]
  fin.py recurring [--all]                         subscriptions and regular payments, monthly + annual cost
  fin.py runrate [--month YYYY-MM]                 pace this month vs trailing 3-month average and budget
  fin.py budget [YYYY-MM] | budget-suggest [PERIOD=6m] [--method median|avg|p75]
  fin.py anomalies [PERIOD=3m] [--history 12] [--k 3] | duplicates [PERIOD=all]
  fin.py balance [--account A] | cashflow [PERIOD=12m] | fy [fy2026]
  fin.py doctor                                    read-only data-quality report, each finding with a fix

Write (DRY-RUN unless --yes; validated, read back, undo file in ~/.cache/finance-management/undo/)
  fin.py add --date D --amount N --type Expense --desc "..." [--payee P] [--category C] [--account A] [--tag T]
  fin.py categorize --to CATEGORY (--ids rec.. | filters [--period P])   e.g. --payee Woolworths --uncategorized
  fin.py tag|untag TAG (--ids rec.. | filters [--period P])
  fin.py budget-set YYYY-MM --category C --amount N
  fin.py payee-default PAYEE --category C
  fin.py delete rec.. (to the table trash; explicit ids only)
  fin.py undo [FILE]                               restore the latest (or given) undo file

Filters on every report: --type T, --category C[,C], --exclude-category C[,C], --payee P[,P], --exclude-payee P[,P], --account A, --tag T, --text WORDS,
--scope personal|business, --min N, --max N, --recurring, --uncategorized, --include-transfers.
Add --json for machine output. Exit codes: 0 ok, 2 bad input or blocked by a check, 3 not found or ambiguous.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import findata as D
import fincalc as C


def money(x):
    if x is None:
        return "-"
    return ("-$%s" if x < 0 else "$%s") % format(abs(x), ",.2f")


def pct(x):
    return "-" if x is None else "%+.1f%%" % x


def table(rows, cols, aligns=None):
    """rows: list of lists of str. Right-aligns columns marked 'r' in aligns."""
    aligns = aligns or "l" * len(cols)
    w = [max(len(str(c)), *(len(str(r[i])) for r in rows)) if rows else len(str(c)) for i, c in enumerate(cols)]
    fmt = lambda r: "  ".join(str(v).rjust(w[i]) if aligns[i] == "r" else str(v).ljust(w[i]) for i, v in enumerate(r)).rstrip()
    return "\n".join([fmt(cols), fmt(["-" * x for x in w])] + [fmt(r) for r in rows])


def emit(a, data, human):
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1, default=str))
    else:
        print(human() if callable(human) else human)


def period_of(a, spec, default):
    return D.resolve_period(spec or default, anchor=a.anchor)


def filters(a):
    f = dict(types=a.type, categories=a.category, payees=a.payee, accounts=a.account, tags=a.tag, text=a.text,
             min_amount=a.min, max_amount=a.max, recurring=True if a.recurring else None, uncategorized=a.uncategorized,
             exclude_categories=a.exclude_category, exclude_payees=a.exclude_payee)
    return {k: v for k, v in f.items() if v not in (None, False, [])}


def fetch(a, period):
    """Category enrichment (1 extra call) only when scope or category paths matter."""
    need = bool(a.scope) or getattr(a, "by", None) in ("scope", "parent")
    return D.load_txns(period, scope=a.scope, enrich_categories=need, **filters(a))


def basis(a, period, rows):
    f = filters(a)
    if a.scope:
        f["scope"] = a.scope
    return dict(note=D.coverage_note(period, len(rows)), filters=f, include_transfers=a.include_transfers,
                http_calls=D.CALLS[0])


def filter_line(a):
    f = filters(a)
    if a.scope:
        f["scope"] = a.scope
    return "filters: " + ", ".join("%s=%s" % (k, ",".join(v) if isinstance(v, list) else v) for k, v in f.items()) if f else None


def head(a, title, period, rows):
    return "\n".join(x for x in [title, D.coverage_note(period, len(rows), label=False), filter_line(a)] if x)


COST_DEF = "net spend = expenses - refunds; transfers %s"


# ---------- report commands ----------

def cmd_summary(a):
    p = period_of(a, a.period, "last-month")
    rows = fetch(a, p)
    s = C.summarize(rows, p, a.include_transfers)
    data = dict(summary=s, basis=basis(a, p, rows))

    def human():
        lines = [head(a, "Summary · " + p.label, p, rows), ""]
        kv = [("Income", money(s["income"])), ("Expenses", money(s["expense"])), ("Refunds", money(s["refunds"])),
              ("Net spend" + (" (incl. transfers)" if a.include_transfers else ""), money(s["net_spend"])),
              ("  per month", money(s.get("monthly_avg"))), ("  per day", money(s.get("daily_avg"))),
              ("Transfers out", money(s["transfers_out"])), ("Transfers in", money(s["transfers_in"])),
              ("Net cash flow", money(s["net_cash_flow"])),
              ("Savings rate", "-" if s["savings_rate"] is None else "%.1f%%" % s["savings_rate"]),
              ("Rows", ", ".join("%s %d" % kv for kv in sorted(s["count_by_type"].items())) or "0")]
        lines += ["%-24s %s" % kv for kv in kv]
        if s["internal_transfers"]:
            lines.append("%-24s %s (moved between your own accounts, both directions; not cost or income)" % ("Own-account transfers", money(s["internal_transfers"])))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_cost(a):
    windows = tuple(int(x) for x in a.windows.split(","))
    ps = C.window_periods(windows, anchor=a.anchor, mtd=not a.no_mtd)
    whole = C.span(*ps)
    rows = fetch(a, whole)
    res = C.cost_windows(rows, windows, anchor=a.anchor, include_transfers=a.include_transfers, mtd=not a.no_mtd)
    data = dict(definition=COST_DEF % ("included" if a.include_transfers else "excluded"), windows=res, basis=basis(a, whole, rows),
                warnings={p.label: D.coverage_warnings(p) for p in ps if D.coverage_warnings(p)})
    by = None
    if a.by:
        by = {}
        for p in ps:
            g = C.group_values(C.within(rows, p), a.by, include_transfers=a.include_transfers)
            by[p.label] = {k: C.r2(v[0] / p.months if a.avg and p.months else v[0]) for k, v in g.items()}
        data["by"] = dict(group_by=a.by, values="monthly_avg" if a.avg else "total", windows=by)

    def human():
        cov = D.coverage()
        lines = ["Cost by window · " + COST_DEF % ("included" if a.include_transfers else "excluded"),
                 "%d rows · data %s..%s (%d days old)" % (len(rows), cov["first"], cov["last"], cov["age_days"])]
        lines += [x for x in [filter_line(a)] if x] + [""]
        lines.append(table([[r["window"], "%s..%s" % (r["start"], r["end"]), money(r["net_spend"]), money(r["monthly_avg"]),
                             money(r["daily_avg"]), money(r["refunds"]), str(r["count"])] for r in res],
                           ["window", "dates", "net spend", "per month", "per day", "refunds", "rows"], "llrrrrr"))
        warned = {}
        for p in ps:
            for w in D.coverage_warnings(p):
                warned.setdefault(w, []).append(p.label)
        lines += ["! %s: %s" % (", ".join(v) if len(v) < len(ps) else "all windows", w) for w, v in warned.items()]
        if by:
            labels = [p.label for p in ps]
            short = ["%dm" % w for w in windows] + ([] if len(ps) == len(windows) else ["MTD"])
            widest = max(ps, key=lambda p: p.months).label
            keys = sorted({k for v in by.values() for k in v}, key=lambda k: -abs(by[widest].get(k, 0)))
            lines += ["", "By %s (%s)" % (a.by, "monthly average" if a.avg else "totals")]
            lines.append(table([[k] + [money(by[l][k]) if k in by[l] else "-" for l in labels] for k in keys],
                               [a.by] + short, "l" + "r" * len(labels)))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_trend(a):
    p = period_of(a, a.period, "12m")
    rows = fetch(a, p)
    ser = C.monthly_series(rows, p, a.by, a.include_transfers, top=a.top)
    stats = C.trend_stats(ser["total"])
    ser["rolling_3m"] = C.rolling_avg(ser["total"], 3)
    data = dict(trend=ser, stats=stats, basis=basis(a, p, rows))

    def human():
        lines = [head(a, "Monthly cost · " + p.label + " · " + COST_DEF % ("included" if a.include_transfers else "excluded"), p, rows), ""]
        if a.by:
            cols = ["month"] + list(ser["series"]) + ["total"]
            body = [[m] + [money(ser["series"][k][i]) for k in ser["series"]] + [money(ser["total"][i])] for i, m in enumerate(ser["months"])]
            lines.append(table(body, cols, "l" + "r" * (len(cols) - 1)))
        else:
            peak = max(ser["total"] or [0]) or 1
            body = [[m, money(v), money(ser["rolling_3m"][i]), "#" * int(round(28 * (v or 0) / peak))] for i, (m, v) in enumerate(zip(ser["months"], ser["total"]))]
            lines.append(table(body, ["month", "net spend", "3m avg", ""], "lrrl"))
        lines.append("")
        lines.append("mean %s · median %s · min %s · max %s · last %s (%s vs mean) · slope %s/month" % (
            money(stats["mean"]), money(stats["median"]), money(stats["min"]), money(stats["max"]), money(stats["last"]),
            pct(stats["last_vs_mean_pct"]), money(stats["slope_per_month"])))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_compare(a):
    if a.preset:
        pa, pb = C.compare_preset(a.preset, anchor=a.anchor)
    else:
        if not (a.a and a.b):
            raise ValueError("give a preset (mom, yoy, 3m-avg, qoq) or both --a and --b")
        pa, pb = period_of(a, a.a, None), period_of(a, a.b, None)
    whole = C.span(pa, pb)
    rows = fetch(a, whole)
    res = C.compare(rows, pa, rows, pb, a.by, a.include_transfers, a.normalize)
    data = dict(compare=res, basis=basis(a, whole, rows))

    def human():
        t = res["total"]
        unit = " per month" if res["normalize"] == "monthly" else ""
        lines = [head(a, "Compare · %s vs %s%s" % (pa.label, pb.label, unit), whole, rows), "",
                 "Total: %s vs %s · %s (%s)" % (money(t["a"]), money(t["b"]), money(t["delta"]), pct(t["delta_pct"]))]
        if a.by:
            rs = res["rows"][:a.top] if a.top else res["rows"]
            lines += ["", table([[r["group"], money(r["a"]), money(r["b"]), money(r["delta"]), pct(r["delta_pct"])] for r in rs],
                                [a.by, pa.label, pb.label, "change", "%"], "lrrrr")]
        return "\n".join(lines)
    emit(a, data, human)


def cmd_breakdown(a):
    p = period_of(a, a.period, "last-month")
    rows = fetch(a, p)
    res = C.breakdown(rows, a.by, a.value, a.include_transfers)
    total = C.r2(sum(r["total"] for r in res)) if a.by != "tag" else C.r2(sum(C.VALUES[a.value](t, a.include_transfers) for t in rows))
    shown = res[:a.top] if a.top else res
    data = dict(breakdown=shown, group_by=a.by, value=a.value, total=total, groups=len(res),
                per_month=C.r2(total / p.months) if p.months else None, basis=basis(a, p, rows))

    def human():
        what = {"cost": COST_DEF % ("included" if a.include_transfers else "excluded"), "income": "income (refunds excluded)",
                "amount": "raw amounts, every type"}[a.value]
        lines = [head(a, "Breakdown by %s · %s · %s" % (a.by, p.label, what), p, rows), ""]
        body = [[r["group"], money(r["total"]), "-" if r["share"] is None else "%.1f%%" % r["share"],
                 "#" * max(0, int(round((r["share"] or 0) / 4))), str(r["count"]), money(r["avg"])] for r in shown]
        lines.append(table(body, [a.by, "total", "share", "", "rows", "avg"], "lrrlrr"))
        more = len(res) - len(shown)
        lines.append("%stotal %s over %d groups · %s per month" % ("(+%d more groups) " % more if more else "", money(total), len(res),
                                                                   money(data["per_month"])))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_top(a):
    p = period_of(a, a.period, "12m")
    rows = fetch(a, p)
    res = C.top(rows, a.by, a.n, a.value, a.include_transfers)
    data = dict(top=res, by=a.by, value=a.value, basis=basis(a, p, rows))

    def human():
        lines = [head(a, "Top %d %s · %s" % (a.n, "transactions" if a.by == "txn" else a.by, p.label), p, rows), ""]
        if a.by == "txn":
            lines.append(table([[r["date"], r["description"][:40], r["payee"] or "", r["category"] or r["type"], money(r["amount"])] for r in res],
                               ["date", "description", "payee", "category", "amount"], "llllr"))
        else:
            lines.append(table([[r["group"], money(r["total"]), "%.1f%%" % (r["share"] or 0), str(r["count"]), money(r["avg"]), r["last"]] for r in res],
                               [a.by, "total", "share", "rows", "avg", "last"], "lrrrrl"))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_search(a):
    if a.words:
        a.text = (a.text + " " if a.text else "") + " ".join(a.words)
    if not (filters(a) or a.scope):
        raise ValueError("search needs words or at least one filter (--category, --payee, --tag, --type, --min, ...)")
    p = period_of(a, a.period, "all")
    rows = fetch(a, p)
    summ = C.search_summary(rows, p, a.include_transfers)
    newest = sorted(rows, key=lambda t: (t.date, t.id), reverse=True)
    data = dict(summary=summ, transactions=[t.to_dict() for t in newest[:a.limit]], shown=min(a.limit, len(rows)), basis=basis(a, p, rows))

    def human():
        lines = [head(a, "Search · %s" % p.label, p, rows), ""]
        if not rows:
            lines.append("no transactions match")
            return "\n".join(lines)
        types = ", ".join("%s %d" % kv for kv in sorted(summ["count_by_type"].items()))
        lines.append("%d match%s (%s) · %s..%s" % (summ["count"], "" if summ["count"] == 1 else "es", types, summ["first"], summ["last"]))
        money_parts = [("spent (net)", summ["spent"]), ("refunds", summ["refunds"]), ("income", summ["income"]), ("transfers out", summ["transfers_out"])]
        lines.append(" · ".join("%s %s" % (k, money(v)) for k, v in money_parts if v))
        if summ.get("spent_per_month") is not None and summ["spent"]:
            lines.append("spent per month %s over %d months with matches" % (money(summ["spent_per_month"]), summ["months_spanned"]))
        for key, label in (("by_category", "category"), ("by_payee", "payee")):
            if len(summ[key]) > 1:
                lines.append("by %s: %s" % (label, " · ".join("%s %s (%d)" % (r["group"], money(r["total"]), r["count"]) for r in summ[key])))
        lines += ["", table([[t.date.isoformat(), t.description[:40], t.payee or "", t.category or "", t.type[:3],
                              money(t.signed)] for t in newest[:a.limit]], ["date", "description", "payee", "category", "type", "amount"], "lllllr")]
        if len(rows) > a.limit:
            lines.append("(%d older rows not shown; --limit N)" % (len(rows) - a.limit))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_recurring(a):
    p = period_of(a, a.period, "all")
    rows = fetch(a, p)
    cov = D.coverage()
    items = C.recurring(rows, cov["last"])
    irr = C.irregular_bills(rows, cov["last"], items)
    shown = items if a.all else [i for i in items if i["status"] != "stopped"]
    live = [i for i in items if i["status"] != "stopped"]
    bills = [i for i in live if i["kind"] == "bill"]
    transfers = [i for i in live if i["kind"] == "transfer"]
    for i in items:
        i.pop("ids", None)
    data = dict(as_of=cov["last"], items=shown, bills_monthly=C.r2(sum(i["monthly"] for i in bills)),
                bills_annual=C.r2(sum(i["annual"] for i in bills)), transfers_monthly=C.r2(sum(i["monthly"] for i in transfers)),
                transfers_annual=C.r2(sum(i["annual"] for i in transfers)), irregular=irr,
                stopped=len(items) - len(live), basis=basis(a, p, rows))

    def section(rows_):
        return table([[i["payee"][:40], (i["category"] or "")[:22], i["cadence"], money(i["typical"]), money(i["monthly"]), money(i["annual"]),
                       str(i["count"]), i["last"], i["next_expected"], i["status"] + (" NEW" if i["new"] else ""),
                       ("%+.0f%%" % i["price_change"]["pct"]) if i["price_change"] else "",
                       ("flag" if i["flagged"] else "") + ("+infer" if i["inferred"] and i["flagged"] else "infer" if i["inferred"] else "")]
                      for i in rows_],
                     ["payee", "category", "cadence", "typical", "per month", "per year", "n", "last", "next", "status", "price", "source"],
                     "lllrrrrlllrl")

    def human():
        lines = [head(a, "Recurring payments · as of %s (last transaction; status is judged against it, not today)" % cov["last"], p, rows), ""]
        lines += ["Bills and subscriptions", section([i for i in shown if i["kind"] == "bill"]),
                  "%s per month · %s per year · %d active" % (money(data["bills_monthly"]), money(data["bills_annual"]), len(bills))]
        if any(i["kind"] == "transfer" for i in shown):
            lines += ["", "Regular transfers and payments to people (Personal Transfers count as cost; Transfer rows do not)", section([i for i in shown if i["kind"] == "transfer"]),
                      "%s per month · %s per year · %d active" % (money(data["transfers_monthly"]), money(data["transfers_annual"]), len(transfers))]
        if irr["items"]:
            lines += ["", "Other bills paid since %s (annual, quarterly or irregular; amount actually paid)" % irr["since"],
                      table([[r["payee"][:40], (r["category"] or "")[:22], money(r["paid"]), str(r["count"]), r["last"],
                              ", ".join("%.2f" % x for x in r["amounts"])] for r in irr["items"]],
                            ["payee", "category", "paid", "n", "last", "amounts"], "llrrll"),
                      "%s in total" % money(irr["total"])]
        if not a.all and data["stopped"]:
            lines.append("\n%d stopped item(s) hidden (--all)" % data["stopped"])
        return "\n".join(lines)
    emit(a, data, human)


def cmd_runrate(a):
    month = D.resolve_period(a.month) if a.month else D.resolve_period("mtd")
    month = D.Period(month.start, D.add_months(month.start, 1), month.start.strftime("%Y-%m"))
    base_p = D.Period(D.add_months(month.start, -3), month.start, "3 months before")
    rows = fetch(a, C.span(base_p, month))
    cov = D.coverage()
    as_of = min(D.T.today(), cov["last"])
    baseline = C.cost(rows, base_p, a.include_transfers)["monthly_avg"]
    planned = sum(b["planned"] for b in D.budgets().values() if b["month"] == month.start)
    rr = C.run_rate(rows, month, as_of, baseline, planned or None, a.include_transfers)
    data = dict(run_rate=rr, basis=basis(a, month, rows))

    def human():
        lines = [head(a, "Run-rate · %s · %s" % (month.label, COST_DEF % ("included" if a.include_transfers else "excluded")), month, rows), ""]
        if not rr.get("elapsed_days"):
            lines.append("no data in %s yet (last transaction %s); try --month %s" % (month.label, cov["last"], cov["last"].strftime("%Y-%m")))
            return "\n".join(lines)
        lines.append("spent %s in %d of %d days (to %s) · %s per day" % (money(rr["spent"]), rr["elapsed_days"], rr["month_days"], rr["as_of"], money(rr["daily"])))
        lines.append("projected month total %s vs %s average of the 3 months before (%s, %s)" % (
            money(rr["projected"]), money(rr.get("baseline")), money(rr.get("vs_baseline")), pct(rr.get("vs_baseline_pct"))))
        if rr.get("budget"):
            lines.append("budget %s · left %s · %s per remaining day" % (money(rr["budget"]), money(rr["budget_left"]), money(rr["daily_allowance"])))
        else:
            lines.append("no budgets set for %s (fin.py budget-suggest, then budget-set)" % month.label)
        return "\n".join(lines)
    emit(a, data, human)


def cmd_budget(a):
    month = D.resolve_period(a.month or "last-month", anchor=a.anchor)
    if month.months != 1:
        raise ValueError("budget works on one calendar month, e.g. 2026-08")
    rows = fetch(a, month)
    res = C.budget_vs_actual(rows, month, D.budgets(), D.categories(), a.include_transfers)
    data = dict(budget=res, basis=basis(a, month, rows))

    def human():
        lines = [head(a, "Budget vs actual · %s (actuals from category + month)" % month.label, month, rows), ""]
        if not res["budgets"]:
            lines.append("no budgets set for %s: showing actuals only (fin.py budget-suggest proposes amounts)" % month.label)
        lines.append(table([[r["category"], money(r["planned"]), money(r["actual"]), money(r["remaining"]),
                             "-" if r["used_pct"] is None else "%.0f%%" % r["used_pct"], r["status"]] for r in res["rows"]],
                           ["category", "planned", "actual", "remaining", "used", "status"], "lrrrrl"))
        lines.append("planned %s · spent in budgeted categories %s · spent in total %s" % (
            money(res["planned_total"]), money(res["actual_budgeted"]), money(res["actual_total"])))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_budget_suggest(a):
    p = period_of(a, a.period, "6m")
    rows = fetch(a, p)
    res = C.budget_suggest(rows, p, a.method, a.round, a.include_transfers)
    data = dict(suggest=res, basis=basis(a, p, rows))

    def human():
        lines = [head(a, "Suggested monthly budgets · %s of %d months (%s) · rounded up to $%d" % (a.method, len(res["months"]), p.label, a.round), p, rows), ""]
        lines.append(table([[r["category"], money(r["suggested"]), money(r["median"]), money(r["avg"]), money(r["max"]),
                             "%d/%d" % (r["months_with_spend"], r["months"])] for r in res["rows"]],
                           ["category", "suggested", "median", "avg", "max", "months"], "lrrrrr"))
        lines.append("total %s per month · set one with: fin.py budget-set <YYYY-MM> --category <name> --amount <N>" % money(res["total"]))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_anomalies(a):
    p = period_of(a, a.period, "3m")
    hist_p = D.Period(D.add_months(p.start, -a.history), p.start, "%d months before" % a.history)
    rows = fetch(a, C.span(hist_p, p))
    res = C.anomalies(C.within(rows, p), C.within(rows, hist_p), a.k, a.min_amount)
    data = dict(anomalies=res, history=hist_p.to_dict(), k=a.k, min_amount=a.min_amount, basis=basis(a, p, C.within(rows, p)))

    def human():
        lines = [head(a, "Unusual charges · %s vs the %d months before · >= %sx usual and above the 95th percentile, >= %s"
                      % (p.label, a.history, a.k, money(a.min_amount)), p, C.within(rows, p)), ""]
        if not res:
            lines.append("nothing unusual")
        else:
            lines.append(table([[r["date"], r["description"][:36], r["payee"] or "", money(r["amount"]), r["reason"]] for r in res],
                               ["date", "description", "payee", "amount", "why"], "lllrl"))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_duplicates(a):
    p = period_of(a, a.period, "all")
    rows = fetch(a, p)
    res = C.duplicates(rows)
    data = dict(duplicates=res, basis=basis(a, p, rows))

    def human():
        lines = [head(a, "Possible duplicates · same date, type, amount and payee", p, rows), ""]
        if not res:
            lines.append("none found")
        else:
            lines.append(table([[r["date"], r["type"], money(r["amount"]), r["payee"][:30], str(r["count"]), " | ".join(r["descriptions"])[:44],
                                 ("reversed by " + " ".join(r["reversed_by"])) if r["reversed_by"] else "", " ".join(r["ids"])] for r in res],
                               ["date", "type", "amount", "payee", "n", "description", "bank fix", "ids"], "llrlrlll"))
            lines.append("%d group(s), %d already reversed by the bank. Same-day repeats are often genuine (same import, consecutive statement "
                         "lines); check the statement before deleting anything." % (len(res), sum(1 for r in res if r["reversed_by"])))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_balance(a):
    accs = D.accounts()
    targets = [D.resolve("account", x) for x in a.account] if a.account else [x for x in accs.values() if x["active"]]
    out = []
    for acc in targets:
        rows = D.load_txns(None, accounts=[acc["id"]]) + [t for t in D.load_txns(None, types=["Transfer"]) if t.transfer_account == acc["name"]]
        out.append(C.balance_series(rows, acc))
    data = dict(accounts=out, http_calls=D.CALLS[0])

    def human():
        lines = ["Account balances · opening balance + own rows + transfers in; incoming transfers counted as money in",
                 "(the Current Balance formula counts every Transfer as money out; 'formula' shows its figure)"]
        for b in out:
            lines += ["", "%s · opening %s on %s · balance %s at the last transaction (formula %s)" % (
                b["account"], money(b["opening"]), b["opening_date"], money(b["final"]), money(b["formula_balance"]))]
            lines.append(table([[m["month"], money(m["balance"]), money(m["formula_balance"])] for m in b["months"]],
                               ["month end", "balance", "formula"], "lrr"))
            lines += ["! " + w for w in b["warnings"]]
        return "\n".join(lines)
    emit(a, data, human)


def cmd_cashflow(a):
    p = period_of(a, a.period, "12m")
    rows = fetch(a, p)
    res = C.cash_flow(rows, p)
    tot = C.summarize(rows, p)
    data = dict(cash_flow=res, total=tot, basis=basis(a, p, rows))

    def human():
        lines = [head(a, "Cash flow · %s" % p.label, p, rows), ""]
        lines.append(table([[r["month"], money(r["income"]), money(r["net_spend"]), money(r["transfers_out"]), money(r["transfers_in"]),
                             money(r["net_cash_flow"])] for r in res]
                           + [["total", money(tot["income"]), money(tot["net_spend"]), money(tot["transfers_out"]), money(tot["transfers_in"]),
                               money(tot["net_cash_flow"])]],
                           ["month", "income", "net spend", "transfers out", "transfers in", "net cash flow"], "lrrrrr"))
        return "\n".join(lines)
    emit(a, data, human)


def cmd_fy(a):
    p = period_of(a, a.fy, "last-fy")
    if not p.label.startswith("FY"):
        raise ValueError("fy takes fy, last-fy, fytd or fyYYYY (FY2026 = Jul 2025-Jun 2026)")
    rows = D.load_txns(p, scope=a.scope, enrich_categories=True, **filters(a))
    res = C.fy_report(rows, p)
    data = dict(fy=res, basis=basis(a, p, rows))

    def human():
        s = res["summary"]
        lines = [head(a, "Financial year · %s" % p.label, p, rows), "",
                 "income %s · net spend %s · transfers out %s · net cash flow %s" % (money(s["income"]), money(s["net_spend"]),
                                                                                    money(s["transfers_out"]), money(s["net_cash_flow"])), "",
                 "Income by category", table([[r["group"], money(r["total"]), str(r["count"])] for r in res["income_by_category"]],
                                             ["category", "total", "rows"], "lrr"), "",
                 "Business (category scope Business or Shared): income %s · expenses %s" % (money(res["business_income"]), money(res["business_expense_total"])),
                 table([[r["group"], money(r["total"]), str(r["count"])] for r in res["business_expenses"]], ["category", "total", "rows"], "lrr"), ""]
        for tag, v in res["tagged"].items():
            lines.append("Tagged %s: %s in %d row(s)" % (tag, money(v["total"]), v["count"]))
        if not any(v["count"] for v in res["tagged"].values()):
            lines.append("(no transactions are tagged yet; fin.py tag adds tags)")
        lines.append("Not tax advice: a summary of what is recorded.")
        return "\n".join(lines)
    emit(a, data, human)


def cmd_doctor(a):
    import doctor
    res = doctor.run()
    res["http_calls"] = D.CALLS[0]

    def human():
        cov = res["coverage"]
        lines = ["Finance doctor · %d rows · data %s..%s (%s days old) · read-only" % (res["rows"], cov["first"], cov["last"], cov["age_days"])]
        if not res["findings"]:
            lines.append("no findings")
        for f in res["findings"]:
            lines += ["", "[%s] %s %s · %d%s" % (f["group"], f["severity"].upper(), f["title"], f["count"], " · " + f["note"] if f["note"] else "")]
            lines += ["    " + str(x) for x in f["sample"]]
            if f["count"] > len(f["sample"]):
                lines.append("    ... and %d more (--json lists all)" % (f["count"] - len(f["sample"])))
            lines.append("  fix: " + f["fix"])
        return "\n".join(lines)
    emit(a, res, human)


# ---------- write commands ----------

def show_plan(a, data, lines, blocks=()):
    """Print a write preview; returns True when the caller should write."""
    data = dict(data, dry_run=not a.yes, blocked=list(blocks))
    if blocks:
        emit(a, data, lambda: "\n".join(lines + ["BLOCKED: " + b for b in blocks]))
        sys.exit(2)
    if not a.yes:
        emit(a, data, lambda: "\n".join(lines + ["DRY RUN: nothing written. Re-run with --yes to apply."]))
        return False
    return True


def done(a, data, line):
    emit(a, dict(data, dry_run=False, blocked=[]), line)


def cmd_add(a):
    fields, info = D.plan_add(a.date, a.amount, a.type_, a.desc, a.account_name, a.payee_name, a.category_name, a.tags, a.notes,
                              a.recurring_flag, a.frequency, a.transfer_account)
    if a.allow_duplicate:
        info["blocks"] = [b for b in info["blocks"] if not b.startswith("possible duplicate")]
    if a.force:
        info["warnings"] += [b for b in info["blocks"] if "(use --force" in b]
        info["blocks"] = [b for b in info["blocks"] if "(use --force" not in b]
    pv = info["preview"]
    lines = ["Add transaction", "  " + " · ".join("%s: %s" % (k, v) for k, v in pv.items() if v not in (None, [], False))]
    lines += ["  inferred " + x for x in info["inferred"]] + ["  warning: " + w for w in info["warnings"]]
    if not show_plan(a, dict(preview=pv, info=info), lines, info["blocks"]):
        return
    ids, undo = D.create_many(D.TX, [fields], "add")
    done(a, dict(created=ids, undo=str(undo), preview=pv), "created %s · verified · undo: fin.py undo %s" % (ids[0], undo))


def _targets(a):
    ids = [x for x in (a.ids or "").replace(",", " ").split() if x]
    p = D.resolve_period(a.period, anchor=a.anchor) if a.period else None
    return D.select_txns(ids or None, p, **filters(a)), p


def _sample(rows, n=12):
    out = ["  %s  %s  %-34s %-20s %-18s %s" % (t.id, t.date, t.description[:34], (t.payee or "")[:20], (t.category or "-")[:18], money(t.amount))
           for t in rows[:n]]
    if len(rows) > n:
        out.append("  ... and %d more" % (len(rows) - n))
    return out


def cmd_categorize(a):
    rows, p = _targets(a)
    cat, change, mismatch, transfers = D.plan_categorize(rows, a.to)
    todo = [t for t in rows if t.id in change]
    lines = ["Categorize -> %s: %d selected, %d to change, %d already there" % (cat["path"], len(rows), len(change), len(rows) - len(change))]
    lines += _sample(todo)
    blocks = []
    if mismatch:
        msg = "%d row(s) are %s but %s is an %s category" % (len(mismatch), "/".join(sorted({t.type for t in mismatch})), cat["path"], cat["type"])
        (lines.append("  warning: " + msg + " (allowed with --force)") if a.force else blocks.append(msg + "; use --force if intended"))
    if transfers:
        lines.append("  note: %d transfer(s) selected; a category on a transfer does not make it cost (metrics.md)" % len(transfers))
    data = dict(category=cat["path"], selected=len(rows), to_change=[t.id for t in todo])
    if not change:
        emit(a, dict(data, dry_run=not a.yes, blocked=[]), lambda: "\n".join(lines + ["nothing to change"]))
        return
    if not show_plan(a, data, lines, blocks):
        return
    undo = D.update_many(D.TX, change, "categorize")
    done(a, dict(data, undo=str(undo)), "categorized %d row(s) -> %s · verified · undo: fin.py undo %s" % (len(change), cat["path"], undo))


def cmd_tag(a, remove=False):
    rows, p = _targets(a)
    tid, change = D.plan_tag(rows, a.tag_name, remove)
    verb = "untag" if remove else "tag"
    lines = ["%s %s: %d selected, %d to change" % (verb.capitalize(), a.tag_name, len(rows), len(change))] + _sample([t for t in rows if t.id in change])
    data = dict(tag=a.tag_name, selected=len(rows), to_change=list(change))
    if not change:
        emit(a, dict(data, dry_run=not a.yes, blocked=[]), lambda: "\n".join(lines + ["nothing to change"]))
        return
    if not show_plan(a, data, lines):
        return
    undo = D.update_many(D.TX, change, verb)
    done(a, dict(data, undo=str(undo)), "%sged %d row(s) · verified · undo: fin.py undo %s" % (verb, len(change), undo))


def cmd_untag(a):
    cmd_tag(a, remove=True)


def cmd_budget_set(a):
    op, rid, fields, cat, m, before = D.plan_budget(a.month, a.category_name, a.amount)
    lines = ["Budget %s · %s · %s%s" % (m.strftime("%Y-%m"), cat["path"], money(a.amount),
                                        "" if op == "create" else " (was %s)" % money(before)), "  " + op]
    data = dict(op=op, month=m.strftime("%Y-%m"), category=cat["path"], amount=a.amount, previous=before)
    if not show_plan(a, data, lines):
        return
    if op == "update":
        undo = D.update_many(D.BUD, {rid: fields}, "budget-set")
        rec = rid
    else:
        ids, undo = D.create_many(D.BUD, [fields], "budget-set")
        rec = ids[0]
    done(a, dict(data, id=rec, undo=str(undo)), "budget %s %s · %s · verified · undo: fin.py undo %s" % (op + "d", rec, money(a.amount), undo))


def cmd_payee_default(a):
    pay = D.resolve("payee", a.payee_ref)
    cat = D.resolve("category", a.category_name)
    rows = D.load_txns(None, payees=[pay["id"]])
    other = [t for t in rows if t.category_id != cat["id"] and t.type == cat["type"]]
    old = D.categories().get(pay["default"], {}).get("path") if pay["default"] else None
    lines = ["Payee %s: default category %s -> %s" % (pay["name"], old or "(none)", cat["path"]),
             "  %d of its %d transaction(s) have another or no category; to align them: fin.py categorize --to %r --payee %r" % (
                 len(other), len(rows), cat["path"], pay["name"])]
    data = dict(payee=pay["name"], old=old, new=cat["path"], other_rows=len(other))
    if pay["default"] == cat["id"]:
        emit(a, dict(data, dry_run=not a.yes, blocked=[]), lambda: "\n".join(lines[:1] + ["nothing to change"]))
        return
    if not show_plan(a, data, lines):
        return
    undo = D.update_many(D.PAY, {pay["id"]: {D.FP["default"]: {"id": cat["id"]}}}, "payee-default")
    done(a, dict(data, undo=str(undo)), "payee %s default -> %s · verified · undo: fin.py undo %s" % (pay["name"], cat["path"], undo))


def cmd_delete(a):
    ids = [x for x in " ".join(a.rec).replace(",", " ").split() if x]
    if len(ids) > 20:
        raise D.Blocked("refusing to delete %d rows at once (max 20, explicit ids only)" % len(ids))
    rows = [D.to_txn(D.T.get_record(D.TX, i, D.TX_PROJECTION)) for i in ids]
    lines = ["Delete %d transaction(s) (to the Teable trash; restore from the Teable UI, not fin.py undo)" % len(rows)] + _sample(rows, 20)
    if not show_plan(a, dict(ids=ids), lines):
        return
    D.T.delete_records(D.TX, ids)
    D.forget_lookups()
    still = D.T.get_records(D.TX, {"conjunction": "and", "filterSet": [{"fieldId": D.FX["desc"], "operator": "isNotEmpty", "value": None}]},
                            [D.FX["desc"]], take=D.ALL)
    left = sorted(set(ids) & {r["id"] for r in still})
    if left:
        raise D.Blocked("VERIFY FAILED: still present after delete: %s" % ", ".join(left))
    done(a, dict(deleted=ids), "deleted %d row(s) to the trash" % len(ids))


def cmd_undo(a):
    path = a.file
    if not path:
        files = sorted(D.UNDO_DIR.glob("*.json")) if D.UNDO_DIR.exists() else []
        if not files:
            raise D.Blocked("no undo files in %s" % D.UNDO_DIR)
        path = str(files[-1])
    plan = D.undo(path, apply=False)
    lines = ["Undo %s (%s on %s): restore %d record(s), delete %d created record(s)" % (Path(path).name, plan["op"], plan["table"], plan["restore"], plan["delete"])]
    if not show_plan(a, plan, lines):
        return
    D.undo(path, apply=True)
    Path(path).rename(Path(path).with_suffix(".undone"))
    done(a, plan, "undone · %s renamed to .undone" % Path(path).name)


# ---------- main ----------

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, **kw):
        s = sub.add_parser(name, **kw)
        s.set_defaults(fn=fn)
        s.add_argument("--json", action="store_true")
        s.add_argument("--anchor", help="YYYY-MM: treat this as the last complete month")
        g = s.add_argument_group("filters")
        g.add_argument("--type", type=lambda v: [x.strip().capitalize() for x in v.split(",")], help="Income, Expense, Transfer")
        g.add_argument("--category", type=lambda v: v.split(","))
        g.add_argument("--exclude-category", type=lambda v: v.split(","), help="drop these categories (uncategorised rows stay)")
        g.add_argument("--payee", type=lambda v: v.split(","))
        g.add_argument("--exclude-payee", type=lambda v: v.split(","), help="drop these payees (rows without a payee stay)")
        g.add_argument("--account", type=lambda v: v.split(","))
        g.add_argument("--tag", type=lambda v: v.split(","))
        g.add_argument("--text", help="every word must match description, notes or payee")
        g.add_argument("--scope", choices=["personal", "business"])
        g.add_argument("--min", type=float)
        g.add_argument("--max", type=float)
        g.add_argument("--recurring", action="store_true")
        g.add_argument("--uncategorized", action="store_true")
        g.add_argument("--include-transfers", action="store_true")
        return s

    s = add("summary", cmd_summary, help="totals for one period")
    s.add_argument("period", nargs="?")
    s = add("cost", cmd_cost, help="cost over 1/3/6/12 complete months + MTD")
    s.add_argument("--windows", default="1,3,6,12")
    s.add_argument("--by", help="category, parent, payee, tag, scope, account")
    s.add_argument("--avg", action="store_true", help="with --by: monthly averages instead of totals")
    s.add_argument("--no-mtd", action="store_true")
    s = add("trend", cmd_trend, help="month-by-month cost")
    s.add_argument("period", nargs="?")
    s.add_argument("--by")
    s.add_argument("--top", type=int, default=8)
    s = add("compare", cmd_compare, help="compare two periods")
    s.add_argument("preset", nargs="?", choices=["mom", "yoy", "3m-avg", "qoq"])
    s.add_argument("--a")
    s.add_argument("--b")
    s.add_argument("--by")
    s.add_argument("--top", type=int)
    s.add_argument("--normalize", choices=["monthly", "total"])

    s = add("breakdown", cmd_breakdown, help="totals by category, payee, tag, scope, ...")
    s.add_argument("period", nargs="?")
    s.add_argument("--by", default="category", choices=["category", "parent", "payee", "tag", "scope", "account", "weekday", "type", "month"])
    s.add_argument("--value", default="cost", choices=["cost", "income", "amount"])
    s.add_argument("--top", type=int)
    s = add("top", cmd_top, help="largest payees, categories or single transactions")
    s.add_argument("period", nargs="?")
    s.add_argument("--by", default="payee", choices=["payee", "category", "parent", "tag", "account", "txn"])
    s.add_argument("-n", type=int, default=10)
    s.add_argument("--value", default="cost", choices=["cost", "income", "amount"])
    s = add("search", cmd_search, help="find transactions by words and filters, with totals")
    s.add_argument("words", nargs="*")
    s.add_argument("--period")
    s.add_argument("--limit", type=int, default=30)

    s = add("recurring", cmd_recurring, help="subscriptions and regular payments")
    s.add_argument("period", nargs="?")
    s.add_argument("--all", action="store_true", help="include stopped ones")
    s = add("runrate", cmd_runrate, help="spending pace this month")
    s.add_argument("--month", help="YYYY-MM (default: this month)")
    s = add("budget", cmd_budget, help="budget vs actual for one month")
    s.add_argument("month", nargs="?")
    s = add("budget-suggest", cmd_budget_suggest, help="suggest monthly budgets from history")
    s.add_argument("period", nargs="?")
    s.add_argument("--method", default="median", choices=["median", "avg", "p75"])
    s.add_argument("--round", type=int, default=10)
    s = add("anomalies", cmd_anomalies, help="unusually large charges")
    s.add_argument("period", nargs="?")
    s.add_argument("--history", type=int, default=12, help="months of history before the period")
    s.add_argument("--k", type=float, default=3.0)
    s.add_argument("--min-amount", type=float, default=100.0)
    s = add("duplicates", cmd_duplicates, help="possible duplicate rows")
    s.add_argument("period", nargs="?")
    s = add("balance", cmd_balance, help="account balance by month")
    s = add("cashflow", cmd_cashflow, help="income, spend and transfers by month")
    s.add_argument("period", nargs="?")
    add("doctor", cmd_doctor, help="read-only data-quality report")
    s = add("fy", cmd_fy, help="Australian financial year and tax view")
    s.add_argument("fy", nargs="?")

    def addw(name, fn, filt=False, **kw):
        s = add(name, fn, **kw) if filt else sub.add_parser(name, **kw)
        if not filt:
            s.set_defaults(fn=fn)
            s.add_argument("--json", action="store_true")
            s.add_argument("--anchor")
        s.add_argument("--yes", action="store_true", help="write (default is a dry run)")
        return s

    s = addw("add", cmd_add, help="add one transaction")
    s.add_argument("--date", required=True)
    s.add_argument("--amount", type=float, required=True)
    s.add_argument("--type", dest="type_", default="Expense", type=str.capitalize, choices=list(D.TYPES))
    s.add_argument("--desc", required=True)
    s.add_argument("--account", dest="account_name")
    s.add_argument("--payee", dest="payee_name")
    s.add_argument("--category", dest="category_name")
    s.add_argument("--tag", dest="tags", type=lambda v: v.split(","))
    s.add_argument("--notes")
    s.add_argument("--recurring", dest="recurring_flag", action="store_true")
    s.add_argument("--frequency", choices=["Weekly", "Monthly", "Yearly"])
    s.add_argument("--transfer-account")
    s.add_argument("--allow-duplicate", action="store_true")
    s.add_argument("--force", action="store_true", help="allow an Income category on an Expense or vice versa")
    s = addw("categorize", cmd_categorize, filt=True, help="set the category of selected rows")
    s.add_argument("--to", required=True, help="target category")
    s.add_argument("--ids")
    s.add_argument("--period")
    s.add_argument("--force", action="store_true", help="allow an Expense category on Income rows or vice versa")
    for name, fn in (("tag", cmd_tag), ("untag", cmd_untag)):
        s = addw(name, fn, filt=True, help="%s selected rows" % name)
        s.add_argument("tag_name")
        s.add_argument("--ids")
        s.add_argument("--period")
    s = addw("budget-set", cmd_budget_set, help="set one category's budget for a month")
    s.add_argument("month")
    s.add_argument("--category", dest="category_name", required=True)
    s.add_argument("--amount", type=float, required=True)
    s = addw("payee-default", cmd_payee_default, help="set a payee's default category")
    s.add_argument("payee_ref")
    s.add_argument("--category", dest="category_name", required=True)
    s = addw("delete", cmd_delete, help="delete transactions by id (to the trash)")
    s.add_argument("rec", nargs="+")
    s = addw("undo", cmd_undo, help="restore an undo file")
    s.add_argument("file", nargs="?")

    a = p.parse_args()
    try:
        a.fn(a)
    except (D.NotFound, D.Ambiguous) as e:
        print(str(e), file=sys.stderr)
        sys.exit(3)
    except (ValueError, D.Blocked) as e:
        print(str(e), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
