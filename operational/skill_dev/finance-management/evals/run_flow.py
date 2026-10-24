#!/usr/bin/env python3
"""Live acceptance test for finance-management. Run from the repo root: python3 skill_dev/finance-management/evals/run_flow.py

A. teable.py is identical to the project-management copy (below its header line).
B. Reads: cost windows and summaries match the server aggregation endpoint to the cent; local-date month
   boundaries agree with server counts; coverage; resolve never guesses.
C. Writes, isolated: creates an inactive "[TEST] Account" plus [TEST] categories, payee and tags, runs the
   CLI end to end (dry-run default, --yes, blocks, read-back, undo, delete), then deletes every [TEST] row in
   a `finally` and checks that every finance table is back to its starting row count.
Undo files go to a temporary FIN_UNDO_DIR, never the user's.
"""
import json, os, subprocess, sys, tempfile, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
UNDO = tempfile.mkdtemp(prefix="fin-undo-")
os.environ["FIN_UNDO_DIR"] = UNDO
import findata as D
import fincalc as C

T = D.T
RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(detail)[:400]))


def fin(*args):
    """Run the CLI with --json; returns (exit code, parsed JSON or raw text)."""
    p = subprocess.run([sys.executable, str(SCRIPTS / "fin.py"), *args, "--json"], capture_output=True, text=True,
                       env=dict(os.environ, FIN_UNDO_DIR=UNDO))
    out = p.stdout.strip()
    try:
        return p.returncode, json.loads(out) if out else p.stderr.strip()
    except ValueError:
        return p.returncode, out + p.stderr


TABLES = dict(transactions=D.TX, accounts=D.ACC, categories=D.CAT, payees=D.PAY, tags=D.TAG, budgets=D.BUD)


PRIMARY = {D.TX: D.FX["desc"], D.ACC: D.FA["name"], D.CAT: D.FC["name"], D.PAY: D.FP["name"], D.TAG: D.FG["name"], D.BUD: D.FB["month"]}


def counts():
    return {k: len(T.get_records(t, projection=[PRIMARY[t]], take=D.ALL)) for k, t in TABLES.items()}


def tx_ids():
    return {r["id"] for r in T.get_records(D.TX, projection=[D.FX["desc"]], take=D.ALL)}


# ---------- A ----------

def part_a():
    pm = HERE.parent.parent / "project-management" / "scripts" / "teable.py"
    mine = (SCRIPTS / "teable.py").read_text().split("\n", 1)[1]
    check("teable.py identical to project-management copy (below header)", pm.is_file() and mine == pm.read_text())


# ---------- B ----------

def part_b():
    ps = C.window_periods((1, 3, 6, 12)) + [D.resolve_period(x) for x in ("fy2026", "2026-01", "2026-08", "all")]
    rows = D.load_txns(C.span(*ps))
    for p in ps:
        mine = C.cost(rows, p)["net_spend"]
        srv = round(D.server_sum(p, types=["Expense"]) - D.server_sum(p, types=["Income"], categories=["Refunds"]), 2)
        check("net spend == server aggregation · %s" % p.label, mine == srv, (mine, srv))
    p = D.resolve_period("12m")
    s = C.summarize(C.within(rows, p))
    srv_inc = round(D.server_sum(p, types=["Income"]) - D.server_sum(p, types=["Income"], categories=["Refunds"]), 2)
    check("income (refunds excluded) == server", s["income"] == srv_inc, (s["income"], srv_inc))
    srv_tr = D.server_sum(p, types=["Transfer"])
    check("transfers out + in == server Transfer total", round(s["transfers_out"] + s["transfers_in"] + s["internal_transfers"], 2) == srv_tr,
          (s["transfers_out"], s["transfers_in"], srv_tr))
    # every month: client rows by local date == server rows for that month (instant boundaries)
    allrows = D.load_txns(D.resolve_period("all"))
    by_month = {}
    for t in allrows:
        by_month[t.date.strftime("%Y-%m")] = by_month.get(t.date.strftime("%Y-%m"), 0) + 1
    bad = []
    for m, n in sorted(by_month.items()):
        got = len(T.get_records(D.TX, D.build_filter(D.resolve_period(m)), [D.FX["date"]], take=D.ALL))
        if got != n:
            bad.append((m, n, got))
    check("server month filters match local dates for all %d months" % len(by_month), not bad, bad)
    check("full read returns every row (take=ALL)", len(allrows) == counts()["transactions"])
    cov = D.coverage()
    check("coverage first/last", cov["first"] == min(t.date for t in allrows) and cov["last"] == max(t.date for t in allrows), cov)
    for kind, ref, exc in (("category", "insur", D.Ambiguous), ("category", "zzzz-none", D.NotFound)):
        try:
            D.resolve(kind, ref)
            check("resolve %r raises %s" % (ref, exc.__name__), False, "no error")
        except exc:
            check("resolve %r raises %s" % (ref, exc.__name__), True)
    before = counts()
    code, out = fin("doctor")
    groups = {g["group"] for g in out["findings"]} if code == 0 else set()
    check("doctor runs read-only and reports groups", code == 0 and groups and counts() == before, (code, groups))
    check("doctor items carry a fix", code == 0 and all(g["fix"] for g in out["findings"]))
    code, out = fin("search", "woolworths", "--period", "2026-08")
    check("text search uses <= 2 HTTP calls", code == 0 and out["basis"]["http_calls"] <= 2, out if code else out["basis"])


