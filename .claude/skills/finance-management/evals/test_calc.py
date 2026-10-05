#!/usr/bin/env python3
"""Offline unit tests for findata periods and fincalc (no network, no token). Run: python3 evals/test_calc.py"""
import datetime as dt, sys, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import findata as D

D_ = dt.date
TODAY = D_(2026, 10, 5)
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)))


def period(spec, **kw):
    return D.resolve_period(spec, today=TODAY, **kw)


def test_periods():
    p = period("last-month")
    check("last-month = Sep 2026", (p.start, p.end, p.months) == (D_(2026, 9, 1), D_(2026, 10, 1), 1), p)
    check("month and 1m alias last-month", period("month") == p == period("1m"))
    p = period("3m")
    check("3m = Jul..Sep complete months", (p.start, p.end, p.months) == (D_(2026, 7, 1), D_(2026, 10, 1), 3), p)
    p = period("6m")
    check("6m = Apr..Sep", (p.start, p.end) == (D_(2026, 4, 1), D_(2026, 10, 1)), p)
    p = period("12m")
    check("12m = Oct 2025..Sep 2026", (p.start, p.end, p.months) == (D_(2025, 10, 1), D_(2026, 10, 1), 12), p)
    check("year alias 12m", period("year") == p)
    p = period("3m", anchor="2026-08")
    check("3m anchored at 2026-08 = Jun..Aug", (p.start, p.end) == (D_(2026, 6, 1), D_(2026, 9, 1)), p)
    p = period("mtd")
    check("mtd = Oct 1..5 inclusive", (p.start, p.last) == (D_(2026, 10, 1), TODAY), p)
    p = period("30d")
    check("30d ends today, 30 days", (p.last, p.days) == (TODAY, 30), p)
    p = period("2026-02")
    check("YYYY-MM month", (p.start, p.end, p.months) == (D_(2026, 2, 1), D_(2026, 3, 1), 1), p)
    p = period("qtd")
    check("qtd = Q4 from Oct 1", p.start == D_(2026, 10, 1) and p.last == TODAY, p)
    check("ytd", period("ytd").start == D_(2026, 1, 1))
    p = period("2025")
    check("calendar year", (p.start, p.end) == (D_(2025, 1, 1), D_(2026, 1, 1)), p)
    p = period("fy2026")
    check("FY2026 = Jul 2025..Jun 2026", (p.start, p.end, p.months) == (D_(2025, 7, 1), D_(2026, 7, 1), 12), p)
    check("fy (today Oct 2026) = FY2027", period("fy").start == D_(2026, 7, 1))
    check("last-fy = FY2026", period("last-fy").start == D_(2025, 7, 1))
    check("fytd from Jul 1 to today", (period("fytd").start, period("fytd").last) == (D_(2026, 7, 1), TODAY))
    p = period("2026-01-15..2026-02-14")
    check("date range inclusive", (p.start, p.last, p.days) == (D_(2026, 1, 15), D_(2026, 2, 14), 31), p)
    p = period("2026-01..2026-03")
    check("month range", (p.start, p.end, p.months) == (D_(2026, 1, 1), D_(2026, 4, 1), 3), p)
    check("non-aligned months fractional", abs(period("30d").months - 30 / 30.4375) < 1e-9)
    for bad in ("fortnight", "2026-13", "2026-03..2026-01"):
        try:
            period(bad)
            check("rejects %r" % bad, False, "no error")
        except ValueError:
            check("rejects %r" % bad, True)
    check("january wraps to previous year", D.resolve_period("3m", today=D_(2026, 1, 10)).start == D_(2025, 10, 1))


def test_instants():
    check("instant AEST (winter) = 14:00Z previous day", D.instant(D_(2026, 8, 24)) == "2026-08-23T14:00:00.000Z")
    check("instant AEDT (summer) = 13:00Z previous day", D.instant(D_(2026, 1, 1)) == "2025-12-31T13:00:00.000Z")
    check("instant on DST start day (2026-10-04) uses +10", D.instant(D_(2026, 10, 4)) == "2026-10-03T14:00:00.000Z")
    check("instant the day after DST start uses +11", D.instant(D_(2026, 10, 5)) == "2026-10-04T13:00:00.000Z")


