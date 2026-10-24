#!/usr/bin/env python3
"""Create / drop a small realistic fixture dataset for the behavioral evals (live database writes).

  make_fixture.py create    builds a goal, projects 'Website Refresh', 'k3s Migration', 'Inbox' with tasks
  make_fixture.py drop      deletes exactly what `create` made (ids in evals/fixture_manifest.json; every
                            goal/project is re-checked for the EVAL-FIXTURE marker before deletion)

Links point at REAL contacts (Avarile, Anastasia Wang, Agentic Mind (Developer)); `drop` removes the tasks and
projects, which clears those links. Nothing else is modified.
"""
import datetime as dt, json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
SC = HERE.parent / "scripts"
sys.path.insert(0, str(SC))
import teable as T, rollup as R  # noqa: E402

MANIFEST = HERE / "fixture_manifest.json"
MARK = "EVAL-FIXTURE"
DEV, ME, ANA = "Agentic Mind (Developer)", "Avarile", "Anastasia Wang"


def post(table, fields):
    return T.call("POST", "/api/table/%s/record" % table, body={"fieldKeyType": "id", "records": [{"fields": fields}]})["records"][0]["id"]


def sh(*a):
    p = subprocess.run([sys.executable, *map(str, a)], capture_output=True, text=True, cwd=SC, stdin=subprocess.DEVNULL)
    if p.returncode:
        sys.exit("FAILED %s\n%s%s" % (a, p.stdout, p.stderr))
    return p.stdout


def step_ids(pid):
    out = {}
    for r in T.get_records(R.TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid)]), [R.TF["title"]]):
        n = int(R.parse_task(r, None)["step"])
        out[n] = r["id"]
    return out


