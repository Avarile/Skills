#!/usr/bin/env python3
"""Deterministic project / goal / portfolio health (read-only). Implements references/reports.md.

  rollup.py project <projectRecId> [--today YYYY-MM-DD] [--json]
  rollup.py goal <goalRecId>       [--today ...] [--json]
  rollup.py portfolio              [--today ...] [--json]

Definitions (see reports.md): open = active and progress not finished_*/cancelled; Due = 'Due:' line in task context;
overdue = open and Due < today; SPI = finished / tasks with Due <= today (standard EV/PV, may exceed 1);
RAG rules and thresholds are the constants below. Every figure states its row basis.
"""
import argparse, datetime as dt, json, re, sys
import teable as T

PROJECTS, GOALS, TASKS = "tbliD8gcOTRk9RZ9SmR", "tblbGSzWdR7KEtPVClg", "tblOMgDiajqa1moRRjE"
# thresholds (keep in sync with references/reports.md)
STALE_DAYS, STATUS_GAP_DAYS, GATE_OVERDUE_RED, OVERDUE_RATIO_RED, ONHOLD_RED_DAYS = 14, 10, 3, 0.25, 14
SPI_AMBER, SPI_RED, INBOX_DAYS = 0.85, 0.70, 7
DONE_T = {"finished_reviewing", "finished_validating"}
DONE_P = {"finished-reviewing", "finished-validating", "finished-testing", "finalized"}
TF = dict(title="fldGqUoXO7oyq6ufX2Y", ctx="fldaOhjcXqdiF3IRVB1", prog="fldG7fZN9XhOa0lMy33", prio="fldMTuydiWUFAgtqAPX",
          proj="fld6X3nrMTQlYiV5XSa", who="fld3ZGyfGzogzwHt5Md", active="fldJMclfBagyBukSxoy", created="fldYNEyagDaFRoxV8zF")
PF = dict(title="fldiDksJhyT8mDAhCBP", ctx="fldnzxFdoNG8bN1y4kC", prog="fldYje9YsvEa6e7QotE", goal="flduhpVlKOqQrmbIQv2",
          lead="fldJKSNWzxTU1K5o83t", active="fldF4pjQ5r6H0qSsbdy", updated="fldj85aGVZVUyo2xerD", tasks="fldmosZm5TTPkuyo5hr")
GF = dict(title="fld8ipvRLGq7YTgPQkI", ctx="fldEoRNZHELqaaQbNTE", deadline="fldlHvInBnEeptWDAvI", active="fldRA4LarPTZ8fwagzt")
EMOJI = {"GREEN": "🟢", "AMBER": "🟡", "RED": "🔴"}


def parse_task(r, today):
    f = r["fields"]
    ctx = f.get(TF["ctx"]) or ""
    due = re.search(r"^Due:\s*(\d{4}-\d{2}-\d{2})", ctx, re.M)
    step = re.search(r"Step\s+(\d+)", f.get(TF["title"]) or "")
    prog = f.get(TF["prog"]) or "backlog"
    return dict(id=r["id"], title=f.get(TF["title"]) or "", prog=prog, prio=f.get(TF["prio"]) or "normal",
                due=dt.date.fromisoformat(due.group(1)) if due else None, gate=bool(re.search(r"^Gate:", ctx, re.M)),
                step=int(step.group(1)) if step else None, active=bool(f.get(TF["active"])),
                who_id=(f.get(TF["who"]) or {}).get("id"), who_name=(f.get(TF["who"]) or {}).get("title"),
                phase=(re.search(r"\[(PLAN|DO|CHECK|ACT)\]", f.get(TF["title"]) or "") or [None, None])[1],
                who=bool(f.get(TF["who"])), created=T.local_date(f.get(TF["created"])))


def section(ctx, heading):
    m = re.search(r"^%s\s*$(.*?)(?=^## |\Z)" % re.escape(heading), ctx or "", re.M | re.S)
    return m.group(1) if m else ""


