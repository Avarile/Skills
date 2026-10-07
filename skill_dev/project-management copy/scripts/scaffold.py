#!/usr/bin/env python3
"""Expand a task template into dated tasks for a project; lint it; optionally create the tasks.
DRY-RUN BY DEFAULT: --create without --yes only previews. Preview is always printed first.

  scaffold.py --list
  scaffold.py client-delivery --start 2026-10-12 --days 90 --buffer 0.25
  scaffold.py build --start 2026-10-05 --days 28 --project-id recXXXX --create --yes
  scaffold.py build --start 2026-10-05 --assign PLAN=Avarile --assign "DO=Agentic Mind (Developer)" --assign CHECK=Avarile

Due dates: span = ceil(days * (1 + buffer)) calendar days from --start; each step is due at
start + round(at * span), moved forward to a weekday. The buffer is printed, never hidden.
Task title: 'Step NN [PHASE] <title>' (+ ' (M1)'); context: 'Due:' line, optional 'Gate:' / 'Acceptance:', notes.
Lint (exit 2 on failure): a gate step, >=1 CHECK, >=1 ACT, and a mid-point/health check when >=10 steps.
"""
import argparse, datetime as dt, json, math, sys
from pathlib import Path
import teable as T

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
TASKS = "tblOMgDiajqa1moRRjE"
F = dict(title="fldGqUoXO7oyq6ufX2Y", context="fldaOhjcXqdiF3IRVB1", priority="fldMTuydiWUFAgtqAPX",
         project="fld6X3nrMTQlYiV5XSa", assignee="fld3ZGyfGzogzwHt5Md")


def load(name):
    p = TEMPLATES / (name + ".json")
    if not p.is_file():
        sys.exit("unknown template %r; available: %s" % (name, ", ".join(sorted(x.stem for x in TEMPLATES.glob("*.json")))))
    return json.loads(p.read_text())


def weekday(d):
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d


def expand(tpl, start, days, buffer):
    span = math.ceil(days * (1 + buffer))
    out = []
    for i, s in enumerate(tpl["steps"], 1):
        due = weekday(start + dt.timedelta(days=round(s["at"] * span)))
        title = "Step %02d [%s] %s" % (i, s["p"], s["t"]) + (" (%s)" % s["m"] if s.get("m") else "")
        ctx = ["Due: " + due.isoformat()]
        if s.get("g"):
            ctx.append("Gate: " + s["g"])
        if s.get("acc"):
            ctx.append("Acceptance: " + s["acc"])
        body = "\n".join(ctx) + ("\n\n" + s["n"] if s.get("n") else "")
        out.append(dict(step=i, phase=s["p"], title=title, priority=s.get("pr", "normal"), due=due.isoformat(),
                        gate=bool(s.get("g")), context=body))
    return out, span


