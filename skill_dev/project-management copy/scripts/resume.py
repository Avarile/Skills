#!/usr/bin/env python3
"""Agent entry point (read-only): find the project for a working directory and print a start-of-session brief.

  resume.py [--path DIR] [--name TEXT] [--as CONTACT] [--json]     (--as, or env PM_AGENT_CONTACT, narrows the brief to
                            the tasks assigned to that contact and lists unassigned tasks the agent could claim)
  resume.py --hook          SessionStart hook mode: reads {"cwd": ...} on stdin, prints hook JSON only on a confident
                            match, otherwise prints nothing; never fails the session.

Matching against the project's `Repo:` line (comma-separated paths/URLs allowed), best score wins:
  3 = working dir equals/is inside a Repo path, or git origin URL equals a Repo URL
  2 = last path component of a Repo value equals the directory name
  1 = project title contains the directory name (weak: confirm with the user)
Exit codes: 0 match, 3 no match, 4 ambiguous (several projects tie).
"""
import argparse, datetime as dt, json, os, re, subprocess, sys
from pathlib import Path
import teable as T
import rollup as R

PRIO = {"urgent": 0, "important": 1, "prioritise": 2, "normal": 3, "can wait": 4}


def open_blockers(section_text):
    """Blockers are append-only lines `- DATE · <blocker> · owner · status open|cleared DATE`. A line is resolved if it says
    cleared, or if a later cleared line's blocker text matches it (one text contains the other, case-insensitive)."""
    entries = []
    for l in section_text.splitlines():
        if not l.strip().startswith("-"):
            continue
        parts = [x.strip() for x in l.strip().lstrip("- ").split(" · ")]
        key = (parts[1] if len(parts) > 1 else parts[0]).lower()
        entries.append((l.strip("- ").strip(), key, "cleared" in l.lower()))
    out = []
    for i, (text, key, cleared) in enumerate(entries):
        if cleared:
            continue
        if any(c and (k in key or key in k) for _, k, c in entries[i + 1:]):
            continue
        out.append(text)
    return out


def norm_url(u):
    u = u.strip().lower().rstrip("/")
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"^(https?://|ssh://)?(git@)?", "", u).replace(":", "/", 1) if "@" in u or "://" in u else u
    return u


def git_origin(path):
    try:
        out = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"], capture_output=True, text=True, timeout=5)
        return norm_url(out.stdout) if out.returncode == 0 and out.stdout.strip() else None
    except Exception:
        return None


def score(project, path, origin, name):
    ctx = project["fields"].get(R.PF["ctx"]) or ""
    best, how = 0, None
    for line in re.findall(r"^Repo:\s*(.+)$", ctx, re.M):
        for v in [x.strip() for x in line.split(",") if x.strip()]:
            if v.startswith(("/", "~")):
                vp = Path(os.path.expanduser(v)).resolve()
                if path == vp or vp in path.parents:
                    best, how = max(best, 3), ("path" if best < 3 else how)
                elif vp.name.lower() == name.lower():
                    best, how = (2, "name") if best < 2 else (best, how)
            else:
                if origin and norm_url(v) == origin:
                    best, how = 3, "url"
                elif norm_url(v).split("/")[-1] == name.lower():
                    best, how = (2, "name") if best < 2 else (best, how)
    if best == 0 and name:
        t = re.sub(r"[-_ ]+", " ", (project["fields"].get(R.PF["title"]) or "").lower())
        if re.sub(r"[-_ ]+", " ", name.lower()) in t:
            best, how = 1, "title"
    return best, how


def charter_excerpt(ctx):
    sec = R.section(ctx, "## Charter")
    keep = [l.strip() for l in sec.splitlines() if re.match(r"-\s*(Scope|Out of scope|Acceptance criteria|Fixed constraint)", l.strip(), re.I)]
    return keep[:4]


def build(project, today, me=None):
    tasks = T.get_records(R.TASKS, T.and_filter(["%s is %s" % (R.TF["proj"], project["id"])]))
    gl = (project["fields"].get(R.PF["goal"]) or {}).get("id")
    dl = T.local_date(T.get_record(R.GOALS, gl, [R.GF["deadline"]])["fields"].get(R.GF["deadline"])) if gl else None
    roll = R.project_rollup(project, tasks, today, dl)
    ts = [R.parse_task(t, today) for t in tasks]
    ts = [t for t in ts if t["active"] and t["prog"] not in R.DONE_T and t["prog"] != "cancelled"]
    far = dt.date.max
    order = lambda t: (PRIO.get(t["prio"], 3), t["due"] or far, t["step"] or 0)
    unassigned = []
    if me:  # agent identity: my work first, plus unassigned work I could claim
        unassigned = sorted([t for t in ts if not t["who_id"] and t["prog"] != "in-progress"], key=order)
        ts = [t for t in ts if t["who_id"] == me[0]]
    nxt = sorted([t for t in ts if t["prog"] != "in-progress"], key=order)[:3]
    blockers = open_blockers(R.section(project["fields"].get(R.PF["ctx"]) or "", "## Blockers"))
    brief = dict(project=dict(id=project["id"], title=roll["title"], progress=roll["progress"], rag=roll["rag"], rules=roll["rules"]),
                 charter=charter_excerpt(project["fields"].get(R.PF["ctx"]) or ""),
                 in_progress=[dict(id=t["id"], title=t["title"], due=t["due"].isoformat() if t["due"] else None) for t in ts if t["prog"] == "in-progress"],
                 next=[dict(id=t["id"], title=t["title"], prio=t["prio"], due=t["due"].isoformat() if t["due"] else None, gate=t["gate"]) for t in nxt],
                 blockers=blockers, next_gate=roll["next_gate"], overdue=len(roll["overdue"]), as_contact=me[1] if me else None,
                 claimable=[dict(id=t["id"], title=t["title"], prio=t["prio"], due=t["due"].isoformat() if t["due"] else None, gate=t["gate"]) for t in unassigned[:3]],
                 claimable_count=len(unassigned))
    return brief