def test_local_dates():
    import teable as T
    check("UTC-midnight import reads as same local day", T.local_date("2026-08-31T00:00:00.000Z") == D_(2026, 8, 31))
    check("Melbourne-midnight entry reads as next UTC day", T.local_date("2026-08-31T14:00:00.000Z") == D_(2026, 9, 1))


# ---------- fincalc on fixture rows ----------

import fincalc as C


def T_(day, typ, amt, cat=None, payee=None, tags=(), transfer_account=None, scope=None):
    t = D.Txn(id="rec%s" % abs(hash((day, typ, amt, cat, payee))), date=day, type=typ, amount=amt, category=cat, payee=payee,
              tags=tuple(tags), transfer_account=transfer_account, account_scope="Personal")
    t.category_scope = scope
    return t


FIX = [
    T_(D_(2026, 7, 3), "Expense", 100.0, "Food", "Coles"),
    T_(D_(2026, 7, 31), "Expense", 50.0, "Dining & Takeaway", "KFC", tags=("Tax Deductible",)),
    T_(D_(2026, 8, 1), "Expense", 200.0, "Food", "Woolworths"),
    T_(D_(2026, 8, 15), "Income", 30.0, "Refunds", "Kmart"),
    T_(D_(2026, 8, 20), "Income", 1000.0, "Business Income", "Client A", scope="Business"),
    T_(D_(2026, 9, 2), "Transfer", 500.0),
    T_(D_(2026, 9, 3), "Transfer", 70.0, transfer_account="Savings"),
    T_(D_(2026, 9, 30), "Expense", 10.01, "Subscriptions & Software", "Cloudflare", scope="Business"),
    T_(D_(2026, 10, 2), "Expense", 5.0, "Food", "Coles"),
]


def test_roles():
    check("refund is negative cost", C.cost_value(FIX[3]) == -30.0)
    check("income is not cost", C.cost_value(FIX[4]) == 0.0)
    check("external transfer not cost by default", C.cost_value(FIX[5]) == 0.0)
    check("external transfer cost with include_transfers", C.cost_value(FIX[5], True) == 500.0)
    check("internal transfer never cost", C.cost_value(FIX[6], True) == 0.0)


def test_summarize():
    s = C.summarize(FIX[:8])
    check("expense", s["expense"] == 360.01, s)
    check("refunds", s["refunds"] == 30.0, s)
    check("net spend = expense - refunds", s["net_spend"] == 330.01, s)
    check("income excludes refunds", s["income"] == 1000.0, s)
    check("transfers out excludes internal", (s["transfers_out"], s["internal_transfers"]) == (500.0, 70.0), s)
    check("net cash flow", s["net_cash_flow"] == round(1000 + 30 - 360.01 - 500, 2), s)
    check("savings rate", s["savings_rate"] == round(100 * (1000 - 330.01) / 1000, 2), s)
    s = C.summarize(FIX[:8], include_transfers=True)
    check("net spend incl transfers", s["net_spend"] == 830.01, s)
    check("no income -> savings rate None", C.summarize(FIX[:3])["savings_rate"] is None)


def test_windows():
    res = {r["window"]: r for r in C.cost_windows(FIX, (1, 3), today=TODAY)}
    one = res["2026-09"]
    check("1m = Sep only", (one["net_spend"], one["count"]) == (10.01, 1), one)
    three = res["3 months 2026-07..2026-09"]
    check("3m = Jul..Sep net spend", three["net_spend"] == 330.01, three)
    check("3m monthly avg", three["monthly_avg"] == round(330.01 / 3, 2), three)
    mtd = [r for r in res.values() if "MTD" in r["window"]][0]
    check("MTD separate", mtd["net_spend"] == 5.0, mtd)
    check("month boundary: Jul 31 in Jul, Aug 1 in Aug",
          [C.cost(FIX, D.resolve_period(m, today=TODAY))["net_spend"] for m in ("2026-07", "2026-08")] == [150.0, 170.0])