def table_rows(text):
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in text.splitlines() if l.strip().startswith("|")]
    return [r for r in rows if r and not set("".join(r)) <= set("-: ")]


def project_rollup(proj, tasks, today, goal_deadline=None):
    pf = proj["fields"]
    ctx, prog = pf.get(PF["ctx"]) or "", pf.get(PF["prog"]) or "backlog"
    ts = [parse_task(t, today) for t in tasks]
    ts = [t for t in ts if t["active"]]
    live = [t for t in ts if t["prog"] != "cancelled"]
    done = [t for t in live if t["prog"] in DONE_T]
    opn = [t for t in live if t["prog"] not in DONE_T]
    overdue = [t for t in opn if t["due"] and t["due"] < today]
    undated = [t for t in opn if not t["due"]]
    planned = [t for t in live if t["due"] and t["due"] <= today]
    spi = round(len(done) / len(planned), 2) if planned else None
    counts = {}
    for t in ts:
        counts[t["prog"]] = counts.get(t["prog"], 0) + 1
    gates = sorted([t for t in opn if t["gate"] and t["due"]], key=lambda t: t["due"])
    gate_late = [t for t in gates if (today - t["due"]).days > GATE_OVERDUE_RED]
    early = [t["title"] for t in ts if t["phase"] == "DO" and t["prog"] in DONE_T | {"in-progress"} and t["step"]
             and any(g["step"] and g["step"] < t["step"] for g in gates)]
    log_dates = [dt.date.fromisoformat(d) for d in re.findall(r"^###\s+(\d{4}-\d{2}-\d{2})", section(ctx, "## Status Log"), re.M)]
    gap = (today - max(log_dates)).days if log_dates else None
    updated = T.local_date(pf.get(PF["updated"]))
    stale_days = (today - updated).days if updated else None
    risks = [r for r in table_rows(section(ctx, "## Risk Register"))[1:] if len(r) >= 6]
    risk_open = [r for r in risks if r[5].lower() not in ("closed", "mitigated", "resolved")]
    risk_unmitigated = [r[0] for r in risk_open if r[2].lower() == "high" and not r[4]]
    red, amber = [], []
    if gate_late:
        red.append("gate task overdue >%dd: %s" % (GATE_OVERDUE_RED, gate_late[0]["title"]))
    if live and len(overdue) / len(live) > OVERDUE_RATIO_RED:
        red.append("%d of %d tasks overdue (>%d%%)" % (len(overdue), len(live), OVERDUE_RATIO_RED * 100))
    if prog == "onhold" and stale_days is not None and stale_days > ONHOLD_RED_DAYS:
        red.append("on hold for >%dd" % ONHOLD_RED_DAYS)
    if goal_deadline and goal_deadline < today and prog not in DONE_P:
        red.append("goal deadline %s passed, project unfinished" % goal_deadline)
    if overdue and not red:
        amber.append("%d task(s) overdue" % len(overdue))
    elif overdue:
        amber.append("%d task(s) overdue" % len(overdue))
    if spi is not None and spi < SPI_RED:
        red.append("SPI %.2f < %.2f" % (spi, SPI_RED))
    elif spi is not None and spi < SPI_AMBER:
        amber.append("SPI %.2f < %.2f" % (spi, SPI_AMBER))
    if risk_unmitigated:
        amber.append("high-impact risk without mitigation: %s" % risk_unmitigated[0])
    if prog == "in-progress" and (gap is None or gap > STATUS_GAP_DAYS):
        amber.append("no status entry for %s" % ("any period" if gap is None else "%dd" % gap))
    if early:
        amber.append("DO work started before gate: %s" % early[0])
    rag = "RED" if red else "AMBER" if amber else "GREEN"
    by_who = {}
    for t in opn:
        by_who[t["who_name"] or "unassigned"] = by_who.get(t["who_name"] or "unassigned", 0) + 1
    return dict(by_assignee=by_who, unassigned_in_progress=len([t for t in opn if t["prog"] == "in-progress" and not t["who_id"]]),
                lead=T.contact_name(pf[PF["lead"]]["id"]) if pf.get(PF["lead"]) else None, id=proj["id"], title=pf.get(PF["title"]), progress=prog, rag=rag, rules=red + amber,
                tasks_active=len(ts), counts=counts, completion=round(len(done) / len(live), 2) if live else None,
                overdue=[dict(title=t["title"], due=t["due"].isoformat(), prio=t["prio"]) for t in sorted(overdue, key=lambda t: t["due"])],
                undated=len(undated), spi=spi, next_gate=dict(title=gates[0]["title"], due=gates[0]["due"].isoformat()) if gates else None,
                open_risks=len(risk_open), last_status=max(log_dates).isoformat() if log_dates else None,
                stale=bool(prog == "in-progress" and stale_days is not None and stale_days > STALE_DAYS),
                basis="%d active task row(s), today=%s" % (len(ts), today))