def render(b, how):
    p = b["project"]
    out = ["PROJECT %s (%s) · %s · RAG %s%s · match: %s" % (p["title"], p["id"], p["progress"], R.EMOJI[p["rag"]], " (%s)" % "; ".join(p["rules"]) if p["rules"] else "", how)]
    out += ["  " + c for c in b["charter"]]
    if b.get("as_contact"):
        out.append("ACTING AS: %s (showing tasks assigned to them)" % b["as_contact"])
    out += ["IN PROGRESS: %s (%s)%s" % (t["title"], t["id"], " due " + t["due"] if t["due"] else "") for t in b["in_progress"]] or ["IN PROGRESS: none"]
    out += ["NEXT: %s [%s]%s%s (%s)" % (t["title"], t["prio"], " due " + t["due"] if t["due"] else "", " GATE" if t["gate"] else "", t["id"]) for t in b["next"]]
    if b.get("as_contact"):
        out.append("UNASSIGNED, CLAIMABLE: %d%s" % (b["claimable_count"], "" if not b["claimable"] else " (top: %s)" % "; ".join("%s [%s]%s (%s)" % (t["title"], t["prio"], " GATE" if t["gate"] else "", t["id"]) for t in b["claimable"])))
    if b["next_gate"]:
        out.append("NEXT GATE: %s due %s" % (b["next_gate"]["title"], b["next_gate"]["due"]))
    out += ["BLOCKER: " + x for x in b["blockers"]]
    return "\n".join(out)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--path")
    a.add_argument("--name")
    a.add_argument("--json", action="store_true")
    a.add_argument("--hook", action="store_true")
    a.add_argument("--today")
    a.add_argument("--as", dest="as_contact", default=os.environ.get("PM_AGENT_CONTACT"),
                   help="contact name or id this agent acts as (default: env PM_AGENT_CONTACT); narrows tasks to theirs")
    args = a.parse_args()
    cwd = args.path
    if args.hook:
        try:  # never block a session start: read stdin only if data is ready within 1s
            import select
            if not sys.stdin.isatty() and select.select([sys.stdin], [], [], 1.0)[0]:
                cwd = json.loads(sys.stdin.read() or "{}").get("cwd") or cwd
        except Exception:
            pass
    path = Path(cwd or os.getcwd()).resolve()
    name = args.name or path.name
    today = dt.date.fromisoformat(args.today) if args.today else T.today()
    try:
        projects = [p for p in T.get_records(R.PROJECTS) if p["fields"].get(R.PF["active"])]
        origin = git_origin(path)
        scored = sorted(((score(p, path, origin, name), p) for p in projects), key=lambda x: -x[0][0])
        scored = [x for x in scored if x[0][0] > 0]
        if not scored:
            if args.hook:
                return
            print("NO MATCH for %s (name %r). Ask the user which project, or add a `Repo: %s` line to the project context." % (path, name, path))
            sys.exit(3)
        top = scored[0][0][0]
        tied = [x for x in scored if x[0][0] == top]
        if len(tied) > 1:
            if args.hook:
                return
            print("AMBIGUOUS (score %d): %s" % (top, "; ".join("%s (%s)" % (p["fields"].get(R.PF["title"]), p["id"]) for _, p in tied)))
            sys.exit(4)
        (sc, how), proj = scored[0]
        if args.hook and sc < 2:
            return
        me = T.resolve_contact(args.as_contact) if args.as_contact else None
        if me and me[0] is None:
            me = None
        brief = build(proj, today, me)
        brief["match"] = dict(score=sc, how=how, confident=sc >= 2)
        if args.hook:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext":
                  "project-management: this directory matches a tracked project.\n" + render(brief, how)}}))
        elif args.json:
            print(json.dumps(brief, ensure_ascii=False, indent=1))
        else:
            print(render(brief, how) + ("\n(weak match: confirm this is the right project before claiming tasks)" if sc < 2 else ""))
    except SystemExit:
        if args.hook:
            return
        raise


if __name__ == "__main__":
    main()