def test_series_and_groups():
    p = D.resolve_period("3m", today=TODAY)
    ser = C.monthly_series(FIX, p, "category")
    check("months zero-filled", ser["months"] == ["2026-07", "2026-08", "2026-09"], ser)
    check("totals per month", ser["total"] == [150.0, 170.0, 10.01], ser)
    check("refund appears as negative group", ser["series"]["Refunds"] == [0.0, -30.0, 0.0], ser)
    g = C.group_values(FIX, "tag")
    check("tag grouping", g["Tax Deductible"][0] == 50.0 and "(untagged)" in g, dict(g))
    g = C.group_values(C.within(FIX, p), "scope")
    check("scope from category, fallback account", (round(g["Business"][0], 2), g["Personal"][0]) == (10.01, 320.0), dict(g))
    check("rolling avg", C.rolling_avg([3, 6, 9, 12], 3) == [None, None, 6.0, 9.0])
    st = C.trend_stats([100, 200, 300])
    check("trend slope", st["slope_per_month"] == 100.0 and st["mean"] == 200.0, st)
    s = C.monthly_series(FIX, p, "payee", top=1)
    check("top folds into (other)", list(s["series"]) == ["Woolworths", "(other)"], s)


def test_compare():
    pa = D.resolve_period("2026-08", today=TODAY)
    pb = D.resolve_period("2026-07", today=TODAY)
    r = C.compare(FIX, pa, FIX, pb, "category")
    check("compare totals", (r["total"]["a"], r["total"]["b"], r["total"]["delta"]) == (170.0, 150.0, 20.0), r["total"])
    food = [x for x in r["rows"] if x["group"] == "Food"][0]
    check("compare group delta %", (food["delta"], food["delta_pct"]) == (100.0, 100.0), food)
    q = C.compare(FIX, pa, FIX, D.resolve_period("2026-06..2026-07", today=TODAY))
    check("different lengths normalise monthly", q["normalize"] == "monthly" and q["total"]["b"] == 75.0, q["total"])
    a, b = C.compare_preset("yoy", today=TODAY)
    check("yoy preset", (a.start, b.start) == (D_(2026, 9, 1), D_(2025, 9, 1)))
    a, b = C.compare_preset("3m-avg", today=TODAY)
    check("3m-avg preset", (b.start, b.end, b.months) == (D_(2026, 6, 1), D_(2026, 9, 1), 3))


def test_breakdown_top_search():
    p = D.resolve_period("3m", today=TODAY)
    rows = C.within(FIX, p)
    b = C.breakdown(rows, "category")
    check("breakdown sorted, refunds negative last", b[0]["group"] == "Food" and b[-1]["group"] == "Refunds", b)
    check("breakdown shares sum to 100", abs(sum(r["share"] for r in b) - 100) < 0.05, b)
    food = b[0]
    check("breakdown food row", (food["total"], food["count"], food["avg"], food["first"], food["last"]) ==
          (300.0, 2, 150.0, "2026-07-03", "2026-08-01"), food)
    inc = C.breakdown(rows, "category", "income")
    check("income breakdown excludes refunds", [r["group"] for r in inc] == ["Business Income"], inc)
    t = C.top(rows, "txn", 2)
    check("top txn by amount, cost rows only", [x["amount"] for x in t] == [200.0, 100.0], t)
    t = C.top(rows, "txn", 1, include_transfers=True)
    check("top txn with transfers", t[0]["amount"] == 500.0, t)
    check("top payee", C.top(rows, "payee", 1)[0]["group"] == "Woolworths")
    s = C.search_summary([x for x in rows if x.category == "Food"], p)
    check("search summary spent and months spanned", (s["spent"], s["months_spanned"], s["spent_per_month"]) == (300.0, 2, 150.0), s)
    check("search summary empty", C.search_summary([], p)["count"] == 0)


