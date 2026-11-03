#!/usr/bin/env python3
"""Live acceptance test of day.py, taskctx.py and write.py gen-append. Creates only [TEST] rows and plans on dates in 2099,
deletes exactly what it created, then verifies the row counts are back to baseline. Exit 0 = all passed.

  python3 evals/run_day_flow.py        (needs CYBERNETICS_DATA_API_TOKEN in env or .env)
"""
import datetime as dt, json, re, subprocess, sys, tempfile
from pathlib import Path
SC = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SC))
import teable as T, rollup as R, day as D  # noqa: E402

B, P, Q = T.BLOCK, T.PLAN, T.ROUTINE
TABLES = (T.PLANS, T.BLOCKS, T.ROUTINES, R.TASKS, R.PROJECTS, R.GOALS)
results, made = [], {t: [] for t in TABLES}
DAY1, DAY2, MOVED, WINTER = "2099-01-05", "2099-01-06", "2099-01-09", "2099-07-06"   # Mon, Tue, Fri, Mon
AT = DAY1 + "T08:00"
tmp = tempfile.mkdtemp()


def check(name, ok, detail=""):
    ok = bool(ok)
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + ((" -- " + str(detail)[:400]) if detail and not ok else ""))


def sh(script, *args):
    p = subprocess.run([sys.executable, str(SC / script), *map(str, args)], capture_output=True, text=True, cwd=SC, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def day(*args, at=AT):
    return sh("day.py", *args, "--at", at)


def spec(obj):
    path = Path(tmp) / ("plan%d.json" % len(list(Path(tmp).iterdir())))
    path.write_text(json.dumps(obj))
    return str(path)


def counts():
    return {t: len(T.get_records(t, projection=[], take=100000)) for t in TABLES}


def blocks_on(date):
    plan = [r for r in T.get_records(T.PLANS, take=100000) if str(T.local_date(r["fields"].get(P["date"]))) == date]
    if not plan:
        return None, []
    rows = T.get_records(T.BLOCKS, T.and_filter(["%s is %s" % (B["day"], plan[0]["id"])]), take=1000)
    for t, ids in ((T.PLANS, [plan[0]["id"]]), (T.BLOCKS, [r["id"] for r in rows])):
        for i in ids:
            if i not in made[t]:
                made[t].append(i)
    return plan[0], rows


def by_title(rows, title):
    return next((r for r in rows if r["fields"].get(B["title"]) == title), None)


def main():
    base = counts()
    if any(str(T.local_date(r["fields"].get(P["date"]))).startswith("2099") for r in T.get_records(T.PLANS, take=100000)):
        sys.exit("plans on 2099 dates already exist; a previous run did not clean up. Remove them first.")
    try:
        # --- fixtures ---------------------------------------------------------------------------------------------
        g = T.create(R.GOALS, [{R.GF["title"]: "[TEST] day goal", R.GF["ctx"]: "## Key Results\n| KR | Metric |\n|---|---|\n| KR1 | a |\n"}])[0]["id"]
        made[R.GOALS].append(g)
        pr = T.create(R.PROJECTS, [{R.PF["title"]: "[TEST] day project", R.PF["prog"]: "in-progress", R.PF["goal"]: {"id": g}, R.PF["ctx"]: "Repo: /tmp/day-flow\n\n## Charter\n- Scope: test\n\n## Blockers\n"}])[0]["id"]
        made[R.PROJECTS].append(pr)
        pr2 = T.create(R.PROJECTS, [{R.PF["title"]: "[TEST] sponsored project", R.PF["prog"]: "in-progress", R.PF["ctx"]: "## Charter\n- Sponsor / sign-off: Dana Example\n"}])[0]["id"]
        made[R.PROJECTS].append(pr2)
        mk = lambda title, project=pr, ctx="Do it.\n\n## Log\n", **k: dict({R.TF["title"]: title, R.TF["proj"]: {"id": project}, R.TF["ctx"]: ctx}, **k)
        rows = T.create(R.TASKS, [mk("[TEST] task %d" % i) for i in range(1, 5)] + [mk("[TEST] sponsored", pr2, "Details to be completed by the owner.\n\n## Log\n")])
        made[R.TASKS] += [r["id"] for r in rows]
        t1, t2, t3, t4, t5 = [r["id"] for r in rows]

        # --- apply: preview, write, idempotence -----------------------------------------------------------------------
        plan = dict(days=[dict(date=DAY1, capacity=600, focus="[TEST] focus", focus_goal=g, context="Why this plan", deferred=["[TEST] later"], blocks=[
            dict(task=t1, minutes=90), dict(title="[TEST] admin", kind="admin", minutes=30),
            dict(title="[TEST] sync", kind="meeting", minutes=30, start="14:00", key="m1", notes="With: Aaron Sansoni"),
            dict(title="[TEST] prep", kind="prepare", minutes=15, before="m1"), dict(task=t2, minutes=60, after="m1")])])
        f = spec(plan)
        rc, out = day("apply", "--input", f)
        check("apply dry-run writes nothing", rc == 0 and "DRY RUN" in out and blocks_on(DAY1)[0] is None, out)
        check("preview shows routines and new blocks", "Morning standup" in out and "[routine]" in out and "[TEST] sync" in out, out)
        rc, out = day("apply", "--input", f, "--yes")
        check("apply writes and verifies", rc == 0 and "verification ok" in out, out)
        pl, bs = blocks_on(DAY1)
        check("one plan row with status, focus, goal, capacity", pl["fields"].get(P["status"]) == "planned" and pl["fields"].get(P["focus"]) == "[TEST] focus" and pl["fields"].get(P["goal"], {}).get("id") == g and pl["fields"].get(P["capacity"]) == 600, pl["fields"])
        check("plan context holds the why and the deferred work", "## Plan" in pl["fields"].get(P["ctx"], "") and "## Deferred" in pl["fields"].get(P["ctx"], ""), pl["fields"].get(P["ctx"]))
        rou = [r for r in T.get_records(T.ROUTINES, take=100) if r["fields"].get(Q["active"]) is True and r["fields"].get(Q["freq"]) == "weekdays"]
        stamped = [r for r in bs if r["fields"].get(B["source"]) == "routine"]
        check("every routine that falls is stamped and linked", len(stamped) == len(rou) and all(r["fields"].get(B["routine"]) for r in stamped), (len(stamped), len(rou)))
        check("task block keeps defaults and link", any((r["fields"].get(B["task"]) or {}).get("id") == t1 and r["fields"].get(B["kind"]) == "deep-work" and r["fields"].get(B["status"]) == "planned" and r["fields"].get(B["source"]) == "plan" for r in bs))
        sync, prep = by_title(bs, "[TEST] sync"), by_title(bs, "[TEST] prep")
        check("meeting stored at 14:00 Melbourne with its attendee", T.local_dt(sync["fields"][B["start"]]).strftime("%H:%M") == "14:00" and "Aaron" in sync["fields"].get(B["notes"], ""), sync["fields"])
        check("prepare ends when the meeting starts", T.local_dt(prep["fields"][B["start"]]).strftime("%H:%M") == "13:45", prep["fields"])
        after = next(r for r in bs if (r["fields"].get(B["task"]) or {}).get("id") == t2)
        check("dependent work placed after the meeting", T.local_dt(after["fields"][B["start"]]) >= T.local_dt(sync["fields"][B["start"]]))
        spans = sorted(D.block_span(D.parse_block(r)) for r in bs)
        check("the plan has no overlaps", all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), spans)
        ordered = sorted(bs, key=lambda r: r["fields"][B["start"]])
        check("order follows the timeline", [r["fields"].get(B["order"]) for r in ordered] == list(range(len(ordered))), [r["fields"].get(B["order"]) for r in ordered])
        n = len(bs)
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=DAY1, blocks=[dict(title="[TEST] second pass", kind="admin", minutes=15)])])), "--yes")
        pl2, bs2 = blocks_on(DAY1)
        check("re-planning reuses the day and never re-stamps routines", rc == 0 and pl2["id"] == pl["id"] and len(bs2) == n + 1, (rc, out, len(bs2)))
        # refusals
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=DAY1, blocks=[dict(title="[TEST] clash", kind="admin", minutes=30, start="14:10")])])), "--yes")
        check("an overlapping fixed block is refused", rc == 2 and "overlaps" in out and "nothing written" in out, out)
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=DAY2, capacity=120, blocks=[dict(title="[TEST] huge", kind="admin", minutes=400)])])), "--yes")
        check("over capacity is refused with a choice", rc == 2 and "over capacity" in out and blocks_on(DAY2)[0] is None, out)
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=DAY2, blocks=[dict(title="[TEST] bad", kind="deepwork", minutes=30)])])), "--yes")
        check("a misspelt kind is refused before writing", rc != 0 and "invalid kind" in out and blocks_on(DAY2)[0] is None, out)
        rc, out = day("apply", "--input", spec(dict(days=[dict(date="2099-01-04", blocks=[dict(title="[TEST] past", kind="admin", minutes=30)])])), "--yes")
        check("a past date is refused", rc == 2 and "past" in out, out)
        # daylight saving, via a stored row
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=WINTER, blocks=[dict(title="[TEST] winter", kind="admin", minutes=30, start="11:00")])])), "--yes", at=WINTER + "T08:00")
        _, wb = blocks_on(WINTER)
        check("outside daylight saving, times still read back local", T.local_dt(by_title(wb, "[TEST] winter")["fields"][B["start"]]).strftime("%H:%M") == "11:00" and by_title(wb, "[TEST] winter")["fields"][B["start"]].startswith("2099-07-06T01:00"), wb)

        # --- now and start ------------------------------------------------------------------------------------------
        rc, out = day("now", "--json", at=DAY1 + "T14:05")
        nw = json.loads(out)
        check("now finds the block covering this minute", nw["current"] and nw["current"]["title"] == "[TEST] sync", nw["current"])
        check("now reports earlier blocks with no outcome", any(b["title"] == "Morning standup" for b in nw["earlier_unfinished"]), nw["earlier_unfinished"])
        rc, out = day("now", "--json", at=DAY1 + "T13:30")
        check("now names the next block when between blocks", json.loads(out)["next"] is not None)
        task_block = next(r for r in bs if (r["fields"].get(B["task"]) or {}).get("id") == t1)["id"]
        rc, out = day("start", task_block, at=DAY1 + "T10:00")
        check("start dry-run writes nothing", rc == 0 and "DRY RUN" in out and not T.get_record(T.BLOCKS, task_block)["fields"].get(B["actual_start"]), out)
        rc, out = day("start", task_block, "--yes", at=DAY1 + "T10:00")
        fb, ft = T.get_record(T.BLOCKS, task_block)["fields"], T.get_record(R.TASKS, t1)["fields"]
        check("start records actual_start, keeps the block planned", rc == 0 and T.local_dt(fb[B["actual_start"]]).strftime("%H:%M") == "10:00" and fb[B["status"]] == "planned", (out, fb))
        check("start moves the task, sets started_at and logs", ft.get(R.TF["prog"]) == "in-progress" and ft.get(T.TASK_X["started"]) and "· in-progress · started" in ft.get(R.TF["ctx"], ""), ft)
        check("start claims an unassigned task for me", (ft.get(R.TF["who"]) or {}).get("title") == "Avarile", ft.get(R.TF["who"]))
        check("start marks the day running", T.get_record(T.PLANS, pl["id"])["fields"].get(P["status"]) == "running")
        rc, out = day("now", "--json", at=DAY1 + "T15:30")
        check("a started block stays current past its slot", json.loads(out)["current"]["id"] == task_block, out)
        # finish guards
        rc, out = day("finish", task_block, "--status", "done", at=DAY1 + "T11:30")
        check("finish refuses without confirmed minutes", rc != 0 and "--minutes" in out, out)
        rc, out = day("finish", task_block, "--status", "done", "--minutes", 80, "--task-progress", "finished_reviewing", at=DAY1 + "T11:30")
        check("a finished task needs evidence", rc != 0 and "--evidence" in out, out)
        rc, out = day("finish", task_block, "--status", "done", "--minutes", 80, "--task-progress", "finished_reviewing", "--evidence", "PR 1", "--yes", at=DAY1 + "T11:30")
        fb, ft = T.get_record(T.BLOCKS, task_block)["fields"], T.get_record(R.TASKS, t1)["fields"]
        check("finish records outcome and minutes", rc == 0 and fb[B["status"]] == "done" and fb[B["actual_minutes"]] == 80, (out, fb))
        check("finish moves the task with evidence and finished_at", ft.get(R.TF["prog"]) == "finished_reviewing" and ft.get(T.TASK_X["finished"]) and "PR 1" in ft.get(R.TF["ctx"], ""), ft)
        # adhoc
        rc, out = day("start", "--task", t3, "--yes", at=DAY1 + "T15:00")
        _, bs3 = blocks_on(DAY1)
        ad = next((r for r in bs3 if (r["fields"].get(B["task"]) or {}).get("id") == t3), None)
        check("unplanned work becomes an adhoc block with no planned_minutes", rc == 0 and ad and ad["fields"].get(B["source"]) == "adhoc" and not ad["fields"].get(B["minutes"]) and ad["fields"].get(B["actual_start"]), (out, ad and ad["fields"]))
        # a task held by someone else stays theirs
        hold = T.create(R.TASKS, [mk("[TEST] held", **{R.TF["who"]: {"id": T.resolve_contact("Anastasia Wang")[0]}})])[0]["id"]
        made[R.TASKS].append(hold)
        rc, out = day("start", "--task", hold, "--yes", at=DAY1 + "T15:10")
        fh = T.get_record(R.TASKS, hold)["fields"]
        check("start never takes over someone else's task", "held by" in out and fh.get(R.TF["prog"]) == "backlog" and fh[R.TF["who"]]["title"] == "Anastasia Wang", (out, fh.get(R.TF["prog"])))
        blocks_on(DAY1)

        # --- replan --------------------------------------------------------------------------------------------------
        adm = by_title(blocks_on(DAY1)[1], "[TEST] admin")["id"]
        before_plan = D.totals([D.parse_block(r) for r in blocks_on(DAY1)[1]])["planned"]
        rc, out = day("replan", adm, "--start", "16:45", at=DAY1 + "T15:00")
        check("replan needs a reason", rc != 0 and "--reason" in out, out)
        rc, out = day("replan", adm, "--start", "14:10", "--reason", "x", "--yes", at=DAY1 + "T15:00")
        check("replan refuses an overlap", rc == 2 and "overlaps" in out, out)
        rc, out = day("replan", adm, "--start", "16:45", "--reason", "[TEST] priority shift", "--yes", at=DAY1 + "T15:00")
        _, bs4 = blocks_on(DAY1)
        old, new = T.get_record(T.BLOCKS, adm)["fields"], next((r for r in bs4 if (r["fields"].get(B["replaces"]) or {}).get("id") == adm), None)
        check("replan marks the old block moved with the reason", rc == 0 and old[B["status"]] == "moved" and old[B["reason"]] == "[TEST] priority shift", (out, old))
        check("replan creates a successor linked through replaces", new and new["fields"][B["status"]] == "planned" and T.local_dt(new["fields"][B["start"]]).strftime("%H:%M") == "16:45", new and new["fields"])
        check("a move does not double count the day's planned total", D.totals([D.parse_block(r) for r in bs4])["planned"] == before_plan, (D.totals([D.parse_block(r) for r in bs4]), before_plan))
        rc, out = day("replan", adm, "--start", "16:45", "--reason", "x", at=DAY1 + "T15:00")
        check("a moved block cannot be replanned again", rc != 0 and "only a planned block" in out, out)
        eod = by_title(blocks_on(DAY1)[1], "End-of-day meeting")["id"]
        rc, out = day("replan", eod, "--date", MOVED, "--start", "10:00", "--reason", "[TEST] moved a day", "--yes", at=DAY1 + "T15:00")
        moved = next((r for r in blocks_on(MOVED)[1] if (r["fields"].get(B["replaces"]) or {}).get("id") == eod), None)
        check("a routine block moved to another date stops being that date's stamp", rc == 0 and moved and moved["fields"].get(B["source"]) == "plan" and not moved["fields"].get(B["routine"]), (out, moved and moved["fields"]))
        rc, out = day("brief", MOVED, "--json", at=DAY1 + "T15:00")
        check("that date still stamps its own routine", not next(r for r in json.loads(out)["frames"][0]["routines"] if r["title"] == "End-of-day meeting")["stamped"], out[:300])
        # --edit: only unstarted, on a future day
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=DAY2, capacity=600, blocks=[dict(title="[TEST] future", kind="admin", minutes=30, start="11:00")])])), "--yes")
        fut = by_title(blocks_on(DAY2)[1], "[TEST] future")["id"]
        rc, out = day("replan", fut, "--start", "12:00", "--edit", "--yes", at=DAY1 + "T08:00")
        ff = T.get_record(T.BLOCKS, fut)["fields"]
        check("--edit changes a future unstarted block in place", rc == 0 and T.local_dt(ff[B["start"]]).strftime("%H:%M") == "12:00" and ff[B["status"]] == "planned", (out, ff))
        rc, out = day("replan", fut, "--start", "13:00", "--edit", "--yes", at=DAY2 + "T08:00")
        check("--edit is refused once the day has arrived", rc != 0 and "--edit is only" in out, out)
        rc, out = day("replan", fut, "--drop", "--reason", "[TEST] not needed", "--yes", at=DAY1 + "T08:00")
        check("--drop marks the block skipped with the reason", rc == 0 and T.get_record(T.BLOCKS, fut)["fields"][B["status"]] == "skipped", out)

        # --- meetings ------------------------------------------------------------------------------------------------
        t6 = T.create(R.TASKS, [mk("[TEST] task 6")])[0]["id"]   # t1 is finished by now, so it no longer counts as implementation work
        made[R.TASKS].append(t6)
        rc, out = day("meetings", DAY1, "--json", "--tasks", t2, t3, t4, t6, t5)
        m = json.loads(out)
        al = next((p for p in m["proposals"] if p["project_id"] == pr), None)
        check("4 implementation tasks trigger an alignment block with the +1", al and al["signal"] == "alignment" and al["attendee"] == "Aaron Sansoni" and al["attendee_source"] == "your +1", m)
        check("proposals never send anything: a time block only", al and al["kind"] == "meeting" and al["minutes"] == 30 and "draft" not in json.dumps(m).lower())
        sp = next((p for p in m["proposals"] if p["project_id"] == pr2), None)
        check("the Charter sponsor is preferred over the +1", sp and sp["attendee"] == "Dana Example" and sp["signal"] == "unclear", sp)
        rc, out = day("meetings", DAY1, "--json", "--tasks", t1, t2)
        check("2 tasks under the threshold trigger nothing", not [p for p in json.loads(out)["proposals"] if p["project_id"] == pr], out)
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=DAY2, declined_meetings=[dict(project=pr2, signal="unclear", reason="[TEST] not now")])])), "--yes")
        rc, out = day("meetings", DAY1, "--json", "--tasks", t5, at=DAY2 + "T08:00")
        check("a declined proposal stays quiet for 7 days", not [p for p in json.loads(out)["proposals"] if p["project_id"] == pr2], out)
        rc, out = day("meetings", DAY1, "--json", "--tasks", t5, at="2099-01-20T08:00")
        check("a declined proposal can return after 7 days", [p for p in json.loads(out)["proposals"] if p["project_id"] == pr2], out)
        agent = T.resolve_contact("Agentic Mind (Developer)")[0]
        coll = T.create(R.TASKS, [mk("[TEST] agent collab", **{T.TASK_X["collab"]: [{"id": agent}]})])[0]["id"]
        made[R.TASKS].append(coll)
        rc, out = day("meetings", DAY1, "--json", "--tasks", coll)
        check("an agent collaborator is never offered as an attendee", "Agentic Mind" not in out, out)
        T.update(R.PROJECTS, pr, {R.PF["ctx"]: "## Charter\n- Scope: test\n\n## Blockers\n- 2099-01-05 · API key · Sam Example · status open\n"})
        rc, out = day("meetings", DAY1, "--json", "--tasks", t1)
        dep = next((p for p in json.loads(out)["proposals"] if p["project_id"] == pr), None)
        check("an open blocker suggests meeting its owner", dep and dep["signal"] == "dependency" and dep["attendee"] == "Sam Example", dep)
        T.update(R.PROJECTS, pr, {R.PF["ctx"]: "Repo: /tmp/day-flow\n\n## Charter\n- Scope: test\n"})

        # --- task context --------------------------------------------------------------------------------------------
        rc, out = sh("taskctx.py", task_block, "--json", "--no-knowledge", "--at", DAY1 + "T10:30")
        c = json.loads(out)
        check("taskctx from a block loads task, block and time", rc == 0 and c["task"]["id"] == t1 and c["block"]["id"] == task_block and c["time"]["spent_minutes"] == 80, out)
        check("taskctx loads project, charter, repo and goal", c["project"]["id"] == pr and "Scope: test" in c["project"]["charter"] and c["project"]["repo"] == "/tmp/day-flow" and c["goal"]["id"] == g, c["project"])
        check("taskctx loads people and related tasks", c["people"]["assignee"] == "Avarile" and len(c["related"]["next_open"]) >= 1, c["people"])
        rc, out = sh("taskctx.py", "now", "--json", "--no-knowledge", "--at", DAY1 + "T14:05")
        check("taskctx now uses the time", rc == 0 and json.loads(out)["resolved_by"] == "current block", out)
        rc, out = sh("taskctx.py", "[TEST] task", "--no-knowledge")
        check("an ambiguous title lists choices and exits 4", rc == 4 and "Which one" in out, out)
        rc, out = sh("taskctx.py", "recNoSuchRecord000000", "--no-knowledge")
        check("an unknown id exits 3 and guesses nothing", rc == 3, out)
        rc, out = sh("taskctx.py", t2, "--json")
        k = json.loads(out)["knowledge"]
        check("taskctx loads knowledge through kb.py", rc == 0 and k["available"] and all(set(e) <= {"id", "title", "type", "score"} for e in k["suggested"]), k)

        # --- generated output ----------------------------------------------------------------------------------------
        rc, out = sh("write.py", "gen-append", R.TASKS, t2, "--prompt", "First", "--text", "One", "--model", "test")
        check("gen-append dry-run writes nothing", rc == 0 and "DRY RUN" in out and not T.get_record(R.TASKS, t2)["fields"].get(T.TASK_X["gen"]), out)
        rc, out = sh("write.py", "gen-append", R.TASKS, t2, "--prompt", "First", "--text", "One", "--model", "test", "--yes")
        rc2, out2 = sh("write.py", "gen-append", R.TASKS, t2, "--prompt", "Second", "--text", "Two", "--context", "task", "--yes")
        g2 = T.get_record(R.TASKS, t2)["fields"][T.TASK_X["gen"]]
        check("gen-append keeps earlier entries, newest last", rc == 0 and rc2 == 0 and g2.index("First") < g2.index("Second") and "One" in g2 and "Two" in g2 and len(re.findall("^### ◆ ", g2, re.M)) == 2, g2)
        rc, out = sh("taskctx.py", t2, "--json", "--no-knowledge")
        check("earlier output comes back marked untrusted", all(e["untrusted"] for e in json.loads(out)["task"]["generated"]) and len(json.loads(out)["task"]["generated"]) == 2, out)
        rc, out = sh("write.py", "gen-append", T.PLANS, pl["id"], "--prompt", "x", "--text", "y")
        check("gen-append refuses other tables", rc != 0, out)

        # --- review ------------------------------------------------------------------------------------------------
        rc, out = day("review", DAY1, "--json", at=DAY2 + "T08:00")
        rv = json.loads(out)
        check("review reports totals and carry-over candidates", rc == 0 and rv["totals"]["actual"] == 80 and t2 in rv["carry"], rv)
        rc, out = day("brief", DAY2, "--json", at=DAY2 + "T08:00")
        br = json.loads(out)
        check("an unreviewed past day is raised first", any(o["date"] == DAY1 for o in br["open_days"]), br["open_days"])
        c2 = next((x for x in br["candidates"] if x["id"] == t2), None)
        check("unfinished work comes back as a carry-over, ranked first", c2 and c2["tier"] == 0 and "carried" in c2["why"], c2)
        rc, out = day("review", DAY1, "--all-as-planned", at=DAY2 + "T08:00")
        check("review dry-run writes nothing", rc == 0 and "DRY RUN" in out and T.get_record(T.PLANS, pl["id"])["fields"][P["status"]] != "reviewed", out)
        unknown = T.create(T.PLANS, [{P["date"]: "2099-01-07", P["status"]: "running", P["notes"]: "[TEST]"}])[0]["id"]
        made[T.PLANS].append(unknown)
        ub = T.create(T.BLOCKS, [{B["title"]: "[TEST] unknown", B["day"]: {"id": unknown}, B["kind"]: "admin", B["status"]: "planned", B["minutes"]: 30}])[0]["id"]
        made[T.BLOCKS].append(ub)
        rc, out = day("review", "2099-01-07", "--leave-unknown", "--yes", at="2099-01-08T08:00")
        check("--leave-unknown closes the day without inventing outcomes", rc == 0 and T.get_record(T.PLANS, unknown)["fields"][P["status"]] == "reviewed" and T.get_record(T.BLOCKS, ub)["fields"][B["status"]] == "planned" and not T.get_record(T.BLOCKS, ub)["fields"].get(B["actual_minutes"]), out)
        rc, out = day("review", DAY1, "--all-as-planned", "--text", "[TEST] closed", "--yes", at=DAY2 + "T08:00")
        fp = T.get_record(T.PLANS, pl["id"])["fields"]
        check("review closes the day and stores the text", rc == 0 and fp[P["status"]] == "reviewed" and "[TEST] closed" in fp.get(P["review"], ""), (out, fp.get(P["status"])))
        sb = T.get_record(T.BLOCKS, by_title(bs, "[TEST] sync")["id"])["fields"]
        check("all-as-planned copies planned time into actuals", sb[B["status"]] == "done" and sb[B["actual_minutes"]] == 30 and sb.get(B["actual_start"]) == sb.get(B["start"]), sb)
        check("all-as-planned leaves moved blocks alone", T.get_record(T.BLOCKS, adm)["fields"][B["status"]] == "moved")
        rc, out = day("apply", "--input", spec(dict(days=[dict(date=DAY1, blocks=[dict(title="[TEST] late", kind="admin", minutes=15)])])), "--yes", at=DAY1 + "T08:00")
        check("a reviewed day refuses new blocks", rc == 2 and "already reviewed" in out, out)
        rc, out = day("time", "--from", DAY1, "--to", DAY1, "--json", at=DAY2 + "T08:00")
        tm = json.loads(out)
        check("time report totals by kind", rc == 0 and tm["by_kind"]["meeting"]["planned"] >= 30 and tm["totals"]["actual"] > 80, tm)

        # --- audit: plant one of each problem ----------------------------------------------------------------------
        bad_plan = T.create(T.PLANS, [{P["date"]: "2099-02-02", P["status"]: "running"}])[0]["id"]
        made[T.PLANS].append(bad_plan)
        mkb = lambda t, **k: dict({B["title"]: t, B["day"]: {"id": bad_plan}, B["kind"]: "admin"}, **k)
        planted = T.create(T.BLOCKS, [mkb("[TEST] over a", **{B["start"]: T.utc_iso(dt.date(2099, 2, 2), 600), B["minutes"]: 60, B["status"]: "planned"}), mkb("[TEST] over b", **{B["start"]: T.utc_iso(dt.date(2099, 2, 2), 620), B["minutes"]: 60, B["status"]: "planned"}),
                                       mkb("[TEST] moved no reason", **{B["status"]: "moved"}), mkb("[TEST] routine no link", **{B["source"]: "routine"}), mkb("[TEST] adhoc planned", **{B["source"]: "adhoc", B["minutes"]: 10})])
        made[T.BLOCKS] += [r["id"] for r in planted]
        rc, out = day("check", "--json", at="2099-03-01T08:00")
        text = out
        for name, needle in (("overlap", "[TEST] over a overlaps [TEST] over b"), ("unreviewed day", "2099-02-02 was never reviewed"), ("moved without reason", "moved block [TEST] moved no reason has no reason"),
                             ("moved without successor", "moved block [TEST] moved no reason has no replacement"), ("routine without link", "routine block [TEST] routine no link"), ("adhoc with plan", "adhoc block [TEST] adhoc planned")):
            check("check finds: " + name, needle in text, needle)
        dup = T.create(T.PLANS, [{P["date"]: "2099-02-02", P["status"]: "planned"}])[0]["id"]
        made[T.PLANS].append(dup)
        rc, out = day("check", "--json", at="2099-03-01T08:00")
        check("check finds: duplicate day", "2 plan rows for 2099-02-02" in out, out[:200])

        # --- routines ------------------------------------------------------------------------------------------------
        rc, out = day("routine", "add", "--name", "[TEST] routine", "--freq", "weekly", "--weekdays", "Wed", "--start", "11:00", "--minutes", "30", "--kind", "admin", "--valid-from", "2099-03-01", "--valid-until", "2099-03-31")
        check("routine add is a dry run by default", rc == 0 and "DRY RUN" in out, out)
        rc, out = day("routine", "add", "--name", "[TEST] routine", "--freq", "weekly", "--weekdays", "Wed", "--start", "11:00", "--minutes", "30", "--kind", "admin", "--valid-from", "2099-03-01", "--valid-until", "2099-03-31", "--yes")
        rid = re.search(r"routine (rec\w+)", out)
        check("routine add writes", rc == 0 and rid, out)
        rid = rid[1]
        made[T.ROUTINES].append(rid)
        rc, out = day("brief", "2099-03-04", "--json", at="2099-03-02T08:00")
        check("a new routine falls on its day", any(r["title"] == "[TEST] routine" for r in json.loads(out)["frames"][0]["routines"]), out[:300])
        rc, out = day("routine", "pause", rid, "--yes", at="2099-03-02T08:00")
        rc2, out2 = day("brief", "2099-03-04", "--json", at="2099-03-02T08:00")
        check("a paused routine stops falling", rc == 0 and not any(r["title"] == "[TEST] routine" for r in json.loads(out2)["frames"][0]["routines"]), out)
        rc, out = day("routine", "resume", rid, "--yes", at="2099-03-02T08:00")
        check("routine resume writes", rc == 0 and T.get_record(T.ROUTINES, rid)["fields"].get(Q["active"]) is True, out)
    finally:
        # --- cleanup: only ids created in this run ------------------------------------------------------------------
        for date in (DAY1, DAY2, MOVED, WINTER, "2099-01-07", "2099-02-02"):
            blocks_on(date)
        for t in (T.BLOCKS, T.PLANS, T.ROUTINES, R.TASKS, R.PROJECTS, R.GOALS):
            for chunk in [made[t][i:i + 50] for i in range(0, len(made[t]), 50)]:
                if chunk:
                    T.delete_records(t, chunk)
        check("cleanup: row counts back to baseline", counts() == base, (counts(), base))
    print("\n%d/%d passed" % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
