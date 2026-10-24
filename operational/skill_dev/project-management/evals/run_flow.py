#!/usr/bin/env python3
"""End-to-end acceptance test of the scripts against the live database. Uses only [TEST] rows it creates and
deletes only ids it created (re-checked for the [TEST] prefix / test-project membership), then verifies the
baseline row and view counts are restored. Exit 0 = all passed.

  python3 evals/run_flow.py            (needs CYBERNETICS_DATA_API_TOKEN in env or .env)
"""
import datetime as dt, json, re, subprocess, sys
from pathlib import Path
SC = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SC))
import teable as T, scaffold as S, rollup as R, write as W  # noqa: E402

GOALS, PROJECTS, TASKS = R.GOALS, R.PROJECTS, R.TASKS
KNOW = "tblVTWb1kxXSFPBq4Fq"
CON = T.CONTACTS
results, created = [], {"tasks": [], "projects": [], "goals": [], "views": [], "knowledge": [], "contacts": []}


def check(name, ok, detail=""):
    ok = bool(ok)
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + ((" -- " + str(detail)) if detail and not ok else ""))


def sh(*args):
    p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=SC, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def counts():
    return {t: len(T.get_records(t, projection=[])) for t in (GOALS, PROJECTS, TASKS, KNOW, CON)}, \
           {t: len(T.call("GET", "/api/table/%s/view" % t)) for t in (GOALS, PROJECTS, TASKS)}


def roll(pid, today):
    proj = T.get_record(PROJECTS, pid)
    tasks = T.get_records(TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid)]))
    gl = (proj["fields"].get(R.PF["goal"]) or {}).get("id")
    dl = T.local_date(T.get_record(GOALS, gl, [R.GF["deadline"]])["fields"].get(R.GF["deadline"])) if gl else None
    return R.project_rollup(proj, tasks, today, dl)


