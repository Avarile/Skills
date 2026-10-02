#!/usr/bin/env python3
"""Assignment and workload for projects and tasks (links to the `contacts` table).

  assign.py set  --to CONTACT (--project P | --ids rec...) [--phase PLAN,DO] [--unassigned-only] [--reassign] [--yes]
  assign.py lead PROJECT --to CONTACT [--reassign] [--yes]
  assign.py workload [--project P] [--today YYYY-MM-DD] [--json]
  assign.py tasks --contact CONTACT [--project P] [--today ...] [--json]

CONTACT is a name or record id; `none` clears the assignment. P is a project record id or title.
Safety: DRY-RUN BY DEFAULT (--yes applies); only active, open tasks are touched; a task already assigned to
someone ELSE is skipped and reported unless --reassign is given (assignment never silently takes work away);
an unknown or ambiguous contact exits without writing; writes go through write.py bulk-update (validated, read back).
"""
import argparse, datetime as dt, json, re, sys
import teable as T
import rollup as R
import write as W

WIP_LIMIT = 3  # in-progress tasks per person before the workload report flags them (keep in sync with reports.md)
PRIO = {"urgent": 0, "important": 1, "prioritise": 2, "normal": 3, "can wait": 4}


def resolve_project(ref):
    if re.fullmatch(r"rec[A-Za-z0-9]{16}", ref):
        r = T.get_record(R.PROJECTS, ref, [R.PF["title"], R.PF["lead"]])
        return r
    recs = [r for r in T.get_records(R.PROJECTS, projection=[R.PF["title"], R.PF["lead"], R.PF["active"]]) if r["fields"].get(R.PF["active"])]
    exact = [r for r in recs if (r["fields"].get(R.PF["title"]) or "").strip().lower() == ref.lower()]
    hit = exact if len(exact) == 1 else [r for r in recs if ref.lower() in (r["fields"].get(R.PF["title"]) or "").lower()]
    if not hit:
        sys.exit("no active project matches %r" % ref)
    if len(hit) > 1:
        sys.exit("ambiguous project %r: %s" % (ref, "; ".join("%s (%s)" % (r["fields"].get(R.PF["title"]), r["id"]) for r in hit)))
    return hit[0]


def bulk(table, ids, field, value, yes):
    ns = argparse.Namespace(table=table, ids=ids, filter=[], set=["%s=%s" % (field, json.dumps(value))], max=200, yes=yes)
    W.cmd_bulk_update(ns)


def cmd_set(a):
    cid, cname = T.resolve_contact(a.to)
    if a.ids:
        rows = [T.get_record(R.TASKS, i) for i in a.ids]
    else:
        if not a.project:
            sys.exit("give --project or --ids")
        pid = resolve_project(a.project)["id"]
        rows = T.get_records(R.TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid)]))
    phases = [x.strip().upper() for x in a.phase.split(",")] if a.phase else None
    today = T.today()
    change, skipped_other, same, closed = [], [], [], 0
    for r in rows:
        t = R.parse_task(r, today)
        if not t["active"] or t["prog"] in R.DONE_T or t["prog"] == "cancelled":
            closed += 1
            continue
        if phases and t["phase"] not in phases:
            continue
        if a.unassigned_only and t["who_id"]:
            continue
        if t["who_id"] == cid:
            same.append(t)
        elif t["who_id"] and not a.reassign:
            skipped_other.append(t)
        else:
            change.append(t)
    print("assign to %s: %d to change · %d already theirs · %d held by someone else (skipped) · %d finished/cancelled/inactive ignored" % (
        cname or "nobody (unassign)", len(change), len(same), len(skipped_other), closed))
    for t in change[:25]:
        print("  %s: %s -> %s" % (t["title"][:60], t["who_name"] or "(unassigned)", cname or "(unassigned)"))
    if len(change) > 25:
        print("  ... and %d more" % (len(change) - 25))
    for t in skipped_other[:10]:
        print("  SKIPPED %s (held by %s; use --reassign to take it over)" % (t["title"][:50], t["who_name"]))
    if not change:
        print("nothing to change")
        return
    if not a.yes:
        print("DRY RUN: nothing written. Re-run with --yes to apply.")
        return
    bulk(R.TASKS, [t["id"] for t in change], R.TF["who"], {"id": cid} if cid else None, True)


def cmd_lead(a):
    cid, cname = T.resolve_contact(a.to)
    p = resolve_project(a.project)
    cur = p["fields"].get(R.PF["lead"]) or {}
    cur_name = T.contact_name(cur["id"]) if cur else None
    title = p["fields"].get(R.PF["title"])
    print("project %s: lead %s -> %s" % (title, cur_name or "(none)", cname or "(none)"))
    if cur.get("id") == cid:
        print("nothing to change")
        return
    if cur and not a.reassign:
        sys.exit("refusing: project already has lead %s (use --reassign to replace)" % cur_name)
    if not a.yes:
        print("DRY RUN: nothing written. Re-run with --yes to apply.")
        return
    bulk(R.PROJECTS, [p["id"]], R.PF["lead"], {"id": cid} if cid else None, True)


def load(project_ref):
    pid = resolve_project(project_ref)["id"] if project_ref else None
    flt = T.and_filter(["%s is %s" % (R.TF["proj"], pid)]) if pid else None
    return [R.parse_task(r, T.today()) for r in T.get_records(R.TASKS, flt)]