def _sub(payee, desc, amount, months, day=10, flagged=False, start=(2026, 1)):
    out = []
    for i in range(months):
        d = D.add_months(D_(start[0], start[1], day), i)
        t = T_(d, "Expense", amount + (0.0 if i % 2 else 0.01 * i), "Subscriptions & Software", payee)
        t.description, t.recurring, t.id = desc, flagged, "rec%s%02d%s" % (payee[:4], i, desc[:3])
        out.append(t)
    return out


def test_recurring():
    rows = _sub("Netflix", "NETFLIX.COM", 22.99, 8) + _sub("Gym", "GYM DD", 60.0, 5, flagged=True, start=(2026, 1))
    # one payee, two plans with different descriptions on different days -> irregular as a whole, split by description
    rows += _sub("Allianz", "ALLIANZ CAR", 117.31, 8, day=3) + _sub("Allianz", "ALLIANZ HOME", 119.03, 8, day=20)
    # groceries: frequent, irregular amounts -> not recurring
    for i in range(30):
        rows.append(T_(D_(2026, 1, 1) + dt.timedelta(days=i * 3 + (i % 2)), "Expense", 10 + 7 * (i % 5), "Food", "Coles"))
    rec = {r["payee"]: r for r in C.recurring(rows, as_of=D_(2026, 8, 20))}
    check("monthly subscription inferred", rec["Netflix"]["cadence"] == "monthly" and rec["Netflix"]["inferred"], rec.get("Netflix"))
    check("annualised", rec["Netflix"]["annual"] == round(rec["Netflix"]["monthly"] * 12, 2))
    check("flagged but stopped", rec["Gym"]["status"] == "stopped" and rec["Gym"]["flagged"], rec.get("Gym"))
    check("active within tolerance", rec["Netflix"]["status"] == "active", rec["Netflix"])
    names = sorted(k for k in rec if k.startswith("Allianz"))
    check("same payee split into two plans", len(names) == 2 and all(" · " in n for n in names), names)
    check("groceries not recurring", "Coles" not in rec)
    late = C.recurring(_sub("Spotify", "SPOTIFY", 11.99, 6), as_of=D_(2026, 7, 25))
    check("late when overdue past tolerance", late[0]["status"] == "late", late)
    up = _sub("Disney", "DISNEY", 13.99, 5)
    up[-1].amount = 17.99
    chg = C.recurring(up, as_of=D_(2026, 5, 15))[0]["price_change"]
    check("price change detected", chg and chg["now"] == 17.99 and chg["pct"] > 25, chg)


def test_run_rate():
    month = D.resolve_period("2026-08", today=TODAY)
    rr = C.run_rate(FIX, month, D_(2026, 8, 10), baseline=300.0, budget_total=400.0)
    check("run rate spent to as_of", (rr["spent"], rr["elapsed_days"]) == (200.0, 10), rr)
    check("run rate projection", rr["projected"] == round(200 / 10 * 31, 2), rr)
    check("run rate vs baseline and budget", (rr["vs_baseline"], rr["budget_left"]) == (round(620 - 300, 2), 200.0), rr)
    check("run rate before month starts", C.run_rate(FIX, month, D_(2026, 7, 20))["elapsed_days"] == 0)


def test_budgets():
    for t in FIX:
        t.category_id = {"Food": "recFood", "Dining & Takeaway": "recDine", "Refunds": "recRef"}.get(t.category, t.category_id)
    cats = {"recFood": dict(path="Food"), "recDine": dict(path="Dining & Takeaway"), "recRef": dict(path="Refunds")}
    buds = {"b1": dict(month=D_(2026, 8, 1), category="recFood", planned=150.0), "b2": dict(month=D_(2026, 7, 1), category="recFood", planned=999.0)}
    r = C.budget_vs_actual(FIX, D.resolve_period("2026-08", today=TODAY), buds, cats)
    food = [x for x in r["rows"] if x["category"] == "Food"][0]
    check("budget over, other months ignored", (food["planned"], food["actual"], food["status"]) == (150.0, 200.0, "over"), food)
    check("unbudgeted rows listed", any(x["status"] == "unbudgeted" for x in r["rows"]), r["rows"])
    sug = C.budget_suggest(FIX, D.resolve_period("3m", today=TODAY), "median")
    f = [x for x in sug["rows"] if x["category"] == "Food"][0]
    check("suggest median incl zero months, rounded up", (f["median"], f["suggested"], f["months_with_spend"]) == (100.0, 100.0, 2), f)
    check("suggest skips refunds", all(x["category"] != "Refunds" for x in sug["rows"]))


