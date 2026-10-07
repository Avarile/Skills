#!/usr/bin/env python3
"""Close-out helpers (read-only): finalize criteria and actual-vs-estimate statistics.

  close.py check <projectRecId>   criteria for `finalized`; exit 1 if any fail
  close.py stats <projectRecId>   actuals vs the Charter estimate, on-time rate, slipped tasks, and the
                                  estimation-norms row to append (via write.py ctx-append) to the norms knowledge entry

Reads `Shape: <template>` and the Charter line `- Estimate: best 20d / likely 28d / worst 40d; buffer 20%`
from the project context. Units: d (default) or w (x7). Dates come from started_at / finished_at (Melbourne).
"""
import argparse, json, re, sys
import teable as T
import rollup as R

STARTED, FINISHED = "fldj3Xb1g9nUX4iFqE0", "fldn95wbkTqefn18WdO"
REFER = "fldCw3cnpw8EWs09C1v"


def days(txt, key):
    m = re.search(r"%s\s*[:=]?\s*(\d+(?:\.\d+)?)\s*([dw])?" % key, txt, re.I)
    return float(m.group(1)) * (7 if (m.group(2) or "d").lower() == "w" else 1) if m else None


def load(pid):
    proj = T.get_record(R.PROJECTS, pid)
    rows = T.get_records(R.TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid)]))
    tasks = []
    for r in rows:
        t = R.parse_task(r, None)
        t["start"], t["finish"] = T.local_date(r["fields"].get(STARTED)), T.local_date(r["fields"].get(FINISHED))
        tasks.append(t)
    return proj, [t for t in tasks if t["active"]]


def meaningful(txt):
    body = [l.strip() for l in (txt or "").splitlines() if l.strip()]
    return bool(body) and not all(re.fullmatch(r"(tbd|todo|-|\.\.\.|n/a)", b.lower()) for b in body)


def check(pid):
    proj, tasks = load(pid)
    ctx = proj["fields"].get(R.PF["ctx"]) or ""
    live = [t for t in tasks if t["prog"] != "cancelled"]
    open_ = [t for t in live if t["prog"] not in R.DONE_T]
    nofin = [t for t in live if t["prog"] in R.DONE_T and not t["finish"]]
    links = proj["fields"].get(R.PF.get("refer", "fldCw3cnpw8EWs09C1v")) or []
    est_rows = [r for r in R.table_rows(R.section(ctx, "## Estimation Record"))[1:]]
    crit = [
        ("all tasks finished or cancelled", not open_, "%d open: %s" % (len(open_), "; ".join(t["title"] for t in open_[:3]))),
        ("every finished task has finished_at", not nofin, "%d missing" % len(nofin)),
        ("## Retro has content", meaningful(R.section(ctx, "## Retro")), "empty or TBD"),
        ("## Lessons has at least one entry", bool(re.search(r"^\s*[-*]\s+\S", R.section(ctx, "## Lessons"), re.M)), "none"),
        ("project links to a lessons knowledge entry (refer_knowledge)", len(links) > 0, "no knowledge linked"),
        ("## Estimation Record row written", bool(est_rows), "no table row (run `close.py stats`, append the row under `## Estimation Record`)"),
    ]
    ok = all(c[1] for c in crit)
    for name, passed, why in crit:
        print(("PASS " if passed else "FAIL ") + name + ("" if passed else " -- " + why))
    print("READY to set `finalized` (needs user confirmation)" if ok else "NOT READY")
    sys.exit(0 if ok else 1)


def stats(pid, as_json):
    proj, tasks = load(pid)
    ctx = proj["fields"].get(R.PF["ctx"]) or ""
    shape = (re.search(r"^Shape:\s*(\S+)", ctx, re.M) or [None, "unknown"])[1]
    charter = R.section(ctx, "## Charter")
    est_line = (re.search(r"Estimate:(.*)", charter) or [None, ""])[1]
    best, likely, worst = (days(est_line, k) for k in ("best", "likely", "worst"))
    bm = re.search(r"buffer\s*[:=]?\s*(\d+)\s*%", est_line + charter, re.I)
    buffer = int(bm.group(1)) / 100 if bm else None
    live = [t for t in tasks if t["prog"] != "cancelled"]
    starts = [t["start"] for t in live if t["start"]]
    fins = [t["finish"] for t in live if t["finish"]]
    actual = (max(fins) - min(starts)).days if starts and fins else None
    judged = [t for t in live if t["due"] and t["finish"]]
    late = sorted([(t["finish"] - t["due"]).days, t["title"]] for t in judged if t["finish"] > t["due"])[::-1]
    on_time = round(100 * (len(judged) - len(late)) / len(judged)) if judged else None
    ratio = round(actual / likely, 2) if actual is not None and likely else None
    within = (actual <= likely * (1 + buffer)) if actual is not None and likely and buffer is not None else None
    res = dict(project=proj["fields"].get(R.PF["title"]), shape=shape, start=min(starts).isoformat() if starts else None,
               end=max(fins).isoformat() if fins else None, actual_days=actual, estimate=dict(best=best, likely=likely, worst=worst),
               buffer=buffer, actual_vs_likely=ratio, within_declared_buffer=within, tasks=len(live), judged=len(judged),
               on_time_pct=on_time, slipped=[dict(days_late=d, title=t) for d, t in late[:5]],
               row="| %s | %s | %s | %s | %s | %s | %s |" % (
                   proj["fields"].get(R.PF["title"]), shape, "%gd" % likely if likely else "n/a", "%dd" % actual if actual is not None else "n/a",
                   ratio if ratio is not None else "n/a", "%d%%" % on_time if on_time is not None else "n/a", max(fins).isoformat() if fins else "n/a"),
               basis="%d active non-cancelled task row(s)" % len(live))
    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    print("%s · shape %s · %s -> %s" % (res["project"], shape, res["start"], res["end"]))
    print("Actual %s d vs estimate best/likely/worst %s/%s/%s (declared buffer %s)" % (actual, best, likely, worst, "%d%%" % round(buffer * 100) if buffer is not None else "n/a"))
    print("Actual/likely %s · within declared buffer: %s · on time %s%% of %d dated finished task(s)" % (ratio, within, on_time, len(judged)))
    for s in res["slipped"]:
        print("  late %dd: %s" % (s["days_late"], s["title"]))
    print("Estimation norms row (header: | Project | Shape | Likely | Actual | Actual/Likely | On-time | Finished |):")
    print(res["row"])
    print("basis: " + res["basis"])


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("cmd", choices=["check", "stats"])
    a.add_argument("project")
    a.add_argument("--json", action="store_true")
    args = a.parse_args()
    check(args.project) if args.cmd == "check" else stats(args.project, args.json)


if __name__ == "__main__":
    main()