def cmd_workload(a):
    today = dt.date.fromisoformat(a.today) if a.today else T.today()
    tasks = [t for t in load(a.project) if t["active"] and t["prog"] not in R.DONE_T and t["prog"] != "cancelled"]
    people = {}
    for t in tasks:
        k = t["who_name"] or "(unassigned)"
        d = people.setdefault(k, dict(open=0, in_progress=0, overdue=0, due7=0, hot=0, onhold=0))
        d["open"] += 1
        d["in_progress"] += t["prog"] == "in-progress"
        d["onhold"] += t["prog"] == "onhold"
        d["hot"] += t["prio"] in ("urgent", "important")
        if t["due"]:
            d["overdue"] += t["due"] < today
            d["due7"] += today <= t["due"] <= today + dt.timedelta(days=7)
    leads = {}
    for r in T.get_records(R.PROJECTS, projection=[R.PF["title"], R.PF["lead"], R.PF["prog"], R.PF["active"]]):
        f = r["fields"]
        if f.get(R.PF["active"]) and f.get(R.PF["prog"]) not in R.DONE_P | {"cancelled"} and f.get(R.PF["lead"]):
            leads.setdefault(T.contact_name(f[R.PF["lead"]]["id"]) or f[R.PF["lead"]]["id"], []).append(f.get(R.PF["title"]))
    flags = {k: [x for x in (["%d in progress (WIP limit %d)" % (v["in_progress"], WIP_LIMIT)] if v["in_progress"] > WIP_LIMIT else []) +
                 (["%d overdue" % v["overdue"]] if v["overdue"] else [])] for k, v in people.items() if k != "(unassigned)"}
    out = dict(today=today.isoformat(), people=people, leads=leads, flags={k: v for k, v in flags.items() if v},
               basis="%d open task row(s)%s" % (len(tasks), " in the given project" if a.project else ""))
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    print("Workload %s · %s" % (out["today"], out["basis"]))
    print("%-34s %5s %6s %7s %5s %9s %7s" % ("person", "open", "in-prg", "overdue", "due7", "urg+imp", "onhold"))
    for k, v in sorted(people.items(), key=lambda kv: (kv[0] == "(unassigned)", -kv[1]["open"])):
        print("%-34s %5d %6d %7d %5d %9d %7d" % (k[:34], v["open"], v["in_progress"], v["overdue"], v["due7"], v["hot"], v["onhold"]))
    for k, v in sorted(leads.items()):
        print("leads: %s -> %s" % (k, "; ".join(v)))
    for k, v in out["flags"].items():
        print("FLAG %s: %s" % (k, ", ".join(v)))


def cmd_tasks(a):
    today = dt.date.fromisoformat(a.today) if a.today else T.today()
    cid, cname = T.resolve_contact(a.contact)
    mine = [t for t in load(a.project) if t["active"] and t["prog"] not in R.DONE_T and t["prog"] != "cancelled" and t["who_id"] == cid]
    far = dt.date.max
    key = lambda t: (PRIO.get(t["prio"], 3), t["due"] or far, t["step"] or 0)
    sec = [("Overdue", [t for t in mine if t["due"] and t["due"] < today]),
           ("Due in 7 days", [t for t in mine if t["due"] and today <= t["due"] <= today + dt.timedelta(days=7)]),
           ("In progress", [t for t in mine if t["prog"] == "in-progress"]),
           ("Blocked / on hold", [t for t in mine if t["prog"] == "onhold"]),
           ("Undated", [t for t in mine if not t["due"]])]
    if a.json:
        print(json.dumps(dict(contact=cname, open=len(mine), sections={n: [dict(id=t["id"], title=t["title"], prio=t["prio"], due=t["due"].isoformat() if t["due"] else None) for t in sorted(ts, key=key)] for n, ts in sec}), ensure_ascii=False, indent=1))
        return
    print("%s · %d open task(s) · %s" % (cname, len(mine), today))
    for n, ts in sec:
        if ts:
            print(n + ":")
            for t in sorted(ts, key=key):
                print("  [%s] %s%s (%s)" % (t["prio"], t["title"], " due " + t["due"].isoformat() if t["due"] else "", t["id"]))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set")
    s.add_argument("--to", required=True)
    s.add_argument("--project")
    s.add_argument("--ids", nargs="*")
    s.add_argument("--phase", help="comma-separated PLAN,DO,CHECK,ACT")
    s.add_argument("--unassigned-only", action="store_true")
    s.add_argument("--reassign", action="store_true")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_set)
    l = sub.add_parser("lead")
    l.add_argument("project")
    l.add_argument("--to", required=True)
    l.add_argument("--reassign", action="store_true")
    l.add_argument("--yes", action="store_true")
    l.set_defaults(fn=cmd_lead)
    w = sub.add_parser("workload")
    w.add_argument("--project")
    w.add_argument("--today")
    w.add_argument("--json", action="store_true")
    w.set_defaults(fn=cmd_workload)
    t = sub.add_parser("tasks")
    t.add_argument("--contact", required=True)
    t.add_argument("--project")
    t.add_argument("--today")
    t.add_argument("--json", action="store_true")
    t.set_defaults(fn=cmd_tasks)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