def render(r):
    c = r["counts"]
    out = ["%s · %s · RAG %s %s" % (r["title"], r["progress"], EMOJI[r["rag"]], r["rag"]) + (" (%s)" % "; ".join(r["rules"]) if r["rules"] else ""),
           "Tasks %d: " % r["tasks_active"] + " / ".join("%s %d" % (k, v) for k, v in sorted(c.items())),
           "Completion %s · SPI %s · Overdue %d · Undated %d" % (
               "n/a" if r["completion"] is None else "%d%%" % round(r["completion"] * 100), "n/a" if r["spi"] is None else r["spi"], len(r["overdue"]), r["undated"]),
           "Next gate: %s · Open risks: %d · Last status: %s" % (
               "%s due %s" % (r["next_gate"]["title"], r["next_gate"]["due"]) if r["next_gate"] else "none", r["open_risks"], r["last_status"] or "none")]
    if r["by_assignee"]:
        out.append("Lead: %s · Open by assignee: %s" % (r["lead"] or "none", ", ".join("%s %d" % (k, v) for k, v in sorted(r["by_assignee"].items()))))
    out += ["  overdue: %s (due %s, %s)" % (o["title"], o["due"], o["prio"]) for o in r["overdue"][:8]]
    out.append("basis: " + r["basis"])
    return "\n".join(out)


def goal_rollup(g, project_rollups, today):
    gf = g["fields"]
    rows = table_rows(section(gf.get(GF["ctx"]) or "", "## Key Results"))
    scores, krs = [], []
    if rows:
        head = [h.lower() for h in rows[0]]
        si = head.index("score") if "score" in head else None
        for r in rows[1:]:
            if si is not None and si < len(r):
                try:
                    scores.append(float(r[si]))
                    krs.append((r[0], float(r[si])))
                except ValueError:
                    pass
    dl = T.local_date(gf.get(GF["deadline"]))
    return dict(id=g["id"], title=gf.get(GF["title"]), deadline=dl.isoformat() if dl else None,
                runway_days=(dl - today).days if dl else None, kr_scores=krs,
                kr_avg=round(sum(scores) / len(scores), 2) if scores else None,
                projects=[dict(title=p["title"], rag=p["rag"], progress=p["progress"]) for p in project_rollups])