def lint(tasks):
    problems = []
    if not any(t["gate"] for t in tasks):
        problems.append("no gate step")
    for ph in ("CHECK", "ACT"):
        if not any(t["phase"] == ph for t in tasks):
            problems.append("no %s step" % ph)
    if len(tasks) >= 10 and not any(("check-point" in t["title"].lower() or "health check" in t["title"].lower()) for t in tasks):
        problems.append("no mid-point / health check for a project of >=10 steps")
    return problems


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("template", nargs="?")
    a.add_argument("--list", action="store_true")
    a.add_argument("--start", help="YYYY-MM-DD (default: today)")
    a.add_argument("--days", type=int, help="likely duration in calendar days (default: template minimum)")
    a.add_argument("--buffer", type=float, default=0.2, help="declared buffer fraction, default 0.2")
    a.add_argument("--project-id")
    a.add_argument("--assignee", help="default contact (name or record id) for tasks whose phase has no --assign")
    a.add_argument("--assign", action="append", default=[], metavar="PHASE=CONTACT",
                   help="assign every task of a phase to a contact (name or id), e.g. --assign PLAN=Avarile --assign 'DO=Agentic Mind (Developer)'; repeatable")
    a.add_argument("--create", action="store_true")
    a.add_argument("--force", action="store_true", help="allow scaffolding into a project that already has tasks")
    a.add_argument("--yes", action="store_true")
    a.add_argument("--json", action="store_true", help="print the task records as JSON instead of a table")
    args = a.parse_args()

    if args.list or not args.template:
        for p in sorted(TEMPLATES.glob("*.json")):
            t = json.loads(p.read_text())
            print("%-16s %2d steps  min %3dd  %s" % (t["name"], len(t["steps"]), t["min_days"], t["desc"]))
        return

    tpl = load(args.template)
    start = dt.date.fromisoformat(args.start) if args.start else dt.date.today()
    days = args.days or tpl["min_days"]
    tasks, span = expand(tpl, start, days, args.buffer)
    problems = lint(tasks)
    default_c = T.resolve_contact(args.assignee) if args.assignee else (None, None)
    by_phase = {}
    for spec in args.assign:
        ph, _, ref = spec.partition("=")
        ph = ph.strip().upper()
        if ph not in ("PLAN", "DO", "CHECK", "ACT") or not ref:
            sys.exit("bad --assign %r (use PHASE=CONTACT with PHASE one of PLAN, DO, CHECK, ACT)" % spec)
        by_phase[ph] = T.resolve_contact(ref)
    for t in tasks:
        t["assignee_id"], t["assignee"] = by_phase.get(t["phase"], default_c)

    print("%s: %d steps · start %s · likely %dd + %d%% declared buffer = %dd span · ends %s" % (
        tpl["name"], len(tasks), start, days, round(args.buffer * 100), span, tasks[-1]["due"]))
    if args.json:
        print(json.dumps(tasks, ensure_ascii=False, indent=1))
    else:
        for t in tasks:
            who = ("  -> " + t["assignee"]) if t.get("assignee") else ""
            print(" %-4s %-10s %s%s%s" % (t["due"][5:], t["priority"], t["title"], "  [GATE]" if t["gate"] else "", who))
    print("lint:", "ok" if not problems else "FAILED: " + "; ".join(problems))
    if problems:
        sys.exit(2)
    if not args.create:
        return

    if not args.project_id:
        sys.exit("--create needs --project-id")
    proj = T.get_record("tbliD8gcOTRk9RZ9SmR", args.project_id, ["fldiDksJhyT8mDAhCBP", "fldmosZm5TTPkuyo5hr"])["fields"]
    existing = len(proj.get("fldmosZm5TTPkuyo5hr") or [])
    print("target project: %s (%d existing task(s))" % (proj.get("fldiDksJhyT8mDAhCBP"), existing))
    if existing and not args.force:
        sys.exit("refusing: project already has tasks (use --force to add anyway)")
    import write as W
    W.validate_sets(TASKS, {F["priority"]: "normal"})  # field exists; options checked per value below
    meta = {f["id"]: f for f in T.call("GET", "/api/table/%s/field" % TASKS)}
    valid = {c["name"] for c in meta[F["priority"]]["options"]["choices"]}
    bad = {t["priority"] for t in tasks} - valid
    if bad:
        sys.exit("template uses invalid priority %s; valid: %s" % (sorted(bad), sorted(valid)))
    records = []
    for t in tasks:
        f = {F["title"]: t["title"], F["context"]: t["context"], F["priority"]: t["priority"],
             F["project"]: {"id": args.project_id}}
        if t.get("assignee_id"):
            f[F["assignee"]] = {"id": t["assignee_id"]}
        records.append({"fields": f})
    if not args.yes:
        print("DRY RUN: would create %d task(s). Re-run with --yes to apply." % len(records))
        return
    res = T.call("POST", "/api/table/%s/record" % TASKS, body={"fieldKeyType": "id", "records": records})
    ids = [r["id"] for r in res["records"]]
    got = T.get_records(TASKS, T.and_filter(["%s is %s" % (F["project"], args.project_id)]), [F["title"]])
    ok = len(got) == existing + len(records)
    print("created %d task(s); project now has %d; verification %s" % (len(ids), len(got), "ok" if ok else "FAILED"))
    print("ids:", " ".join(ids))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