# ---------- C ----------

def create(table, fields):
    return T.call("POST", "/api/table/%s/record" % table, body={"fieldKeyType": "id", "typecast": False,
                                                                 "records": [{"fields": fields}]})["records"][0]["id"]


def part_c(created):
    D.forget_lookups()
    acc = create(D.ACC, {D.FA["name"]: "[TEST] Account", D.FA["type"]: "Checking", D.FA["scope"]: "Personal",
                         D.FA["opening"]: 100, D.FA["opening_date"]: "2026-10-01", D.FA["active"]: False})
    created[D.ACC].append(acc)
    cexp = create(D.CAT, {D.FC["name"]: "[TEST] Expense Cat", D.FC["type"]: "Expense", D.FC["scope"]: "Personal"})
    cinc = create(D.CAT, {D.FC["name"]: "[TEST] Income Cat", D.FC["type"]: "Income", D.FC["scope"]: "Business"})
    created[D.CAT] += [cexp, cinc]
    pay = create(D.PAY, {D.FP["name"]: "[TEST] Payee", D.FP["type"]: "Store", D.FP["scope"]: "Personal"})
    created[D.PAY].append(pay)
    tag1 = create(D.TAG, {D.FG["name"]: "[TEST] Tag One", D.FG["color"]: "Blue"})
    tag2 = create(D.TAG, {D.FG["name"]: "[TEST] Tag Two", D.FG["color"]: "Green"})
    created[D.TAG] += [tag1, tag2]
    base = counts()

    # payee default, then add infers the category from it
    code, out = fin("payee-default", "[TEST] Payee", "--category", "[TEST] Expense Cat")
    check("payee-default dry run writes nothing", code == 0 and out["dry_run"] and not T.get_record(D.PAY, pay, [D.FP["default"]])["fields"].get(D.FP["default"]), out)
    code, out = fin("payee-default", "[TEST] Payee", "--category", "[TEST] Expense Cat", "--yes")
    got = T.get_record(D.PAY, pay, [D.FP["default"]])["fields"].get(D.FP["default"])
    check("payee-default --yes sets and verifies", code == 0 and got and got["id"] == cexp, (code, out, got))

    add = ["add", "--date", "2026-10-03", "--amount", "42.10", "--desc", "[TEST] SHOP ONE", "--account", "[TEST] Account", "--payee", "[TEST] Payee"]
    code, out = fin(*add)
    check("add dry run creates nothing", code == 0 and out["dry_run"] and counts()["transactions"] == base["transactions"], out)
    check("add infers category from payee default", code == 0 and out["preview"]["category"] == "[TEST] Expense Cat", out)
    code, out = fin(*add, "--yes")
    check("add --yes creates one verified row", code == 0 and len(out.get("created", [])) == 1, out)
    t1 = out["created"][0] if code == 0 else None
    if t1:
        created[D.TX].append(t1)
        r = D.to_txn(T.get_record(D.TX, t1, D.TX_PROJECTION))
        check("stored row reads back as written (local date, amount, links)",
              (str(r.date), r.amount, r.category_id, r.payee_id, r.account_id) == ("2026-10-03", 42.10, cexp, pay, acc), r)
        add_undo = out["undo"]
    code, out = fin(*add, "--yes")
    check("duplicate add is blocked (exit 2)", code == 2 and "possible duplicate" in json.dumps(out), (code, out))
    code, out = fin("add", "--date", "2026-10-04", "--amount", "5", "--desc", "[TEST] BAD", "--account", "[TEST] Account",
                    "--category", "[TEST] Income Cat", "--yes")
    check("expense with income category is blocked", code == 2, (code, out))
    code, out = fin("add", "--date", "2026-10-04", "--amount", "7.5", "--desc", "[TEST] NO CAT", "--account", "[TEST] Account", "--yes")
    t2 = out["created"][0] if code == 0 else None
    check("add without category (warns) creates", bool(t2), out)
    if t2:
        created[D.TX].append(t2)

    # categorize with undo
    code, out = fin("categorize", "--to", "[TEST] Income Cat", "--ids", t2, "--yes")
    check("categorize type mismatch blocked", code == 2, (code, out))
    code, out = fin("categorize", "--to", "[TEST] Expense Cat", "--ids", t2, "--yes")
    check("categorize --yes sets category", code == 0 and D.to_txn(T.get_record(D.TX, t2, D.TX_PROJECTION)).category_id == cexp, out)
    code, out = fin("categorize", "--to", "[TEST] Expense Cat", "--ids", t2)
    check("categorize again: nothing to change", code == 0 and out["to_change"] == [], out)
    code, out = fin("undo")
    check("undo dry run", code == 0 and out["dry_run"] and out["restore"] == 1, out)
    code, out = fin("undo", "--yes")
    check("undo restores previous (empty) category", code == 0 and D.to_txn(T.get_record(D.TX, t2, D.TX_PROJECTION)).category_id is None, out)

    # tags append, never replace; untag removes one
    fin("tag", "[TEST] Tag One", "--ids", "%s,%s" % (t1, t2), "--yes")
    code, out = fin("tag", "[TEST] Tag Two", "--ids", t1, "--yes")
    tags1 = sorted(x["id"] for x in T.get_record(D.TX, t1, [D.FX["tags"]])["fields"].get(D.FX["tags"]) or [])
    check("tag appends (both tags kept)", tags1 == sorted([tag1, tag2]), tags1)
    code, out = fin("tag", "[TEST] Tag One", "--ids", t1)
    check("tag already present: nothing to change", code == 0 and out["to_change"] == [], out)
    code, out = fin("untag", "[TEST] Tag One", "--ids", t1, "--yes")
    tags1 = [x["id"] for x in T.get_record(D.TX, t1, [D.FX["tags"]])["fields"].get(D.FX["tags"]) or []]
    check("untag removes only that tag", tags1 == [tag2], tags1)
    code, out = fin("search", "--tag", "[TEST] Tag One")
    check("search by tag finds the tagged row", code == 0 and [x["id"] for x in out["transactions"]] == [t2], out)

    # budgets: create then update the same row
    code, out = fin("budget-set", "2026-10", "--category", "[TEST] Expense Cat", "--amount", "100", "--yes")
    b1 = out.get("id") if code == 0 else None
    if b1:
        created[D.BUD].append(b1)
    code, out = fin("budget-set", "2026-10", "--category", "[TEST] Expense Cat", "--amount", "150", "--yes")
    check("budget-set updates the existing row", code == 0 and out["op"] == "update" and out["id"] == b1, out)
    code, out = fin("budget", "2026-10")
    row = [r for r in out["budget"]["rows"] if r["category"] == "[TEST] Expense Cat"] if code == 0 else []
    check("budget vs actual uses category + month", row and row[0]["planned"] == 150.0 and row[0]["actual"] == 42.10, row or out)

    # reports on the test account
    code, out = fin("search", "--account", "[TEST] Account", "--period", "2026-10")
    check("search by account totals", code == 0 and out["summary"]["count"] == 2 and out["summary"]["spent"] == 49.60, out if code else out["summary"])
    code, out = fin("balance", "--account", "[TEST] Account")
    check("balance = opening + signed rows", code == 0 and out["accounts"][0]["final"] == round(100 - 42.10 - 7.5, 2), out)
    acc_bal = T.get_record(D.ACC, acc, [D.FA["balance"]])["fields"].get(D.FA["balance"])
    check("matches the Current Balance formula", acc_bal is not None and abs(acc_bal - (100 - 49.60)) < 0.01, acc_bal)

    # undo an add (deletes the created row), then delete the other row
    code, out = fin("undo", add_undo, "--yes")
    gone = t1 not in tx_ids()
    check("undo of add deletes the created row", code == 0 and gone, out)
    if gone:
        created[D.TX].remove(t1)
    code, out = fin("delete", t2)
    check("delete dry run", code == 0 and out["dry_run"], out)
    code, out = fin("delete", t2, "--yes")
    check("delete --yes removes the row", code == 0 and t2 not in tx_ids(), out)
    if code == 0:
        created[D.TX].remove(t2)
    code, out = fin("categorize", "--to", "Food")
    check("bulk write without a selector is refused", code == 2, (code, out))