def test_duplicates_anomalies():
    a = T_(D_(2026, 8, 5), "Expense", 19.05, "Food", "Woolworths")
    b = T_(D_(2026, 8, 5), "Expense", 19.05, "Food", "Woolworths")
    b.id = "recOther"
    d = C.duplicates([a, b, T_(D_(2026, 8, 6), "Expense", 19.05, "Food", "Woolworths")])
    check("duplicates same day only", len(d) == 1 and d[0]["count"] == 2, d)
    a.description = b.description = "WOOLWORTHS/SHOP 1200"
    c = T_(D_(2026, 8, 5), "Expense", 2.5, "Food", "Coles"); c.description = "COLES 7682 STH MELBOURNE"
    e = T_(D_(2026, 8, 5), "Expense", 2.5, "Food", "Coles"); e.description, e.id = "COLES 7735 DONCASTER", "recColes2"
    rev = T_(D_(2026, 8, 5), "Income", 19.05, "Refunds", "Woolworths"); rev.description, rev.id = "REV VISA DEBIT PURCHASE", "recRev"
    d = C.duplicates([a, b, c, e, rev])
    check("different descriptions (two stores) are not duplicates", all(x["payee"] != "Coles" for x in d), d)
    check("double charge with same-day reversal is marked", d and d[0]["reversed_by"] == ["recRev"], d)
    hist = [T_(D_(2026, 1, 1) + dt.timedelta(days=i), "Expense", 20.0 + i % 3, "Shopping", "Kmart") for i in range(10)]
    cur = [T_(D_(2026, 8, 1), "Expense", 250.0, "Shopping", "Kmart"), T_(D_(2026, 8, 2), "Expense", 45.0, "Shopping", "Kmart"),
           T_(D_(2026, 8, 3), "Expense", 300.0, "Travel", "New Airline")]
    an = C.anomalies(cur, hist, min_amount=40)
    check("anomaly vs payee median", any(x["payee"] == "Kmart" and x["amount"] == 250.0 for x in an), an)
    check("normal amount not flagged", not any(x["amount"] == 45.0 for x in an), an)
    check("new payee large first payment", any("first payment" in x["reason"] for x in an), an)


def test_balance_cashflow_fy():
    acc = dict(id="recAcc", name="ANZ", opening=1000.0, opening_date=D_(2026, 6, 30), type="Checking", balance=None)
    rows = [T_(D_(2026, 7, 1), "Income", 500.0, "Salary"), T_(D_(2026, 7, 2), "Expense", 2000.0, "Rent"),
            T_(D_(2026, 8, 1), "Transfer", 100.0, transfer_account="Savings")]
    for t in rows:
        t.account_id = "recAcc"
    inbound = T_(D_(2026, 8, 2), "Transfer", 40.0, transfer_account="ANZ")
    inbound.account_id = "recOtherAcc"
    b = C.balance_series(rows + [inbound], acc)
    check("balance = opening + signed + transfers in", b["final"] == 1000 + 500 - 2000 - 100 + 40, b)
    check("month-end points", [m["balance"] for m in b["months"]] == [-500.0, -560.0], b["months"])
    check("negative checking warns", any("negative" in w for w in b["warnings"]), b["warnings"])
    cf = C.cash_flow(FIX, D.resolve_period("3m", today=TODAY))
    check("cash flow per month", [r["net_spend"] for r in cf] == [150.0, 170.0, 10.01] and cf[1]["income"] == 1000.0, cf)
    fy = C.fy_report(FIX, D.resolve_period("fy2027", today=TODAY))
    check("fy business split", (fy["business_income"], fy["business_expense_total"]) == (1000.0, 10.01), (fy["business_income"], fy["business_expense_total"]))
    check("fy tagged totals", fy["tagged"]["Tax Deductible"]["total"] == 50.0, fy["tagged"])