def load_all():
    projects = [r for r in T.get_records(PROJECTS) if r["fields"].get(PF["active"])]
    tasks = [r for r in T.get_records(TASKS)]
    goals = [r for r in T.get_records(GOALS) if r["fields"].get(GF["active"])]
    by = {}
    for t in tasks:
        link = t["fields"].get(TF["proj"])
        by.setdefault(link["id"] if link else None, []).append(t)
    return goals, projects, by, tasks


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("what", choices=["project", "goal", "portfolio"])
    a.add_argument("id", nargs="?")
    a.add_argument("--today")
    a.add_argument("--json", action="store_true")
    args = a.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else T.today()

    if args.what == "project":
        if not args.id:
            sys.exit("project needs a record id")
        proj = T.get_record(PROJECTS, args.id)
        tasks = T.get_records(TASKS, T.and_filter(["%s is %s" % (TF["proj"], args.id)]))
        gl = (proj["fields"].get(PF["goal"]) or {}).get("id")
        dl = T.local_date(T.get_record(GOALS, gl, [GF["deadline"]])["fields"].get(GF["deadline"])) if gl else None
        r = project_rollup(proj, tasks, today, dl)
        print(json.dumps(r, ensure_ascii=False, indent=1) if args.json else render(r))
        return

    goals, projects, by, all_tasks = load_all()
    gdl = {g["id"]: T.local_date(g["fields"].get(GF["deadline"])) for g in goals}
    rolls = {}
    for p in projects:
        gl = (p["fields"].get(PF["goal"]) or {}).get("id")
        rolls[p["id"]] = project_rollup(p, by.get(p["id"], []), today, gdl.get(gl))
    if args.what == "goal":
        g = next((x for x in goals if x["id"] == args.id), None) or sys.exit("goal not found or inactive")
        ps = [rolls[p["id"]] for p in projects if (p["fields"].get(PF["goal"]) or {}).get("id") == g["id"]]
        r = goal_rollup(g, ps, today)
        print(json.dumps(r, ensure_ascii=False, indent=1) if args.json else "%s · deadline %s (%s days) · KR avg %s\n%s" % (
            r["title"], r["deadline"], r["runway_days"], r["kr_avg"], "\n".join("  %s %s %s" % (EMOJI[p["rag"]], p["title"], p["progress"]) for p in r["projects"])))
        return

    inbox = next((p for p in projects if (p["fields"].get(PF["title"]) or "").strip().lower() == "inbox"), None)
    old_inbox = [t for t in by.get(inbox["id"], []) if (lambda c: c and (today - c).days > INBOX_DAYS)(T.local_date(t["fields"].get(TF["created"])))] if inbox else []
    out = dict(today=today.isoformat(),
               goals=[goal_rollup(g, [rolls[p["id"]] for p in projects if (p["fields"].get(PF["goal"]) or {}).get("id") == g["id"]], today) for g in goals],
               no_goal=[rolls[p["id"]]["title"] for p in projects if not p["fields"].get(PF["goal"]) and p is not inbox],
               no_lead=[rolls[p["id"]]["title"] for p in projects if not p["fields"].get(PF["lead"]) and p is not inbox],
               no_tasks=[rolls[p["id"]]["title"] for p in projects if not by.get(p["id"]) and p is not inbox],
               stale=[r["title"] for r in rolls.values() if r["stale"]],
               orphan_tasks=len([t for t in by.get(None, []) if t["fields"].get(TF["active"])]),
               inbox_old=len(old_inbox),
               basis="%d goal(s), %d project(s), %d task row(s)" % (len(goals), len(projects), len(all_tasks)))
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    print("Portfolio %s · %s" % (out["today"], out["basis"]))
    for g in out["goals"]:
        print("GOAL %s · deadline %s (%s d) · KR avg %s" % (g["title"], g["deadline"], g["runway_days"], g["kr_avg"]))
        for p in g["projects"]:
            print("   %s %s [%s]" % (EMOJI[p["rag"]], p["title"], p["progress"]))
    for k in ("no_goal", "no_lead", "no_tasks", "stale"):
        if out[k]:
            print("%s: %s" % (k.replace("_", " "), "; ".join(out[k])))
    print("orphan active tasks (no project): %d · Inbox items older than %dd: %d" % (out["orphan_tasks"], INBOX_DAYS, out["inbox_old"]))


if __name__ == "__main__":
    main()