def cleanup(created, baseline):
    for table in (D.TX, D.BUD, D.PAY, D.TAG, D.CAT, D.ACC):  # children first
        ids = [i for i in created.get(table, []) if i]
        if ids:
            try:
                T.delete_records(table, ids)
            except SystemExit as e:
                print("cleanup failed on %s %s: %s" % (table, ids, e))
    def strays():
        out = []
        for name, table in TABLES.items():
            prim = PRIMARY[table] if table != D.BUD else None
            if prim:
                out += [(table, r["id"]) for r in T.get_records(table, {"conjunction": "and", "filterSet": [
                    {"fieldId": prim, "operator": "contains", "value": "[TEST]"}]}, [prim], take=D.ALL)]
        return out
    for table, rid in strays():  # rows whose id was lost (e.g. a create that failed its read-back)
        print("cleanup: removing stray %s %s" % (table, rid))
        T.delete_records(table, [rid])
    left = strays()
    check("no [TEST] rows left", not left, left)
    check("every finance table back to its starting row count", counts() == baseline, (counts(), baseline))


def main():
    part_a()
    part_b()
    baseline = counts()
    created = {t: [] for t in TABLES.values()}
    try:
        part_c(created)
    except Exception:
        check("write flow raised", False, traceback.format_exc())
    finally:
        cleanup(created, baseline)
    failed = [n for n, ok in RESULTS if not ok]
    print("\n%d/%d passed" % (len(RESULTS) - len(failed), len(RESULTS)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