def create():
    if MANIFEST.exists():
        sys.exit("fixture already exists (%s); run drop first" % MANIFEST)
    today = T.today()
    me_id, _ = T.resolve_contact(ME)
    m = {"projects": [], "goal": None, "created": today.isoformat()}
    save = lambda: MANIFEST.write_text(json.dumps(m, indent=1))
    m["goal"] = post(R.GOALS, {R.GF["title"]: "Become the most reliable agent platform in our vertical", R.GF["deadline"]: "2026-12-31",
        R.GF["ctx"]: "## Key Results\n| KR | Metric | Baseline | Target | Current | Score | Owner | Date |\n|---|---|---|---|---|---|---|---|\n"
                     "| KR1 | Agent task success rate | 87% | 94% | 89% | 0.29 | Avarile | 2026-12-31 |\n| KR2 | p95 latency (s) | 3.0 | 1.8 | 2.4 | 0.50 | Avarile | 2026-12-31 |\n\n## Check-ins\n\n" + MARK + "\n"})
    save()
    d = lambda n: (today + dt.timedelta(days=n)).isoformat()

    # ---- Website Refresh: in progress, amber, assigned across people/agent, some unassigned
    wr = post(R.PROJECTS, {R.PF["title"]: "Website Refresh", R.PF["prog"]: "in-progress", R.PF["goal"]: {"id": m["goal"]}, R.PF["lead"]: {"id": me_id},
        R.PF["ctx"]: "Moves: KR1\nRepo: /work/site-refresh\nShape: build\n\n## Charter\n- Scope: Redesign and rebuild the marketing site on the new CMS.\n"
                     "- Out of scope: Blog migration, SEO overhaul.\n- Acceptance criteria: 1) Lighthouse >= 90 2) all pages ported 3) sponsor sign-off\n"
                     "- Fixed constraint: time\n- Estimate: best 35d / likely 42d / worst 60d; buffer 20% (declared)\n- Sponsor / sign-off: Avarile\n\n"
                     "## Risk Register\n| Risk | Likelihood | Impact | Owner | Mitigation | Status |\n|---|---|---|---|---|---|\n"
                     "| CMS API instability | Medium | High | Avarile |  | open |\n| Content not ready | High | Medium | Avarile | Weekly content check-in | open |\n\n"
                     "## Status Log\n### " + d(-16) + " · 🟢 GREEN\nKickoff done, design in progress.\n\n" + MARK + "\n"})
    m["projects"].append(wr)
    save()
    sh("scaffold.py", "build", "--start", d(-21), "--days", 42, "--project-id", wr, "--create", "--yes",
       "--assign", "PLAN=" + ME, "--assign", "DO=" + DEV, "--assign", "CHECK=" + ME)
    s = step_ids(wr)
    done = [s[i] for i in range(1, 7)]
    sh("write.py", "bulk-update", R.TASKS, "--ids", *done, "--set", "%s=finished_validating" % R.TF["prog"],
       "--set", "fldj3Xb1g9nUX4iFqE0=%s" % d(-21), "--set", "fldn95wbkTqefn18WdO=%s" % d(-9), "--yes")
    sh("write.py", "bulk-update", R.TASKS, "--ids", s[7], "--set", "%s=in-progress" % R.TF["prog"], "--set", "fldj3Xb1g9nUX4iFqE0=%s" % d(-5), "--yes")
    sh("assign.py", "set", "--to", "none", "--ids", s[9], s[10], "--reassign", "--yes")  # claimable DO work

    # ---- k3s Migration: preparing, no lead, PLAN held by Anastasia, rest unassigned
    k3 = post(R.PROJECTS, {R.PF["title"]: "k3s Migration", R.PF["prog"]: "preparing", R.PF["goal"]: {"id": m["goal"]},
        R.PF["ctx"]: "Moves: KR1\nRepo: /work/k3s-migration\nShape: migration\n\n## Charter\n- Scope: Move staging workloads from docker-compose to k3s in three waves.\n"
                     "- Out of scope: Production cutover.\n- Fixed constraint: scope\n- Estimate: best 30d / likely 42d / worst 60d; buffer 25% (declared)\n\n" + MARK + "\n"})
    m["projects"].append(k3)
    save()
    sh("scaffold.py", "migration", "--start", d(3), "--days", 56, "--buffer", 0.25, "--project-id", k3, "--create", "--yes", "--assign", "PLAN=" + ANA)

    # ---- Inbox with an old capture
    ib = post(R.PROJECTS, {R.PF["title"]: "Inbox", R.PF["prog"]: "in-progress", R.PF["ctx"]: "Unsorted captures.\n\n" + MARK + "\n"})
    m["projects"].append(ib)
    save()
    T.call("POST", "/api/table/%s/record" % R.TASKS, body={"fieldKeyType": "id", "records": [{"fields": {
        R.TF["title"]: "Renew the domain name", R.TF["ctx"]: "Due: %s\n" % d(5), R.TF["proj"]: {"id": ib}, R.TF["prio"]: "important"}}]})
    print("fixture created:", json.dumps(m))


def drop():
    if not MANIFEST.exists():
        sys.exit("no manifest; nothing to drop")
    m = json.loads(MANIFEST.read_text())
    n_t = 0
    for pid in m["projects"]:
        ctx = T.get_record(R.PROJECTS, pid, [R.PF["ctx"]])["fields"].get(R.PF["ctx"], "")
        if MARK not in ctx:
            sys.exit("refusing: project %s lacks the %s marker" % (pid, MARK))
        tasks = T.get_records(R.TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], pid)]), [])
        if tasks:
            T.delete_records(R.TASKS, [t["id"] for t in tasks])
            n_t += len(tasks)
        T.delete_records(R.PROJECTS, [pid])
    gctx = T.get_record(R.GOALS, m["goal"], [R.GF["ctx"]])["fields"].get(R.GF["ctx"], "")
    if MARK in gctx:
        T.delete_records(R.GOALS, [m["goal"]])
    MANIFEST.unlink()
    print("fixture dropped: %d task(s), %d project(s), 1 goal" % (n_t, len(m["projects"])))


if __name__ == "__main__":
    {"create": create, "drop": drop}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