def main():
    base_rows, base_views = counts()
    start = dt.date.fromisoformat("2026-11-02")  # a Monday, far from real data; all dates are test-controlled
    orphans0 = len(T.get_records(TASKS, T.and_filter(["%s isEmpty" % R.TF["proj"]]), []))
    try:
        # --- create goal + project (REST) -------------------------------------------------
        g = T.call("POST", "/api/table/%s/record" % GOALS, body={"fieldKeyType": "id", "records": [{"fields": {
            R.GF["title"]: "[TEST] eval goal", R.GF["deadline"]: "2026-12-31",
            R.GF["ctx"]: "## Key Results\n| KR | Metric | Baseline | Target | Current | Score |\n|---|---|---|---|---|---|\n| KR1 | a | 0 | 10 | 2 | 0.2 |\n| KR2 | b | 0 | 10 | 5 | 0.5 |\n"}}]})
        gid = g["records"][0]["id"]; created["goals"].append(gid)
        status = "## Status Log\n### %s · 🟢 GREEN\nstart\n" % start.isoformat()
        p = T.call("POST", "/api/table/%s/record" % PROJECTS, body={"fieldKeyType": "id", "records": [{"fields": {
            R.PF["title"]: "[TEST] eval project", R.PF["prog"]: "in-progress", R.PF["goal"]: {"id": gid},
            R.PF["ctx"]: "Moves: KR1\nRepo: /tmp/eval-repo-xyz\nShape: build\n\n## Charter\n- Scope: test\n- Estimate: best 20d / likely 28d / worst 40d; buffer 20%\n\n" + status}}]})
        pid = p["records"][0]["id"]; created["projects"].append(pid)
        check("create goal and project via REST", bool(gid and pid))

        # --- scaffold ---------------------------------------------------------------------
        rc, out = sh("scaffold.py", "build", "--start", start, "--days", 28, "--project-id", pid, "--create")
        check("scaffold dry-run writes nothing", rc == 0 and "DRY RUN" in out and not T.get_records(TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid)])), out[-200:])
        rc, out = sh("scaffold.py", "build", "--start", start, "--days", 28, "--project-id", pid, "--create", "--yes")
        tasks = T.get_records(TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid)]))
        created["tasks"] = [t["id"] for t in tasks]
        check("scaffold --create makes 14 linked tasks", rc == 0 and len(tasks) == 14, (rc, len(tasks), out[-200:]))
        check("task defaults and Due lines", all("Due: " in (t["fields"].get(R.TF["ctx"]) or "") for t in tasks)
              and all(t["fields"].get(R.TF["prog"]) == "backlog" for t in tasks))
        rc, out = sh("scaffold.py", "build", "--start", start, "--days", 28, "--project-id", pid, "--create", "--yes")
        check("re-scaffold into a populated project is refused", rc != 0 and "already has tasks" in out, out[-150:])
        exp, _ = S.expand(S.load("build"), start, 28, 0.2)
        by_step = {int(R.parse_task(t, start)["step"]): t["id"] for t in tasks}
        due = {e["step"]: dt.date.fromisoformat(e["due"]) for e in exp}

        # --- rollup: GREEN / AMBER / RED with controlled dates -----------------------------
        r = roll(pid, start)
        check("GREEN before anything is due", r["rag"] == "GREEN" and r["completion"] == 0.0 and r["spi"] is None, r)
        cut = due[7] + dt.timedelta(days=1)  # one day after step 7 is due, so it is overdue (due today is not)
        planned = [s for s, d in due.items() if d <= cut]
        target = 7
        todo = [by_step[s] for s in planned if s != target]
        rc, out = sh("write.py", "bulk-update", TASKS, "--ids", *todo, "--set", "%s=finished_validating" % R.TF["prog"], "--yes")
        check("bulk-update to finished (verified)", rc == 0 and "verification ok" in out, out[-200:])
        # status entry must be recent for GREEN/AMBER logic: append one dated cut
        rc, out = sh("write.py", "ctx-append", PROJECTS, pid, "--field", R.PF["ctx"], "--section", "## Status Log",
                     "--text", "### %s · 🟡 AMBER\nmid" % cut.isoformat(), "--yes")
        check("ctx-append status entry", rc == 0 and "verified" in out, out[-150:])
        r = roll(pid, cut)
        check("AMBER: one overdue, SPI >= 0.85", r["rag"] == "AMBER" and len(r["overdue"]) == 1 and r["spi"] is not None and r["spi"] >= 0.85
              and any("overdue" in x for x in r["rules"]), r)
        r = roll(pid, start + dt.timedelta(days=200))
        check("RED when everything is overdue", r["rag"] == "RED" and any("overdue" in x for x in r["rules"]), r["rules"])
        # gate rule in isolation: reopen gate (step 4) only, look at a day shortly after it is >3 days late
        rc, out = sh("write.py", "bulk-update", TASKS, "--ids", by_step[4], "--set", "%s=backlog" % R.TF["prog"], "--yes")
        r = roll(pid, due[4] + dt.timedelta(days=5))
        check("RED rule: gate task overdue > 3 days", r["rag"] == "RED" and any(x.startswith("gate task overdue") for x in r["rules"]), r["rules"])
        check("next gate reported", r["next_gate"] and "Step 04" in r["next_gate"]["title"], r["next_gate"])
        # status gap + unmitigated risk
        r = roll(pid, cut + dt.timedelta(days=12))
        check("status-gap rule", any("no status entry" in x for x in r["rules"]), r["rules"])
        rc, out = sh("write.py", "ctx-append", PROJECTS, pid, "--field", R.PF["ctx"], "--section", "## Risk Register", "--yes",
                     "--text", "| Risk | Likelihood | Impact | Owner | Mitigation | Status |\n|---|---|---|---|---|---|\n| API outage | Medium | High | me |  | open |")
        r = roll(pid, start)
        check("unmitigated high-impact risk -> AMBER rule", r["open_risks"] == 1 and any("without mitigation" in x for x in r["rules"]), r)

        # --- goal + portfolio ---------------------------------------------------------------
        gr = R.goal_rollup(T.get_record(GOALS, gid), [r], start)
        check("goal rollup: KR avg 0.35, runway", gr["kr_avg"] == 0.35 and gr["runway_days"] == (dt.date(2026, 12, 31) - start).days, gr)
        rc, out = sh("rollup.py", "portfolio", "--today", start, "--json")
        pj = json.loads(out)
        check("portfolio lists the goal and keeps orphan count", any(x["id"] == gid for x in pj["goals"]) and pj["orphan_tasks"] == orphans0, (pj["orphan_tasks"], orphans0))

        # --- guards -------------------------------------------------------------------------
        rc, out = sh("write.py", "bulk-update", TASKS, "--ids", by_step[1], "--set", "%s=finished-validating" % R.TF["prog"], "--yes")
        check("bad enum spelling refused before any write", rc != 0 and "invalid option" in out
              and T.get_record(TASKS, by_step[1], [R.TF["prog"]])["fields"].get(R.TF["prog"]) == "finished_validating", out[-160:])
        rc, out = sh("write.py", "bulk-update", TASKS, "--set", "%s=urgent" % R.TF["prio"])
        check("bulk-update without a target is refused", rc != 0, out[-100:])
        # concurrent edit abort
        real, calls = T.get_record, {"n": 0}
        def racing(table, rid, proj=()):
            calls["n"] += 1
            x = real(table, rid, proj)
            if calls["n"] == 2:
                x["fields"][R.PF["ctx"]] += "\nHUMAN"
            return x
        before = real(PROJECTS, pid, [R.PF["ctx"]])["fields"][R.PF["ctx"]]
        W.T.get_record = racing
        try:
            import argparse
            W.cmd_ctx_append(argparse.Namespace(table=PROJECTS, record=pid, field=R.PF["ctx"], section="## Status Log", text="### NO", text_file=None, yes=True))
            aborted = False
        except SystemExit as e:
            aborted = "ABORT" in str(e)
        finally:
            W.T.get_record = real
        check("concurrent edit aborts without writing", aborted and real(PROJECTS, pid, [R.PF["ctx"]])["fields"][R.PF["ctx"]] == before)

        # --- knowledge trace + view ----------------------------------------------------------
        K = "recrOLgVTcrjEKiqBuj"
        T.call("PATCH", "/api/table/%s/record/%s" % (PROJECTS, pid), body={"fieldKeyType": "id", "record": {"fields": {"fldCw3cnpw8EWs09C1v": [{"id": K}]}}})
        hit = T.get_records(PROJECTS, T.and_filter(["fldCw3cnpw8EWs09C1v hasAnyOf %s" % K]), [R.PF["title"]])
        check("trace: reverse lookup by hasAnyOf", [x["id"] for x in hit] == [pid], hit)
        rc, out = sh("views.py", "create", TASKS, "--name", "[TEST] eval view", "--filter", "%s is urgent" % R.TF["prio"], "--yes")
        vid = next((l.split()[1] for l in out.splitlines() if l.startswith("created ")), None)
        if vid:
            created["views"].append(vid)
        check("filtered view created with filter stored", rc == 0 and vid is not None, out[-200:])

        # --- Phase 2: resume (agent entry point) -------------------------------------------------
        import os
        rc, out = sh("resume.py", "--path", "/tmp/eval-repo-xyz/sub/dir", "--json")
        b = json.loads(out) if rc == 0 else {}
        check("resume: path inside Repo matches confidently", rc == 0 and b.get("project", {}).get("id") == pid and b["match"]["score"] == 3
              and len(b["next"]) == 3 and b["charter"], out[-200:])
        rc, out = sh("resume.py", "--path", "/somewhere/else/eval-repo-xyz", "--json")
        b = json.loads(out) if rc == 0 else {}
        check("resume: directory name equals Repo basename (score 2)", rc == 0 and b["match"]["score"] == 2 and b["match"]["how"] == "name", out[-150:])
        rc, out = sh("resume.py", "--path", "/nonexistent-qq-zz")
        check("resume: no match exits 3 with guidance", rc == 3 and "NO MATCH" in out, (rc, out[-120:]))
        rc, out = sh("resume.py", "--hook", "--path", "/tmp/eval-repo-xyz")
        hk = json.loads(out) if out.strip().startswith("{") else {}
        check("resume --hook: emits SessionStart additionalContext", "[TEST] eval project" in hk.get("hookSpecificOutput", {}).get("additionalContext", ""), out[-150:])
        rc, out = sh("resume.py", "--hook", "--path", "/nonexistent-qq-zz")
        check("resume --hook: silent on no match", rc == 0 and out.strip() == "", out[-100:])
        p2 = T.call("POST", "/api/table/%s/record" % PROJECTS, body={"fieldKeyType": "id", "records": [{"fields": {
            R.PF["title"]: "[TEST] eval project twin", R.PF["prog"]: "in-progress", R.PF["ctx"]: "Repo: /tmp/eval-repo-xyz\n"}}]})
        created["projects"].append(p2["records"][0]["id"])
        rc, out = sh("resume.py", "--path", "/tmp/eval-repo-xyz")
        check("resume: two projects with the same Repo -> ambiguous, exit 4", rc == 4 and "AMBIGUOUS" in out, (rc, out[-150:]))
        rc, out = sh("resume.py", "--hook", "--path", "/tmp/eval-repo-xyz")
        check("resume --hook: silent when ambiguous", rc == 0 and out.strip() == "")

        # --- Phase 2: close ----------------------------------------------------------------------
        rc, out = sh("close.py", "check", pid)
        check("close check: NOT READY while tasks are open", rc == 1 and "FAIL all tasks finished" in out and "NOT READY" in out, out[-300:])
        fin_day, st_day = start + dt.timedelta(days=30), start
        rc, out = sh("write.py", "bulk-update", TASKS, "--filter", "%s is %s" % (R.TF["proj"], pid),
                     "--set", "%s=finished_validating" % R.TF["prog"], "--set", "fldj3Xb1g9nUX4iFqE0=%s" % st_day.isoformat(),
                     "--set", "fldn95wbkTqefn18WdO=%s" % fin_day.isoformat(), "--yes")
        check("bulk finish all tasks with started_at/finished_at (dates verified in Melbourne time)", rc == 0 and "verification ok" in out, out[-200:])
        for sec, txt in (("## Retro", "Went well: scope held. Do differently: estimate the review step."), ("## Lessons", "- Gate the charter early -> knowledge: [TEST] eval lessons")):
            rc, out = sh("write.py", "ctx-append", PROJECTS, pid, "--field", R.PF["ctx"], "--section", sec, "--text", txt, "--yes")
        k = T.call("POST", "/api/table/%s/record" % KNOW, body={"fieldKeyType": "id", "records": [{"fields": {
            "fldROFj15OlD8COVxX0": "[TEST] eval lessons", "fld5tr2rH8oJXLrjUo9": "## Lessons\n- test"}}]})
        kid = k["records"][0]["id"]; created["knowledge"].append(kid)
        T.call("PATCH", "/api/table/%s/record/%s" % (PROJECTS, pid), body={"fieldKeyType": "id", "record": {"fields": {"fldCw3cnpw8EWs09C1v": [{"id": kid}]}}})
        rc, out = sh("close.py", "check", pid)
        only_est = [l for l in out.splitlines() if l.startswith("FAIL")]
        check("close check: only the Estimation Record is missing", rc == 1 and len(only_est) == 1 and "Estimation Record" in only_est[0], out[-400:])
        rc, out = sh("close.py", "stats", pid, "--json")
        st = json.loads(out)
        late = sum(1 for e in exp if dt.date.fromisoformat(e["due"]) < fin_day)
        want_on_time = round(100 * (len(exp) - late) / len(exp))
        check("close stats: actual 30d vs likely 28d, ratio 1.07, within the declared 20% buffer",
              st["actual_days"] == 30 and st["estimate"]["likely"] == 28 and st["actual_vs_likely"] == 1.07 and st["within_declared_buffer"] is True
              and st["shape"] == "build" and st["buffer"] == 0.2, st)
        check("close stats: on-time %% equals independent calculation (%d%%)" % want_on_time, st["on_time_pct"] == want_on_time and st["judged"] == 14, (st["on_time_pct"], want_on_time))
        rc, out = sh("write.py", "ctx-append", PROJECTS, pid, "--field", R.PF["ctx"], "--section", "## Estimation Record", "--yes",
                     "--text", "| Project | Shape | Likely | Actual | Actual/Likely | On-time | Finished |\n|---|---|---|---|---|---|---|\n" + st["row"])
        rc, out = sh("close.py", "check", pid)
        check("close check: READY once every criterion is met", rc == 0 and "READY" in out and "NOT READY" not in out, out[-300:])

        # --- Phase 3: assignment ---------------------------------------------------------------
        def mk_contact(name):
            r = T.call("POST", "/api/table/%s/record" % CON, body={"fieldKeyType": "id", "records": [{"fields": {T.CONTACT_TITLE: name}}]})
            created["contacts"].append(r["records"][0]["id"])
            return r["records"][0]["id"]
        ann, annm, bot = mk_contact("[TEST] Ann"), mk_contact("[TEST] Ann Marie"), mk_contact("[TEST] Bot")
        ap = T.call("POST", "/api/table/%s/record" % PROJECTS, body={"fieldKeyType": "id", "records": [{"fields": {
            R.PF["title"]: "[TEST] eval assign project", R.PF["prog"]: "in-progress",
            R.PF["ctx"]: "Repo: /tmp/eval-assign-repo\nShape: personal-small\n\n## Status Log\n### %s\nstart\n" % start.isoformat()}}]})["records"][0]["id"]
        created["projects"].append(ap)

        def who(pid_):
            rows = T.get_records(TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid_)]), [R.TF["title"], R.TF["who"]])
            return {re.search(r"\[(\w+)\]", r["fields"][R.TF["title"]]).group(1) + r["fields"][R.TF["title"]][5:7]: (r["fields"].get(R.TF["who"]) or {}).get("title") for r in rows}
        rc, out = sh("scaffold.py", "personal-small", "--start", start, "--days", 14, "--project-id", ap, "--create", "--yes",
                     "--assign", "PLAN=[TEST] Ann", "--assign", "DO=[TEST] Bot")
        w = who(ap)
        check("scaffold --assign: PLAN -> Ann (exact name beats 'Ann Marie'), DO -> Bot, CHECK/ACT unassigned",
              rc == 0 and w["PLAN01"] == "[TEST] Ann" and all(w[k] == "[TEST] Bot" for k in ("DO02", "DO03", "DO04"))
              and w["CHECK05"] is None and w["ACT06"] is None, (rc, w, out[-200:]))
        rc, out = sh("scaffold.py", "personal-small", "--start", start, "--assign", "PLAN=[TEST] An")
        check("scaffold --assign with an ambiguous name is refused", rc != 0 and "ambiguous" in out, out[-160:])
        rc, out = sh("assign.py", "set", "--to", "[TEST] An", "--project", ap, "--yes")
        check("assign: ambiguous contact exits without writing", rc != 0 and "ambiguous" in out and who(ap) == w, out[-160:])
        rc, out = sh("assign.py", "set", "--to", "Nobody At All", "--project", ap, "--yes")
        check("assign: unknown contact exits without writing", rc != 0 and "no contact matches" in out and who(ap) == w, out[-160:])
        rc, out = sh("assign.py", "set", "--to", "[TEST] Ann", "--project", ap, "--phase", "CHECK,ACT")
        check("assign: dry-run reports 2 changes and writes nothing", rc == 0 and "2 to change" in out and "DRY RUN" in out and who(ap) == w, out[-250:])
        rc, out = sh("assign.py", "set", "--to", "[TEST] Ann", "--project", ap, "--phase", "CHECK,ACT", "--yes")
        w2 = who(ap)
        check("assign: --yes assigns CHECK and ACT to Ann (verified)", rc == 0 and w2["CHECK05"] == "[TEST] Ann" and w2["ACT06"] == "[TEST] Ann" and "verification ok" in out, out[-250:])
        rc, out = sh("assign.py", "set", "--to", "[TEST] Ann", "--project", ap, "--phase", "DO", "--yes")
        check("assign: tasks held by someone else are skipped, not taken", rc == 0 and "3 held by someone else" in out and "nothing to change" in out
              and all(who(ap)[k] == "[TEST] Bot" for k in ("DO02", "DO03", "DO04")), out[-250:])
        rc, out = sh("assign.py", "set", "--to", "[TEST] Ann", "--project", ap, "--phase", "DO", "--reassign", "--yes")
        check("assign: --reassign takes over DO tasks", rc == 0 and all(who(ap)[k] == "[TEST] Ann" for k in ("DO02", "DO03", "DO04")), out[-250:])
        rc, out = sh("assign.py", "set", "--to", "none", "--project", ap, "--phase", "ACT", "--reassign", "--yes")
        check("assign: --to none clears the assignee", rc == 0 and who(ap)["ACT06"] is None, out[-250:])
        rc, out = sh("assign.py", "lead", ap, "--to", "[TEST] Bot", "--yes")
        lead = lambda: T.contact_name((T.get_record(PROJECTS, ap, [R.PF["lead"]])["fields"].get(R.PF["lead"]) or {}).get("id"))
        check("lead: sets lead_by", rc == 0 and lead() == "[TEST] Bot", out[-200:])
        rc, out = sh("assign.py", "lead", ap, "--to", "[TEST] Ann", "--yes")
        check("lead: replacing an existing lead needs --reassign", rc != 0 and "already has lead" in out and lead() == "[TEST] Bot", out[-200:])
        rc, out = sh("assign.py", "lead", ap, "--to", "[TEST] Ann", "--reassign", "--yes")
        check("lead: --reassign replaces the lead", rc == 0 and lead() == "[TEST] Ann", out[-200:])

        rc, out = sh("assign.py", "workload", "--project", ap, "--today", start, "--json")
        wl = json.loads(out)
        check("workload: Ann 5 open, 1 unassigned, Ann leads the project, no WIP flag",
              wl["people"]["[TEST] Ann"]["open"] == 5 and wl["people"]["(unassigned)"]["open"] == 1
              and "[TEST] eval assign project" in wl["leads"].get("[TEST] Ann", []) and not wl["flags"], wl)
        rc, out = sh("assign.py", "tasks", "--contact", "[TEST] Ann", "--project", ap, "--today", start, "--json")
        tj = json.loads(out)
        check("tasks --contact: Ann's 5 open tasks, none of the unassigned", tj["open"] == 5 and tj["contact"] == "[TEST] Ann", tj)
        rc, out = sh("rollup.py", "project", ap, "--today", start, "--json")
        rj = json.loads(out)
        check("rollup: by_assignee and lead are reported", rj["by_assignee"] == {"[TEST] Ann": 5, "unassigned": 1} and rj["lead"] == "[TEST] Ann", rj["by_assignee"])
        rc, out = sh("resume.py", "--path", "/tmp/eval-assign-repo", "--as", "[TEST] Ann", "--json")
        rb = json.loads(out)
        check("resume --as Ann: only Ann's tasks, 1 unassigned claimable", rc == 0 and rb["as_contact"] == "[TEST] Ann" and len(rb["next"]) == 3 and rb["claimable_count"] == 1, out[-250:])
        rc, out = sh("resume.py", "--path", "/tmp/eval-assign-repo", "--as", "[TEST] Bot", "--json")
        rb = json.loads(out)
        check("resume --as Bot: nothing assigned to them, still sees the claimable task", rc == 0 and rb["next"] == [] and rb["in_progress"] == [] and rb["claimable_count"] == 1, out[-250:])
        rc, out = sh("resume.py", "--path", "/tmp/eval-assign-repo", "--as", "[TEST] An")
        check("resume --as with an ambiguous name is refused", rc != 0 and "ambiguous" in out, out[-160:])
        rc, out = sh("resume.py", "--path", "/tmp/eval-assign-repo", "--json")
        check("resume without --as is unchanged (all open tasks)", rc == 0 and "as_contact" in json.loads(out) and json.loads(out)["as_contact"] is None, out[-160:])
    finally:
        # --- cleanup (only ids created in this run) ------------------------------------------
        for v in created["views"]:
            T.delete_view(TASKS, v)
        for pj in created["projects"]:
            nm = T.get_record(PROJECTS, pj, [R.PF["title"]])["fields"].get(R.PF["title"], "")
            if str(nm).startswith("[TEST]"):
                live = T.get_records(TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pj)]), [])
                if live:
                    T.delete_records(TASKS, [t["id"] for t in live])
        for tbl, key in ((PROJECTS, "projects"), (GOALS, "goals")):
            for rid in created[key]:
                title = T.get_record(tbl, rid, [R.PF["title"] if tbl == PROJECTS else R.GF["title"]])["fields"]
                name = list(title.values())[0] if title else ""
                if str(name).startswith("[TEST]"):
                    T.delete_records(tbl, [rid])
        for cid in created["contacts"]:
            cn = T.get_record(CON, cid, [T.CONTACT_TITLE])["fields"].get(T.CONTACT_TITLE, "")
            if str(cn).startswith("[TEST]"):
                T.delete_records(CON, [cid])
        for kid in created["knowledge"]:
            kt = T.get_record(KNOW, kid, ["fldROFj15OlD8COVxX0"])["fields"].get("fldROFj15OlD8COVxX0", "")
            if str(kt).startswith("[TEST]"):
                T.delete_records(KNOW, [kid])
        rows, views = counts()
        check("cleanup: row counts back to baseline", rows == base_rows, (rows, base_rows))
        check("cleanup: view counts back to baseline", views == base_views, (views, base_views))
    n = len(results)
    print("\n%d/%d passed" % (sum(results), n))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