def test_iteration2():
    inc = T_(D_(2026, 9, 9), "Transfer", 1000.0)
    inc.description = "TRANSFER 509564 FROM 807590005"
    out = T_(D_(2026, 9, 1), "Transfer", 5200.0)
    out.description = "TRANSFER 587524 TO 013148807590005"
    check("incoming transfer detected", C.is_incoming(inc) and not C.is_incoming(out))
    check("incoming never cost, even with transfers included", C.cost_value(inc, True) == 0.0 and C.cost_value(out, True) == 5200.0)
    s = C.summarize([inc, out])
    check("summary splits transfers in/out", (s["transfers_out"], s["transfers_in"], s["net_cash_flow"]) == (5200.0, 1000.0, -4200.0), s)
    acc = dict(id="recAcc", name="ANZ", opening=0.0, opening_date=D_(2026, 8, 31), type="Checking", balance=None)
    for t in (inc, out):
        t.account_id = "recAcc"
    b = C.balance_series([inc, out], acc)
    check("balance corrects incoming transfers", (b["final"], b["formula_balance"], b["incoming_transfers"]) == (-4200.0, -6200.0, 1), b)
    check("balance warns about formula", any("incoming transfer" in w for w in b["warnings"]), b["warnings"])
    # 4-weekly billing
    four = []
    for i in range(10):
        t = T_(D_(2026, 1, 5) + dt.timedelta(days=28 * i), "Expense", 25.0, "Utilities", "Amaysim")
        t.id = "recAmay%02d" % i
        four.append(t)
    r = C.recurring(four, as_of=four[-1].date)[0]
    check("4-weekly cadence, 13 charges a year", r["cadence"] == "4-weekly" and abs(r["annual"] - 25.0 * 365.25 / 28) < 0.02, r)
    # regular transfers out and payments to people are kind 'transfer'
    tr = []
    for i in range(5):
        t = T_(D_(2026, 3, 9) + dt.timedelta(days=30 * i), "Transfer", 2357.36)
        t.description, t.id = "TO WANG JUNYANG", "recWang%02d" % i
        tr.append(t)
    ppl = _sub("Aiyun Yu", "TO AIYUN YU", 2816.0, 5)
    for t in ppl:
        t.category = "Personal Transfers"
    kinds = {r["payee"]: r["kind"] for r in C.recurring(tr + ppl + _sub("Netflix", "NETFLIX.COM", 22.99, 5), as_of=D_(2026, 7, 20))}
    check("regular transfer detected as kind transfer", kinds.get("transfer: TO WANG JUNYANG") == "transfer", kinds)
    check("payments to people are kind transfer, bills are bill", (kinds.get("Aiyun Yu"), kinds.get("Netflix")) == ("transfer", "bill"), kinds)
    # irregular bills: bill-like categories not already recurring, in the last 12 months
    rego = T_(D_(2026, 1, 27), "Expense", 875.48, "Vehicle & Rego", "VicRoads")
    food = T_(D_(2026, 2, 1), "Expense", 50.0, "Food", "Coles")
    old = T_(D_(2025, 1, 1), "Expense", 99.0, "Utilities", "Old Power")
    nf = _sub("Netflix", "NETFLIX.COM", 22.99, 5)
    ir = C.irregular_bills([rego, food, old] + nf, D_(2026, 9, 18), C.recurring(nf, D_(2026, 6, 1)))
    check("irregular bills: annual rego in, food out, old out, recurring out", [r["payee"] for r in ir["items"]] == ["VicRoads"], ir)


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except Exception:
                check(name + " raised", False, traceback.format_exc())
    failed = [n for n, ok in RESULTS if not ok]
    print("\n%d/%d passed" % (len(RESULTS) - len(failed), len(RESULTS)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
