#!/usr/bin/env python3
"""Day planning and execution tracking on daily_plans, day_blocks and routines. Writes are DRY-RUN unless --yes.

Read-only:
  day.py brief RANGE            everything plan-day needs: open days, frame per date, routines, ranked candidates
  day.py meetings RANGE --tasks recA recB ...    meeting block suggestions for the selected work (at most 2)
  day.py now                    the current block, the next one, unfinished earlier ones
  day.py review DATE            a day's outcomes, totals and carry-overs
  day.py time --from D --to D   planned vs actual minutes by kind (for reports)
  day.py check                  data-quality audit of the day tables, report-only

Writes:
  day.py apply --input plan.json [--allow-over] [--yes]    validate, place, stamp routines, preview; write with --yes
  day.py start (BLOCK | --task REC | --title TEXT) [--kind K] [--yes]
  day.py finish BLOCK --status done|partial|skipped [--minutes N] [--reason T]
                [--task-progress P --evidence T] [--yes]
  day.py replan BLOCK --reason T [--date D] [--start HH:MM] [--minutes N] [--drop] [--edit] [--yes]
  day.py review DATE (--all-as-planned | --leave-unknown | --outcomes FILE) [--text T | --text-file F] [--yes]
  day.py routine list | add | set REC | pause REC | resume REC     (see --help)

RANGE: today | tomorrow | this-week | next-week | next-N-days | YYYY-MM-DD | YYYY-MM-DD..YYYY-MM-DD
Add --json for machine output and --at YYYY-MM-DDTHH:MM to evaluate at another Melbourne time (tests, previews).
Every applied write is read back and verified; exit code 1 on a mismatch, 2 when a plan is refused.

apply input:
  {"days": [{"date": "2026-11-04", "capacity": 600, "focus": "...", "focus_goal": "rec...", "window": "09:00-17:45",
             "context": "why this plan", "deferred": ["..."],
             "declined_meetings": [{"project": "rec...", "signal": "alignment", "reason": "..."}],
             "blocks": [{"title": "...", "task": "rec...", "kind": "deep-work", "minutes": 90, "start": "10:00",
                         "notes": "With: ...", "key": "m1", "before": "m1", "after": "m1"}]}]}
  start is optional (placed automatically). `before` puts a block directly before the block with that key, `after` after it.
"""
import argparse, calendar, datetime as dt, json, math, os, re, sys
import teable as T
import rollup as R
import resume as RS
import write as W

# Defaults (keep in sync with references/day-planning.md)
BUFFER, MAX_BLOCK, MIN_BLOCK = 0.20, 120, 30
DEFAULT_WINDOW = "09:00-17:45"
ALIGN_TASKS, ALIGN_MINUTES, ALIGN_LOOKBACK_DAYS, DECLINE_DAYS, MAX_MEETINGS = 4, 360, 14, 7, 2
UNCLEAR_MINUTES = 120
PLUS_ONE = os.environ.get("PM_PLUS_ONE", "Aaron Sansoni")
PRIO = {"urgent": 0, "important": 1, "prioritise": 2, "normal": 3, "can wait": 4}
KINDS = ("deep-work", "review-agent-output", "meeting", "admin", "learning", "personal", "rest", "prepare")
BLOCK_STATUS = ("planned", "done", "partial", "skipped", "moved")
OPEN_PROGRESS = ("backlog", "in-progress")
DEAD_PROJECT = ("onhold", "cancelled", "finalized")
PLACEHOLDER = re.compile(r"details to be completed|\bTBD\b|\bTBC\b|to be confirmed|to be decided|give me some suggestion", re.I)
DOW = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


# --- pure helpers (no database; covered by evals/test_day.py) ---------------------------------------------------------
def hm(text):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", (text or "").strip())
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        return None
    return int(m[1]) * 60 + int(m[2])


def fmt(minute):
    return "%02d:%02d" % (minute // 60, minute % 60)


def ceil5(minute):
    return minute + (-minute % 5)


def parse_range(text, today):
    """RANGE -> list of dates. Week ranges hold Mon-Fri; the caller adds a weekend day when a routine falls on it."""
    t = text.strip().lower()
    if t == "today":
        return [today]
    if t == "tomorrow":
        return [today + dt.timedelta(days=1)]
    if t in ("this-week", "next-week"):
        mon = today - dt.timedelta(days=today.weekday()) + dt.timedelta(days=7 if t == "next-week" else 0)
        days = [mon + dt.timedelta(days=i) for i in range(7)]
        return [d for d in days if d >= today]
    m = re.fullmatch(r"next-(\d+)-days", t)
    if m:
        return [today + dt.timedelta(days=i + 1) for i in range(int(m[1]))]
    if ".." in t:
        a, b = [dt.date.fromisoformat(x) for x in t.split("..", 1)]
        return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]
    try:
        return [dt.date.fromisoformat(t)]
    except ValueError:
        sys.exit("bad RANGE %r; use today, tomorrow, this-week, next-week, next-N-days, a date or A..B" % text)


def falls_on(r, day):
    """Does routine dict r fall on this date? month_day -1 = last day of the month; a day past the month end clamps to it."""
    if not r.get("active"):
        return False
    if r.get("valid_from") and day < r["valid_from"]:
        return False
    if r.get("valid_until") and day > r["valid_until"]:
        return False
    freq, wd = r.get("freq"), r.get("weekdays") or []
    name = DOW[day.weekday()]
    if freq == "daily":
        return True
    if freq == "weekdays":
        return name in wd if wd else day.weekday() < 5
    if freq == "weekly":
        return name in wd
    if freq == "monthly":
        md = r.get("month_day")
        if md is None:
            return False
        last = calendar.monthrange(day.year, day.month)[1]
        want = last + 1 + md if md < 0 else min(md, last)
        return day.day == want
    return False


def subtract(window, busy):
    """Free intervals of (start, end) after removing busy intervals."""
    gaps, cur = [], window[0]
    for s, e in sorted(busy):
        if e <= cur:
            continue
        if s >= window[1]:
            break
        if s > cur:
            gaps.append((cur, min(s, window[1])))
        cur = max(cur, e)
    if cur < window[1]:
        gaps.append((cur, window[1]))
    return gaps


def overlapping(items):
    """Pairs of items (dicts with s and e, in minutes) whose times overlap."""
    out, ordered = [], sorted(items, key=lambda x: x["s"])
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if b["s"] >= a["e"]:
                break
            out.append((a, b))
    return out


def frame(window, busy, capacity, buffer=BUFFER):
    """Time available in a window. Capacity caps it: free = min(open gaps, capacity - everything already committed)."""
    gaps = subtract(window, busy)
    open_minutes = sum(e - s for s, e in gaps)
    committed = sum(e - s for s, e in busy)
    free = open_minutes if capacity is None else max(0, min(open_minutes, capacity - committed))
    return dict(gaps=gaps, free=free, plannable=int(math.floor(free * (1 - buffer))), committed=committed)


def totals(blocks):
    """Day totals. A moved block was replaced, so counting it would double-count; adhoc blocks have no plan; inactive never count."""
    live = [b for b in blocks if b["active"]]
    planned = sum(b["minutes"] or 0 for b in live if b["status"] != "moved" and b["source"] != "adhoc")
    actual = sum(b["actual_minutes"] or 0 for b in live)
    return dict(planned=planned, actual=actual, unplanned=sum(b["actual_minutes"] or 0 for b in live if b["source"] == "adhoc"))


def take(gaps, s, e):
    out = []
    for a, b in gaps:
        if e <= a or s >= b:
            out.append((a, b))
            continue
        if a < s:
            out.append((a, s))
        if e < b:
            out.append((e, b))
    return out


def place(items, gaps):
    """Assign start times. Fixed first, then `before`, then deep work into the longest stretch, then the rest earliest-first.
    Returns (placed, errors, warnings). A block longer than MAX_BLOCK, or one that no single gap can hold, is split."""
    placed, errors, warnings, spans = [], [], [], {}
    def add(it, s, minutes, part=None):
        placed.append(dict(it, s=s, e=s + minutes, minutes=minutes, part=part))
        if it.get("key") and it["key"] not in spans:
            spans[it["key"]] = (s, s + minutes)
    for it in [i for i in items if i.get("start")]:
        s = hm(it["start"])
        if s is None:
            errors.append("%s: bad start %r" % (it["title"], it["start"]))
            continue
        add(it, s, it["minutes"])
        gaps = take(gaps, s, s + it["minutes"])
    for it in [i for i in items if i.get("before") and not i.get("start")]:
        target = spans.get(it["before"])
        if not target:
            errors.append("%s: `before` names unknown or unplaced block %r" % (it["title"], it["before"]))
            continue
        fits = [g for g in gaps if g[0] + it["minutes"] <= min(g[1], target[0])]
        if not fits:
            errors.append("%s: no %d free minutes before %s" % (it["title"], it["minutes"], it["before"]))
            continue
        end = min(max(fits, key=lambda g: g[1])[1], target[0])
        add(it, end - it["minutes"], it["minutes"])
        gaps = take(gaps, end - it["minutes"], end)
    rest = [i for i in items if not i.get("start") and not i.get("before")]
    rest.sort(key=lambda i: 0 if i.get("key") else 1 if i.get("kind") == "deep-work" else 2)  # stable: keeps the ranked order agreed with the user
    for it in rest:
        deep, left, parts, lo = it.get("kind") == "deep-work", it["minutes"], [], 0
        if it.get("after"):
            if it["after"] in spans:
                lo = spans[it["after"]][1]
            else:
                errors.append("%s: `after` names unknown block %r" % (it["title"], it["after"]))
        while left > 0:
            chunk = min(left, MAX_BLOCK) if deep else left
            usable = [(max(a, lo), b) for a, b in gaps if b > max(a, lo)]
            fit = [g for g in usable if g[1] - g[0] >= chunk]
            if fit:
                g = max(fit, key=lambda x: (x[1] - x[0], -x[0])) if deep else min(fit, key=lambda x: x[0])
            elif usable and max(g[1] - g[0] for g in usable) >= MIN_BLOCK:
                g = max(usable, key=lambda x: (x[1] - x[0], -x[0]))
                chunk = g[1] - g[0]
            elif lo:
                warnings.append("%s: no room after %s, placed before it" % (it["title"], it["after"]))
                lo = 0
                continue
            else:
                errors.append("%s: does not fit, %d of %d min unplaced" % (it["title"], left, it["minutes"]))
                break
            parts.append((g[0], chunk))
            gaps = take(gaps, g[0], g[0] + chunk)
            left -= chunk
        for n, (s, m) in enumerate(parts, 1):
            add(it, s, m, "%d/%d" % (n, len(parts)) if len(parts) > 1 else None)
    return sorted(placed, key=lambda p: p["s"]), errors, warnings


def est_minutes(ctx):
    m = re.search(r"^Est:\s*(\d+(?:\.\d+)?)\s*(d|h|m|min)\b", ctx or "", re.M | re.I)
    if not m:
        return None
    return int(float(m[1]) * {"d": 480, "h": 60, "m": 1, "min": 1}[m[2].lower()])


def short_title(title):
    t = re.sub(r"^Step\s+\d+\s*\[\w+\]\s*", "", title or "")
    t = re.sub(r"^[^-]{2,30}\s---\s*", "", t)
    return t[:60].rstrip()


# --- database model ---------------------------------------------------------------------------------------------------
def parse_block(r):
    f, B = r["fields"], T.BLOCK
    start, actual = T.local_dt(f.get(B["start"])), T.local_dt(f.get(B["actual_start"]))
    link = lambda k: (f.get(B[k]) or {})
    return dict(id=r["id"], title=f.get(B["title"]) or "", day_id=link("day").get("id"), task_id=link("task").get("id"),
                task_title=link("task").get("title"), kind=f.get(B["kind"]), status=f.get(B["status"]) or "planned",
                order=f.get(B["order"]), start=start, minutes=f.get(B["minutes"]), actual_start=actual,
                actual_minutes=f.get(B["actual_minutes"]), reason=f.get(B["reason"]), notes=f.get(B["notes"]),
                active=f.get(B["active"]) is True, source=f.get(B["source"]) or "plan", routine_id=link("routine").get("id"),
                replaces_id=link("replaces").get("id"))


def parse_routine(r):
    f, Q = r["fields"], T.ROUTINE
    return dict(id=r["id"], title=f.get(Q["title"]) or "", kind=f.get(Q["kind"]), freq=f.get(Q["freq"]), weekdays=f.get(Q["weekdays"]) or [],
                month_day=f.get(Q["month_day"]), start=hm(f.get(Q["start"])), start_text=f.get(Q["start"]), minutes=f.get(Q["minutes"]) or 0,
                valid_from=T.local_date(f.get(Q["valid_from"])), valid_until=T.local_date(f.get(Q["valid_until"])),
                active=f.get(Q["active"]) is True, notes=f.get(Q["notes"]), task_id=(f.get(Q["task"]) or {}).get("id"))


def parse_plan(r):
    f, P = r["fields"], T.PLAN
    return dict(id=r["id"], date=T.local_date(f.get(P["date"])), status=f.get(P["status"]) or "planned", capacity=f.get(P["capacity"]),
                focus=f.get(P["focus"]), goal=f.get(P["goal"]), ctx=f.get(P["ctx"]) or "", review=f.get(P["review"]) or "",
                active=f.get(P["active"]) is True)


class World:
    """Read fresh, cache for one command. Everything is filtered client-side so the rules stay in one place."""

    def __init__(self, at=None):
        self.now = at or T.now()
        self.today = self.now.date()
        self.minute = self.now.hour * 60 + self.now.minute
        self._c = {}

    def _get(self, key, fn):
        if key not in self._c:
            self._c[key] = fn()
        return self._c[key]

    @property
    def plans(self):
        return self._get("plans", lambda: [p for p in map(parse_plan, T.get_records(T.PLANS, take=100000)) if p["active"]])

    @property
    def blocks(self):
        return self._get("blocks", lambda: [b for b in map(parse_block, T.get_records(T.BLOCKS, take=100000)) if b["active"]])

    @property
    def routines(self):
        return self._get("routines", lambda: list(map(parse_routine, T.get_records(T.ROUTINES, take=1000))))

    @property
    def contacts(self):
        def load():
            rows = T.get_records(T.CONTACTS, projection=[T.CONTACT_TITLE, T.CONTACT_TYPE])
            return {r["id"]: dict(id=r["id"], name=r["fields"].get(T.CONTACT_TITLE) or "", type=(r["fields"].get(T.CONTACT_TYPE) or {}).get("title")) for r in rows}
        return self._get("contacts", load)

    @property
    def me(self):
        def find():
            want = os.environ.get("PM_ME_CONTACT")
            mine = [c for c in self.contacts.values() if (c["name"] == want if want else c["type"] == "self")]
            return mine[0] if len(mine) == 1 else None
        return self._get("me", find)

    def is_agent(self, cid):
        return (self.contacts.get(cid) or {}).get("type") == "Agentic Mind"

    def is_me(self, cid):
        return bool(self.me and cid == self.me["id"])

    @property
    def task_rows(self):
        F = [R.TF["title"], R.TF["ctx"], R.TF["prog"], R.TF["prio"], R.TF["proj"], R.TF["who"], R.TF["active"], R.TF["created"], T.TASK_X["collab"]]
        return self._get("task_rows", lambda: T.get_records(R.TASKS, projection=F, take=100000))

    @property
    def tasks(self):
        def load():
            out = {}
            for r in self.task_rows:
                t = R.parse_task(r, self.today)
                f = r["fields"]
                t.update(ctx=f.get(R.TF["ctx"]) or "", proj_id=(f.get(R.TF["proj"]) or {}).get("id"), proj_title=(f.get(R.TF["proj"]) or {}).get("title"),
                         collab=[c["id"] for c in f.get(T.TASK_X["collab"]) or []])
                t["acceptance"] = bool(re.search(r"^Acceptance:", t["ctx"], re.M))
                out[t["id"]] = t
            return out
        return self._get("tasks", load)

    @property
    def projects(self):
        F = [R.PF["title"], R.PF["ctx"], R.PF["prog"], R.PF["goal"], R.PF["lead"], R.PF["active"], R.PF["updated"]]
        return self._get("projects", lambda: {r["id"]: r for r in T.get_records(R.PROJECTS, projection=F, take=10000)})

    def rag(self, pid):
        cache = self._get("rag", dict)
        if pid not in cache:
            rows = [r for r in self.task_rows if (r["fields"].get(R.TF["proj"]) or {}).get("id") == pid]
            cache[pid] = R.project_rollup(self.projects[pid], rows, self.today) if pid in self.projects else None
        return cache[pid]

    def plan_on(self, day):
        hits = [p for p in self.plans if p["date"] == day]
        return hits[0] if hits else None

    def blocks_of(self, plan):
        rows = [b for b in self.blocks if plan and b["day_id"] == plan["id"]]
        return sorted(rows, key=lambda b: (b["start"] or T.local_dt("9999-01-01T00:00:00Z"), b["order"] or 0))

    def routines_on(self, day):
        return [r for r in self.routines if falls_on(r, day)]

    def default_capacity(self):
        rows = sorted([p for p in self.plans if p["capacity"]], key=lambda p: p["date"] or dt.date.min)
        return rows[-1]["capacity"] if rows else None

    def window(self):
        """Working window: earliest start to latest end of the weekday routines, else the default."""
        rs = [r for r in self.routines if r["active"] and r["start"] is not None and r["freq"] in ("daily", "weekdays")]
        if not rs:
            return tuple(map(hm, DEFAULT_WINDOW.split("-")))
        return min(r["start"] for r in rs), max(r["start"] + r["minutes"] for r in rs)


def block_span(b):
    if not b["start"] or not b["minutes"]:
        return None
    s = b["start"].hour * 60 + b["start"].minute
    return (s, s + b["minutes"])


def holds_time(b):
    return b["status"] in ("planned", "done", "partial")


def day_frame(w, day, capacity=None, window=None):
    """Frame for one date: routines still to stamp, clashes between them, and the time available."""
    plan = w.plan_on(day)
    existing = w.blocks_of(plan)
    stamped = {b["routine_id"] for b in existing if b["routine_id"]}
    due = [r for r in w.routines_on(day)]
    to_stamp = [r for r in due if r["id"] not in stamped]
    win = window or w.window()
    busy = [block_span(b) for b in existing if holds_time(b) and block_span(b)]
    busy += [(r["start"], r["start"] + r["minutes"]) for r in to_stamp if r["start"] is not None]
    if day == w.today:
        win = (max(win[0], ceil5(w.minute)), win[1])
        busy = [(max(s, win[0]), e) for s, e in busy if e > win[0]]
    cap = capacity if capacity is not None else (plan["capacity"] if plan and plan["capacity"] else w.default_capacity())
    fr = frame(win, busy, cap) if win[0] < win[1] else dict(gaps=[], free=0, plannable=0, committed=0)
    flags = []
    if day.weekday() >= 5:
        flags += ["%s falls on %s" % (r["title"], DOW[day.weekday()]) for r in due if r["freq"] == "monthly"]
    timed = [dict(s=r["start"], e=r["start"] + r["minutes"], title=r["title"]) for r in due if r["start"] is not None]
    flags += ["%s overlaps %s" % (a["title"], b["title"]) for a, b in overlapping(timed)]
    flags += ["routine %s has no valid start_time" % r["title"] for r in due if r["start"] is None]
    return dict(date=day.isoformat(), weekday=DOW[day.weekday()], plan_id=plan["id"] if plan else None, plan_status=plan["status"] if plan else None,
                capacity=cap, window=[fmt(win[0]), fmt(win[1])] if win[0] < win[1] else None, routines=[dict(id=r["id"], title=r["title"], start=r["start_text"], minutes=r["minutes"], stamped=r["id"] in stamped) for r in due],
                existing_blocks=len(existing), free=fr["free"], plannable=fr["plannable"], gaps=[[fmt(a), fmt(b)] for a, b in fr["gaps"]], flags=flags)


def range_days(w, text):
    """Week ranges keep Mon-Fri plus any weekend day a routine falls on, so nothing is missed and nothing moves silently."""
    days = parse_range(text, w.today)
    if text.strip().lower() in ("this-week", "next-week"):
        days = [d for d in days if d.weekday() < 5 or w.routines_on(d)]
    return days


def open_days(w):
    """Past days never closed. These come first in plan-day."""
    out = []
    for p in sorted(w.plans, key=lambda p: p["date"] or dt.date.min, reverse=True):
        if not p["date"] or p["date"] >= w.today or p["status"] == "reviewed":
            continue
        bs = w.blocks_of(p)
        unknown = [b for b in bs if b["status"] == "planned"]
        open_tasks = sorted({b["task_id"] for b in unknown if b["task_id"] and b["task_id"] in w.tasks and w.tasks[b["task_id"]]["prog"] in OPEN_PROGRESS + ("finished_reviewing",)})
        likely = [b["id"] for b in unknown if b["task_id"] in w.tasks and w.tasks[b["task_id"]]["prog"] in ("finished_validating", "closed")]
        out.append(dict(plan_id=p["id"], date=p["date"].isoformat(), status=p["status"], blocks=len(bs), no_outcome=len(unknown), open_tasks=open_tasks, likely_done=likely))
    return out


def successors(w):
    return {b["replaces_id"] for b in w.blocks if b["replaces_id"]}


def candidates(w, days, focus_goal=None):
    """Rank the work to plan. Order: carry-overs and in-progress, then reviews waiting, then due in range, then the rest;
    inside a tier priority first, then due date, focus goal, unhealthy projects, oldest."""
    last, replaced = days[-1], successors(w)
    future = {b["task_id"] for b in w.blocks if b["task_id"] and b["status"] == "planned" and b["start"] and b["start"].date() >= w.today}
    carry = set()
    for b in w.blocks:
        if not b["task_id"] or b["task_id"] in future:
            continue
        past = bool(b["start"]) and b["start"].date() < w.today
        if b["status"] == "partial" or (b["status"] == "moved" and b["id"] not in replaced) or (b["status"] == "planned" and past):
            carry.add(b["task_id"])
    spent = {}
    for b in w.blocks:
        if b["task_id"] and b["actual_minutes"]:
            spent[b["task_id"]] = spent.get(b["task_id"], 0) + b["actual_minutes"]
    siblings = {}
    for t in w.tasks.values():
        if t["active"]:
            siblings.setdefault(t["proj_id"], []).append(t)
    out, skipped = [], dict(on_hold=0, delegated=0, someone_else=0, blocked=0, already_planned=0, project_paused=0)
    for t in w.tasks.values():
        if not t["active"] or t["prog"] in ("cancelled", "closed", "finished_validating"):
            continue
        project = w.projects.get(t["proj_id"])
        pprog = project["fields"].get(R.PF["prog"]) if project else None
        if project and (project["fields"].get(R.PF["active"]) is not True or pprog in DEAD_PROJECT):
            skipped["project_paused"] += 1
            continue
        if t["prog"] == "onhold":
            skipped["on_hold"] += 1
            continue
        who, review = t["who_id"], t["prog"] == "finished_reviewing"
        agent = w.is_agent(who)
        if who and not agent and not w.is_me(who):
            skipped["someone_else"] += 1
            continue
        if agent and not review:
            skipped["delegated"] += 1
            continue
        if t["id"] in future:
            skipped["already_planned"] += 1
            continue
        if not review and blocked_by(t, siblings.get(t["proj_id"], [])):
            skipped["blocked"] += 1
            continue
        due_in = bool(t["due"] and t["due"] <= last)
        if t["id"] in carry or t["prog"] == "in-progress":
            tier, why = 0, ("carried over, waiting on your review" if review else "carried over") if t["id"] in carry else "already in progress"
        elif review:
            tier, why = 1, "agent output to review" if agent else "waiting on your review"
        elif due_in:
            tier, why = 2, "overdue" if t["due"] < w.today else "due %s" % t["due"]
        else:
            tier, why = 3, "backlog"
        est = est_minutes(t["ctx"])
        default = 30 if review and agent else 60 if review else 90
        minutes = max(MIN_BLOCK, est - spent.get(t["id"], 0)) if est else default
        goal = (project["fields"].get(R.PF["goal"]) or {}).get("id") if project else None
        rag = (w.rag(t["proj_id"]) or {}).get("rag") if t["proj_id"] else None
        out.append(dict(id=t["id"], title=t["title"], block_title=short_title(t["title"]), project=t["proj_title"], project_id=t["proj_id"], prio=t["prio"],
                        due=t["due"].isoformat() if t["due"] else None, tier=tier, why=why, kind="review-agent-output" if review and agent else "deep-work",
                        minutes=minutes, minutes_from="Est" if est else "default", assignee=t["who_name"], rag=rag,
                        _k=(tier, PRIO.get(t["prio"], 3), t["due"] or dt.date.max, 0 if focus_goal and goal == focus_goal else 1,
                            0 if rag in ("RED", "AMBER") else 1, t["created"] or dt.date.max)))
    out.sort(key=lambda c: c["_k"])
    for c in out:
        c.pop("_k")
    return out, skipped


def blocked_by(t, sibs):
    """An unfinished earlier gate, or a `Depends: Step NN` sibling still open."""
    done = R.DONE_T | {"cancelled"}
    if t["step"] is not None and any(s["gate"] and s["step"] is not None and s["step"] < t["step"] and s["prog"] not in done for s in sibs):
        return True
    m = re.search(r"^Depends:\s*(.+)$", t["ctx"], re.M)
    if m:
        need = {int(x) for x in re.findall(r"Step\s+(\d+)", m[1])}
        return any(s["step"] in need and s["prog"] not in done for s in sibs)
    return False


# --- meetings ---------------------------------------------------------------------------------------------------------
def meeting_target(w, project, tasks):
    """Who to meet, in order: Charter sponsor, a lead who isn't me, human collaborators, then the +1."""
    ctx = project["fields"].get(R.PF["ctx"]) or "" if project else ""
    m = re.search(r"^- Sponsor(?:\s*/\s*sign-off)?:\s*(.+)$", ctx, re.M)
    names = {c["name"].lower() for c in ([w.me] if w.me else [])}
    if m and m[1].strip() not in ("", "...") and m[1].strip().lower() not in names:
        return m[1].strip(), "Charter sponsor"
    lead = (project["fields"].get(R.PF["lead"]) or {}).get("id") if project else None
    if lead and not w.is_me(lead) and not w.is_agent(lead):
        return T.contact_name(lead), "project lead"
    humans = [c for t in tasks for c in t["collab"] if not w.is_me(c) and not w.is_agent(c) and c in w.contacts]
    if humans:
        return w.contacts[humans[0]]["name"], "collaborator"
    return PLUS_ONE, "your +1"


def declined_recently(w):
    """{(project id, signal)} declined in the last DECLINE_DAYS days, read back from plan context."""
    out = set()
    for p in w.plans:
        sec = R.section(p["ctx"], "## Meetings declined")
        for d, pid, sig in re.findall(r"^- (\d{4}-\d{2}-\d{2}) · (rec\w+) · ([\w-]+)", sec, re.M):
            if (w.today - dt.date.fromisoformat(d)).days <= DECLINE_DAYS:
                out.add((pid, sig))
    return out


def meetings(w, days, task_ids, minutes_by_task=None):
    """Meeting block suggestions for the selected work. Only ever a time block: nothing is sent or drafted."""
    minutes_by_task = minutes_by_task or {}
    picked = [w.tasks[i] for i in dict.fromkeys(task_ids) if i in w.tasks]
    in_range = {b["task_id"]: b["minutes"] or 0 for b in w.blocks if b["task_id"] and b["status"] == "planned" and b["kind"] == "deep-work" and b["start"] and b["start"].date() in days}
    for i in in_range:
        if i in w.tasks and w.tasks[i] not in picked:
            picked.append(w.tasks[i])
    groups, proposals, declined = {}, [], declined_recently(w)
    for t in picked:
        groups.setdefault(t["proj_id"], []).append(t)
    since = w.today - dt.timedelta(days=ALIGN_LOOKBACK_DAYS)
    met = {w.tasks[b["task_id"]]["proj_id"] for b in w.blocks if b["kind"] == "meeting" and b["task_id"] in w.tasks and b["start"] and b["start"].date() >= since and b["status"] in ("planned", "done", "partial")}
    def minutes(t):
        return minutes_by_task.get(t["id"]) or in_range.get(t["id"]) or est_minutes(t["ctx"]) or 90
    def add(rank, signal, pid, tasks, reason, agenda, who=None, source=None):
        if (pid, signal) in declined:
            return
        project = w.projects.get(pid)
        if not who:
            who, source = meeting_target(w, project, tasks)
        proposals.append(dict(rank=rank, signal=signal, project=(project["fields"].get(R.PF["title"]) if project else None), project_id=pid, attendee=who, attendee_source=source,
                              reason=reason, minutes=30, prepare_minutes=15, kind="meeting", link_task=tasks[0]["id"], before_tasks=[t["id"] for t in tasks], agenda=agenda))
    for pid, ts in groups.items():
        project = w.projects.get(pid)
        impl = [t for t in ts if t["phase"] not in ("PLAN", "CHECK", "ACT") and t["prog"] != "finished_reviewing" and not w.is_agent(t["who_id"])]
        total = sum(minutes(t) for t in impl)
        name = project["fields"].get(R.PF["title"]) if project else "no project"
        rag = w.rag(pid) if pid else None
        ctx = project["fields"].get(R.PF["ctx"]) or "" if project else ""
        if rag and rag["rag"] == "RED":
            add(0, "escalation", pid, ts, "%s is RED: %s" % (name, "; ".join(rag["rules"])[:120]), ["What is off track", "Options and their cost", "Decision needed"])
        recent = [l for l in R.section(ctx, "## Change Log").splitlines() if re.match(r"\s*-\s*(\d{4}-\d{2}-\d{2})", l)
                  and (w.today - dt.date.fromisoformat(re.match(r"\s*-\s*(\d{4}-\d{2}-\d{2})", l)[1])).days <= 7
                  and any(int(x) > 5 for x in re.findall(r"(\d+)\s*%", l))]
        if recent:
            add(0, "escalation", pid, ts, "A change over 5% impact was logged in %s this week" % name, ["The change and its impact", "Approve or reject", "Re-baseline if approved"])
        gated = [t for t in ts if t["gate"]]
        signoff = [t for t in ts if t["prog"] == "finished_reviewing" and not w.is_agent(t["who_id"]) and not w.is_me(t["who_id"])]
        if gated or signoff:
            add(1, "signoff", pid, gated + signoff, "%s needs a sign-off before work can continue: %s" % (name, short_title((gated + signoff)[0]["title"])), ["What was delivered", "Acceptance check", "Sign-off or changes"])
        blockers = [b for b in RS.open_blockers(R.section(ctx, "## Blockers"))]
        others = [b.split(" · ")[2].strip() for b in blockers if len(b.split(" · ")) > 2 and b.split(" · ")[2].strip().lower() not in {(w.me or {}).get("name", "").lower(), "owner", ""}]
        people = [c for t in ts for c in t["collab"] if not w.is_me(c) and not w.is_agent(c) and c in w.contacts]
        if others:
            add(2, "dependency", pid, ts, "%s has an open blocker owned by %s" % (name, others[0]), ["Current state of the blocker", "What is needed and by when", "Fallback"], others[0], "blocker owner")
        elif people:
            who = w.contacts[people[0]]["name"]
            add(2, "dependency", pid, ts, "Planned %s work involves %s as a collaborator" % (name, who), ["What each side is doing", "Hand-off points", "Open questions"], who, "collaborator")
        if pid not in met and (len(impl) >= ALIGN_TASKS or total >= ALIGN_MINUTES):
            add(3, "alignment", pid, impl, "%d implementation tasks (%d min) planned in %s with no alignment meeting in %d days" % (len(impl), total, name, ALIGN_LOOKBACK_DAYS), ["Confirm the requirements and priorities", "Agree what done looks like", "Surface risks before building"])
        unclear = [t for t in impl if PLACEHOLDER.search(t["ctx"]) or (not t["acceptance"] and minutes(t) >= UNCLEAR_MINUTES)]
        if unclear and pid not in met:
            place_holder = [t for t in unclear if PLACEHOLDER.search(t["ctx"])]
            add(4, "unclear", pid, unclear, "%d planned task(s) in %s have %s" % (len(unclear), name, "placeholder requirements" if place_holder else "no acceptance criteria"), ["Clarify what is wanted", "Set acceptance criteria", "Decide what to drop"])
    seen, out = set(), []
    for p in sorted(proposals, key=lambda p: p["rank"]):
        if p["project_id"] not in seen:
            seen.add(p["project_id"])
            out.append(p)
    return dict(proposals=out[:MAX_MEETINGS], held_back=max(0, len(out) - MAX_MEETINGS))


# --- plan building ----------------------------------------------------------------------------------------------------
def validate_kind(kind, title):
    if kind not in KINDS:
        sys.exit("invalid kind %r for %s; valid: %s (a wrong spelling would silently CLEAR the field)" % (kind, title, ", ".join(KINDS)))


def build_day(w, spec, allow_over=False):
    """Dry computation of one day's writes: the plan row, routine stamps, new blocks and the resulting timeline."""
    day = dt.date.fromisoformat(spec["date"])
    plan = w.plan_on(day)
    errors, warnings = [], []
    if plan and plan["status"] == "reviewed":
        errors.append("%s is already reviewed; a closed day cannot be replanned" % day)
    if day < w.today:
        errors.append("%s is in the past" % day)
    existing = w.blocks_of(plan)
    stamped = {b["routine_id"] for b in existing if b["routine_id"]}
    window = tuple(map(hm, spec["window"].split("-"))) if spec.get("window") else w.window()
    if None in window:
        sys.exit("bad window %r, use HH:MM-HH:MM" % spec["window"])
    fr0 = day_frame(w, day, spec.get("capacity"), window)
    warnings += fr0["flags"]
    stamps = []
    for r in w.routines_on(day):
        if r["id"] in stamped:
            continue
        stamps.append(dict(r=r, title=r["title"], kind=r["kind"], minutes=r["minutes"], s=r["start"], e=(r["start"] + r["minutes"]) if r["start"] is not None else None, task=r["task_id"], source="routine"))
    busy = [dict(s=block_span(b)[0], e=block_span(b)[1], title=b["title"]) for b in existing if holds_time(b) and block_span(b)]
    busy += [dict(s=x["s"], e=x["e"], title=x["title"]) for x in stamps if x["s"] is not None]
    win = window
    if day == w.today:
        win = (max(window[0], ceil5(w.minute)), window[1])
    gaps = subtract(win, [(b["s"], b["e"]) for b in busy]) if win[0] < win[1] else []
    items = []
    for b in spec.get("blocks", []):
        task = w.tasks.get(b.get("task")) if b.get("task") else None
        if b.get("task") and not task:
            errors.append("unknown task %s" % b["task"])
            continue
        title = b.get("title") or (short_title(task["title"]) if task else None)
        if not title:
            errors.append("a block needs a title or a task")
            continue
        kind = b.get("kind", "deep-work")
        validate_kind(kind, title)
        minutes = b.get("minutes")
        if not minutes or minutes <= 0:
            errors.append("%s: needs minutes" % title)
            continue
        if b.get("start") and hm(b["start"]) is not None:
            s = hm(b["start"])
            hit = [x["title"] for x in busy if s < x["e"] and x["s"] < s + minutes]
            if hit:
                errors.append("%s at %s overlaps %s" % (title, b["start"], ", ".join(hit)))
                continue
            if day == w.today and s < w.minute:
                errors.append("%s at %s is already in the past" % (title, b["start"]))
                continue
        if task and task["id"] in {x["task_id"] for x in existing if x["status"] == "planned" and x["title"] == title}:
            warnings.append("%s already has a planned block on this day; skipped" % title)
            continue
        items.append(dict(b, title=title, kind=kind, minutes=minutes))
    placed, perr, pwarn = place(items, gaps)
    errors += perr
    warnings += pwarn
    pairs = overlapping([p for p in placed])
    errors += ["%s overlaps %s" % (a["title"], b["title"]) for a, b in pairs]
    new_minutes = sum(p["minutes"] for p in placed)
    cap = spec.get("capacity") or fr0["capacity"]
    fr = frame(win, [(max(b["s"], win[0]), b["e"]) for b in busy if b["e"] > win[0]], cap) if win[0] < win[1] else dict(free=0, plannable=0)
    if new_minutes > fr["free"] and not allow_over:
        errors.append("over capacity: %d min planned, %d free. Choose what to drop." % (new_minutes, fr["free"]))
    elif new_minutes > fr["plannable"]:
        warnings.append("uses the buffer: %d min planned, %d plannable of %d free" % (new_minutes, fr["plannable"], fr["free"]))
    timeline = [dict(id=b["id"], s=block_span(b)[0], e=block_span(b)[1], title=b["title"], kind=b["kind"], tag="existing " + b["status"]) for b in existing if holds_time(b) and block_span(b)]
    timeline += [dict(id=None, s=x["s"], e=x["e"], title=x["title"], kind=x["kind"], tag="routine") for x in stamps if x["s"] is not None]
    timeline += [dict(id=None, s=p["s"], e=p["e"], title=p["title"] + (" (%s)" % p["part"] if p.get("part") else ""), kind=p["kind"], tag="new", notes=p.get("notes")) for p in placed]
    timeline.sort(key=lambda x: x["s"])
    return dict(date=day, spec=spec, plan=plan, stamps=stamps, placed=placed, errors=errors, warnings=warnings, timeline=timeline, existing=existing, capacity=cap,
                free=fr["free"], plannable=fr["plannable"], new_minutes=new_minutes)


def plan_context(d, existing_ctx=""):
    spec, text = d["spec"], existing_ctx or ""
    if spec.get("context"):
        text = W.append_section(text, "## Plan", spec["context"])
    if spec.get("deferred"):
        text = W.append_section(text, "## Deferred", "\n".join("- " + x for x in spec["deferred"]))
    if spec.get("declined_meetings"):
        lines = ["- %s · %s · %s · %s" % (d["today"], x["project"], x["signal"], x.get("reason", "")) for x in spec["declined_meetings"]]
        text = W.append_section(text, "## Meetings declined", "\n".join(lines))
    return text


def write_day(w, d):
    day, spec, plan = d["date"], d["spec"], d["plan"]
    P, B = T.PLAN, T.BLOCK
    d["today"] = w.today.isoformat()
    ctx = plan_context(d, plan["ctx"] if plan else "")
    fields = {}
    if spec.get("capacity") is not None:
        fields[P["capacity"]] = spec["capacity"]
    elif not plan and d["capacity"]:
        fields[P["capacity"]] = d["capacity"]
    if spec.get("focus"):
        fields[P["focus"]] = spec["focus"]
    if spec.get("focus_goal"):
        fields[P["goal"]] = {"id": spec["focus_goal"]}
    if ctx and ctx != (plan["ctx"] if plan else ""):
        fields[P["ctx"]] = ctx
    if plan:
        pid = plan["id"]
        if fields:
            T.update(T.PLANS, pid, fields)
    else:
        fields.update({P["date"]: day.isoformat(), P["status"]: "planned"})
        pid = T.create(T.PLANS, [fields])[0]["id"]
    rows = []
    def row(title, kind, s, minutes, source, task=None, routine=None, notes=None):
        f = {B["title"]: title, B["day"]: {"id": pid}, B["kind"]: kind, B["status"]: "planned", B["source"]: source}
        if s is not None:
            f[B["start"]] = T.utc_iso(day, s)
        if minutes:
            f[B["minutes"]] = minutes
        if task:
            f[B["task"]] = {"id": task}
        if routine:
            f[B["routine"]] = {"id": routine}
        if notes:
            f[B["notes"]] = notes
        return (s if s is not None else 10 ** 6, f)
    for x in d["stamps"]:
        rows.append(row(x["title"], x["kind"], x["s"], x["minutes"], "routine", x["task"], x["r"]["id"]))
    for p in d["placed"]:
        title = p["title"] + (" (%s)" % p["part"] if p.get("part") else "")
        rows.append(row(title, p["kind"], p["s"], p["minutes"], "plan", p.get("task"), None, p.get("notes")))
    combined = [(block_span(b)[0], b["id"], None) for b in d["existing"] if holds_time(b) and block_span(b)] + [(s, None, f) for s, f in rows]
    combined.sort(key=lambda x: x[0])
    for n, (_, bid, f) in enumerate(combined):
        if f is not None:
            f[B["order"]] = n
    created = T.create(T.BLOCKS, [f for _, f in rows]) if rows else []
    for n, (_, bid, f) in enumerate(combined):
        if bid and next(b for b in d["existing"] if b["id"] == bid)["order"] != n:
            T.update(T.BLOCKS, bid, {B["order"]: n})
    bad = 0
    for rec, (_, f) in zip(created, rows):
        got = T.get_record(T.BLOCKS, rec["id"])["fields"]
        if got.get(B["kind"]) != f[B["kind"]] or got.get(B["status"]) != "planned" or got.get(B["source"]) != f[B["source"]] or (f.get(B["start"]) and T.local_dt(got.get(B["start"])) != T.local_dt(f[B["start"]])):
            bad += 1
            print("VERIFY MISMATCH block", rec["id"], f[B["title"]])
    return pid, [r["id"] for r in created], bad


def render_day(d):
    out = ["%s %s · %d new min · %d free · %d plannable · capacity %s" % (d["date"], DOW[d["date"].weekday()], d["new_minutes"], d["free"], d["plannable"], d["capacity"])]
    for x in d["timeline"]:
        out.append("  %s-%s  %-20s %s [%s]%s" % (fmt(x["s"]), fmt(x["e"]), x["kind"], x["title"], x["tag"], "  " + x["notes"] if x.get("notes") else ""))
    out += ["  FLAG: " + x for x in d["warnings"]]
    out += ["  ERROR: " + x for x in d["errors"]]
    return out


def cmd_apply(a, w):
    spec = json.load(open(a.input))
    days = [build_day(w, s, a.allow_over) for s in spec["days"]]
    errors = [e for d in days for e in d["errors"]]
    if a.json:
        print(json.dumps([dict(date=d["date"].isoformat(), timeline=[dict(x, s=fmt(x["s"]), e=fmt(x["e"])) for x in d["timeline"]], flags=d["warnings"], errors=d["errors"], free=d["free"], plannable=d["plannable"], new_minutes=d["new_minutes"]) for d in days], ensure_ascii=False, indent=1))
    else:
        for d in days:
            print("\n".join(render_day(d)))
    if errors:
        print("REFUSED: %d error(s); nothing written." % len(errors))
        sys.exit(2)
    if not a.yes:
        print("DRY RUN: nothing written. Re-run with --yes to apply.")
        return
    bad = 0
    for d in days:
        pid, ids, b = write_day(w, d)
        bad += b
        print("wrote %s: plan %s, %d block(s) %s" % (d["date"], pid, len(ids), " ".join(ids)))
    print("verification %s" % ("FAILED (%d)" % bad if bad else "ok"))
    sys.exit(1 if bad else 0)


# --- verified single writes -------------------------------------------------------------------------------------------
def verified(table, rec, fields):
    """PATCH then read back. Selects validated up front: a wrong option silently clears the field."""
    W.validate_sets(table, fields)
    T.update(table, rec, fields)
    got = T.get_record(table, rec, list(fields))["fields"]
    for k, v in fields.items():
        have = got.get(k)
        if isinstance(v, dict):
            ok = (have or {}).get("id") == v["id"]
        elif v is None:
            ok = have in (None, "")
        elif isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2}T", v):
            ok = T.local_dt(have) == T.local_dt(v)
        elif isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            ok = T.local_date(have) == dt.date.fromisoformat(v)
        else:
            ok = have == v
        if not ok:
            sys.exit("VERIFY MISMATCH %s %s: %r != %r" % (rec, k, have, v))


def task_log(rec, line):
    field = R.TF["ctx"]
    before = T.get_record(R.TASKS, rec, [field])["fields"].get(field) or ""
    after = W.append_section(before, "## Log", line)
    if (T.get_record(R.TASKS, rec, [field])["fields"].get(field) or "") != before:
        sys.exit("ABORT: task context changed while logging; re-run")
    T.update(R.TASKS, rec, {field: after})


def run(actions, a):
    for desc, _ in actions:
        print(" -", desc)
    if not a.yes:
        print("DRY RUN: nothing written. Re-run with --yes to apply.")
        return False
    for _, fn in actions:
        fn()
    print("applied; verified")
    return True


def nowiso(w):
    return T.utc_iso(w.today, w.minute)


def get_block(ref):
    r = T.get_record(T.BLOCKS, ref)
    return parse_block(r)


def ensure_plan(w):
    """Today's plan row; unplanned work still needs a day to belong to."""
    p = w.plan_on(w.today)
    if p:
        return p
    rec = T.create(T.PLANS, [{T.PLAN["date"]: w.today.isoformat(), T.PLAN["status"]: "running"}])[0]
    return dict(id=rec["id"], status="running", date=w.today, ctx="")


def cmd_start(a, w):
    B = T.BLOCK
    block = get_block(a.block) if a.block else None
    task_id = block["task_id"] if block else a.task
    actions = []
    if block and block["actual_start"]:
        print("block already started at %s" % block["actual_start"].strftime("%H:%M"))
    if a.task and not block:
        mine = [b for b in w.blocks_of(w.plan_on(w.today)) if b["task_id"] == a.task and b["status"] == "planned"]
        if mine:
            block = mine[0]
    if block:
        if not block["actual_start"]:
            actions.append(("block %s: actual_start %s" % (block["title"], w.now.strftime("%H:%M")), lambda: verified(T.BLOCKS, block["id"], {B["actual_start"]: nowiso(w)})))
    else:
        if not a.task and not a.title:
            sys.exit("give a block, --task or --title")
        title = a.title or short_title(w.tasks[a.task]["title"])
        kind = a.kind or "deep-work"
        validate_kind(kind, title)
        def adhoc():
            plan = ensure_plan(w)
            f = {B["title"]: title, B["day"]: {"id": plan["id"]}, B["kind"]: kind, B["status"]: "planned", B["source"]: "adhoc", B["actual_start"]: nowiso(w)}
            if a.task:
                f[B["task"]] = {"id": a.task}
            rec = T.create(T.BLOCKS, [f])[0]
            print("adhoc block", rec["id"])
        actions.append(("create adhoc block %s (today's plan is created if missing)" % title, adhoc))
    plan = w.plan_on(w.today)
    if block and block["day_id"]:
        plan = next((p for p in w.plans if p["id"] == block["day_id"]), plan)
    if plan and plan["status"] == "planned":
        actions.append(("day %s: running" % plan["date"], lambda: verified(T.PLANS, plan["id"], {T.PLAN["status"]: "running"})))
    if task_id:
        t = w.tasks.get(task_id)
        if not t:
            sys.exit("unknown task %s" % task_id)
        held = t["who_id"] and not w.is_me(t["who_id"]) and not w.is_agent(t["who_id"])
        if held:
            print("NOTE: task is held by %s; its status and assignee are left alone" % t["who_name"])
        elif t["prog"] in ("backlog", "onhold"):
            F = {R.TF["prog"]: "in-progress"}
            raw = T.get_record(R.TASKS, task_id, [T.TASK_X["started"]])["fields"]
            if not raw.get(T.TASK_X["started"]):
                F[T.TASK_X["started"]] = nowiso(w)
            if not t["who_id"] and w.me:
                F[R.TF["who"]] = {"id": w.me["id"]}
            def go(F=F):
                verified(R.TASKS, task_id, F)
                task_log(task_id, "- %s · in-progress · started" % w.today)
            actions.append(("task %s: in-progress%s, log line" % (short_title(t["title"]), ", assigned to " + w.me["name"] if not t["who_id"] and w.me else ""), go))
    run(actions, a) if actions else print("nothing to change")


def cmd_finish(a, w):
    B = T.BLOCK
    block = get_block(a.block)
    if block["status"] == "moved":
        sys.exit("this block was moved; finish its replacement")
    if a.status in ("done", "partial") and a.minutes is None:
        sys.exit("--minutes is required: confirm the time actually spent, agent runtime is not your working time")
    if a.status == "skipped" and not a.reason:
        sys.exit("--reason is required when skipping")
    fields = {B["status"]: a.status}
    if a.minutes is not None:
        fields[B["actual_minutes"]] = a.minutes
    if a.reason:
        fields[B["reason"]] = a.reason
    actions = [("block %s: %s%s" % (block["title"], a.status, ", %d min" % a.minutes if a.minutes is not None else ""), lambda: verified(T.BLOCKS, block["id"], fields))]
    if a.task_progress:
        if not block["task_id"]:
            sys.exit("this block has no task")
        finished = a.task_progress in R.DONE_T
        if finished and not a.evidence:
            sys.exit("--evidence is required to move a task to a finished state")
        F = {R.TF["prog"]: a.task_progress}
        if finished and not T.get_record(R.TASKS, block["task_id"], [T.TASK_X["finished"]])["fields"].get(T.TASK_X["finished"]):
            F[T.TASK_X["finished"]] = nowiso(w)
        def go():
            verified(R.TASKS, block["task_id"], F)
            task_log(block["task_id"], "- %s · %s · %s" % (w.today, a.task_progress, a.evidence or "from block " + block["id"]))
        actions.append(("task %s: %s" % (block["task_id"], a.task_progress), go))
    elif a.evidence and block["task_id"]:
        actions.append(("task %s: log line" % block["task_id"], lambda: task_log(block["task_id"], "- %s · %s · %s" % (w.today, a.status, a.evidence))))
    run(actions, a)


def cmd_replan(a, w):
    B = T.BLOCK
    b = get_block(a.block)
    if b["status"] != "planned":
        sys.exit("only a planned block can be replanned (this one is %s)" % b["status"])
    day = dt.date.fromisoformat(a.date) if a.date else (b["start"].date() if b["start"] else w.today)
    start = hm(a.start) if a.start else (block_span(b)[0] if block_span(b) else None)
    if a.start and start is None:
        sys.exit("bad --start %r" % a.start)
    minutes = a.minutes or b["minutes"]
    if a.drop:
        if not a.reason:
            sys.exit("--reason is required")
        return run([("block %s: skipped, reason recorded" % b["title"], lambda: verified(T.BLOCKS, b["id"], {B["status"]: "skipped", B["reason"]: a.reason}))], a)
    target = w.plan_on(day)
    clash = []
    if start is not None and minutes:
        for x in w.blocks_of(target):
            sp = block_span(x)
            if x["id"] != b["id"] and holds_time(x) and sp and start < sp[1] and sp[0] < start + minutes:
                clash.append(x["title"])
    if clash:
        print("REFUSED: %s at %s overlaps %s" % (b["title"], fmt(start), ", ".join(clash)))
        sys.exit(2)
    if a.edit:
        current_day = b["start"].date() if b["start"] else None
        if b["actual_start"] or not current_day or current_day <= w.today or day <= w.today:
            sys.exit("--edit is only for an unstarted block on a future day, moving to a future day; use the default moved + replaces")
        if not target:
            sys.exit("no plan on %s; plan that day first or drop --edit" % day)
        f = {B["day"]: {"id": target["id"]}, B["minutes"]: minutes}
        if start is not None:
            f[B["start"]] = T.utc_iso(day, start)
        return run([("EDIT in place: %s to %s %s, %s min" % (b["title"], day, fmt(start) if start is not None else "unscheduled", minutes), lambda: verified(T.BLOCKS, b["id"], f))], a)
    if not a.reason:
        sys.exit("--reason is required: the shift is recorded, not overwritten")
    def go():
        plan = target or dict(id=T.create(T.PLANS, [{T.PLAN["date"]: day.isoformat(), T.PLAN["status"]: "planned"}])[0]["id"])
        verified(T.BLOCKS, b["id"], {B["status"]: "moved", B["reason"]: a.reason})
        same_day = bool(b["start"]) and b["start"].date() == day
        # A routine block moved to another date stops being that date's stamp, or the date's own occurrence would never be stamped.
        keep_routine = b["source"] == "routine" and same_day
        f = {B["title"]: b["title"], B["day"]: {"id": plan["id"]}, B["kind"]: b["kind"], B["status"]: "planned", B["source"]: "routine" if keep_routine else "plan", B["replaces"]: {"id": b["id"]}}
        if start is not None:
            f[B["start"]] = T.utc_iso(day, start)
        if minutes:
            f[B["minutes"]] = minutes
        if b["task_id"]:
            f[B["task"]] = {"id": b["task_id"]}
        if b["routine_id"] and keep_routine:
            f[B["routine"]] = {"id": b["routine_id"]}
        if b["notes"]:
            f[B["notes"]] = b["notes"]
        rec = T.create(T.BLOCKS, [f])[0]
        got = T.get_record(T.BLOCKS, rec["id"])["fields"]
        if (got.get(B["replaces"]) or {}).get("id") != b["id"]:
            sys.exit("VERIFY MISMATCH new block %s has no replaces link" % rec["id"])
        print("new block", rec["id"])
    run([("block %s: moved (%s)" % (b["title"], a.reason), lambda: None), ("new block on %s %s, %s min, replaces it" % (day, fmt(start) if start is not None else "unscheduled", minutes), go)], a)


def review_data(w, day):
    plan = w.plan_on(day)
    if not plan:
        sys.exit("no plan on %s" % day)
    bs = w.blocks_of(plan)
    rows = []
    for b in bs:
        t = w.tasks.get(b["task_id"])
        rows.append(dict(id=b["id"], title=b["title"], kind=b["kind"], status=b["status"], source=b["source"], start=b["start"].strftime("%H:%M") if b["start"] else None, planned=b["minutes"], actual=b["actual_minutes"],
                         task=b["task_id"], task_progress=t["prog"] if t else None, likely_done=bool(t and t["prog"] in ("finished_validating", "closed") and b["status"] == "planned")))
    carry = sorted({b["task_id"] for b in bs if b["task_id"] in w.tasks and w.tasks[b["task_id"]]["prog"] in OPEN_PROGRESS + ("finished_reviewing",) and b["status"] in ("planned", "partial")})
    return plan, bs, dict(date=day.isoformat(), plan_id=plan["id"], status=plan["status"], totals=totals(bs), capacity=plan["capacity"], blocks=rows, carry=carry)


def cmd_review(a, w):
    B, day = T.BLOCK, dt.date.fromisoformat(a.date) if a.date not in ("today", "yesterday") else w.today - dt.timedelta(days=1 if a.date == "yesterday" else 0)
    plan, bs, data = review_data(w, day)
    acting = a.all_as_planned or a.leave_unknown or a.outcomes
    if not acting:
        if a.json:
            print(json.dumps(data, ensure_ascii=False, indent=1))
            return
        print("%s · %s · planned %d · actual %d · unplanned %d · capacity %s" % (day, data["status"], data["totals"]["planned"], data["totals"]["actual"], data["totals"]["unplanned"], data["capacity"]))
        for r in data["blocks"]:
            print("  %s %-9s %-20s %s planned %s actual %s%s (%s)" % (r["start"] or "--:--", r["status"], r["kind"], r["title"], r["planned"], r["actual"], "  task finished: likely done" if r["likely_done"] else "", r["id"]))
        print("carry-over candidates: %s" % (", ".join(data["carry"]) or "none"))
        return
    actions = []
    def setb(b, f):
        return lambda: verified(T.BLOCKS, b["id"], f)
    if a.all_as_planned:
        for b in [x for x in bs if x["status"] == "planned"]:
            f = {B["status"]: "done"}
            if b["minutes"]:
                f[B["actual_minutes"]] = b["minutes"]
            if b["start"] and not b["actual_start"]:
                f[B["actual_start"]] = b["start"].astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            actions.append(("%s: done as planned" % b["title"], setb(b, f)))
    if a.outcomes:
        known = {b["id"]: b for b in bs}
        for o in json.load(open(a.outcomes)):
            b = known.get(o["block"])
            if not b:
                sys.exit("block %s is not on %s" % (o["block"], day))
            if o["status"] not in ("done", "partial", "skipped"):
                sys.exit("outcome status must be done, partial or skipped")
            f = {B["status"]: o["status"]}
            if o.get("minutes") is not None:
                f[B["actual_minutes"]] = o["minutes"]
            if o.get("reason"):
                f[B["reason"]] = o["reason"]
            actions.append(("%s: %s" % (b["title"], o["status"]), setb(b, f)))
    text = open(a.text_file).read() if a.text_file else a.text
    if a.leave_unknown and not text:
        text = "Outcomes were not recorded for this day."
    fields = {T.PLAN["status"]: "reviewed"}
    if text:
        fields[T.PLAN["review"]] = (plan["review"].rstrip() + "\n\n" if plan["review"].strip() else "") + text.strip()
    actions.append(("day %s: reviewed" % day, lambda: verified(T.PLANS, plan["id"], fields)))
    if run(actions, a):
        print("carry-over candidates: %s" % (", ".join(data["carry"]) or "none"))


def current(w):
    """The block to work on now: one already started, else the one covering this minute, else the next, else an earlier unfinished one."""
    plan = w.plan_on(w.today)
    if not plan:
        return dict(plan=None, current=None, next=None, earlier=[], blocks=[])
    bs = [b for b in w.blocks_of(plan) if b["status"] == "planned"]
    running = [b for b in bs if b["actual_start"]]
    covering = [b for b in bs if block_span(b) and block_span(b)[0] <= w.minute < block_span(b)[1]]
    ahead = [b for b in bs if block_span(b) and block_span(b)[0] > w.minute]
    earlier = [b for b in bs if block_span(b) and block_span(b)[1] <= w.minute and not b["actual_start"]]
    cur = running[-1] if running else covering[0] if covering else None
    nxt = next((b for b in ahead if not cur or b["id"] != cur["id"]), None)
    return dict(plan=plan, current=cur, next=nxt, earlier=earlier, blocks=w.blocks_of(plan))


def view(b):
    if not b:
        return None
    sp = block_span(b)
    return dict(id=b["id"], title=b["title"], kind=b["kind"], status=b["status"], start=fmt(sp[0]) if sp else None, end=fmt(sp[1]) if sp else None, minutes=b["minutes"], task=b["task_id"], routine=b["routine_id"], source=b["source"], started=bool(b["actual_start"]))


def cmd_now(a, w):
    c = current(w)
    fr = day_frame(w, w.today)
    data = dict(at=w.now.strftime("%Y-%m-%d %H:%M"), plan_status=c["plan"]["status"] if c["plan"] else None, focus=c["plan"]["focus"] if c["plan"] else None, current=view(c["current"]), next=view(c["next"]),
                earlier_unfinished=[view(b) for b in c["earlier"]], free=fr["free"], open_days=[d["date"] for d in open_days(w)], blocks=[view(b) for b in c["blocks"]])
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return
    print("%s · plan %s%s · %d min free" % (data["at"], data["plan_status"] or "none", " · " + data["focus"] if data["focus"] else "", data["free"]))
    if not c["plan"]:
        print("No plan for today. Offer plan-day.")
    if data["open_days"]:
        print("Not closed: " + ", ".join(data["open_days"]))
    show = lambda b: "%s %s %s (%s)" % ("%s-%s" % (b["start"], b["end"]) if b["start"] else "unscheduled", b["kind"], b["title"], b["id"])
    print("NOW: " + (show(data["current"]) if data["current"] else "nothing scheduled"))
    print("NEXT: " + (show(data["next"]) if data["next"] else "nothing"))
    for b in data["earlier_unfinished"]:
        print("EARLIER, no outcome: " + show(b))


def cmd_brief(a, w):
    days = range_days(w, a.range)
    frames = [day_frame(w, d, a.capacity) for d in days]
    cands, skipped = candidates(w, days, a.focus_goal)
    data = dict(at=w.now.strftime("%Y-%m-%d %H:%M"), range=[d.isoformat() for d in days], open_days=open_days(w), frames=frames, candidates=cands, skipped=skipped, plus_one=PLUS_ONE)
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return
    print("Brief %s · range %s..%s" % (data["at"], days[0], days[-1]))
    for d in data["open_days"]:
        print("NOT CLOSED %s (%s): %d blocks, %d with no outcome, %d open task(s), %d likely done" % (d["date"], d["status"], d["blocks"], d["no_outcome"], len(d["open_tasks"]), len(d["likely_done"])))
    for f in frames:
        print("%s %s · plan %s · capacity %s · free %d · plannable %d · gaps %s" % (f["date"], f["weekday"], f["plan_status"] or "none", f["capacity"], f["free"], f["plannable"], " ".join("%s-%s" % tuple(g) for g in f["gaps"]) or "none"))
        for r in f["routines"]:
            print("  routine %s %s %s min%s" % (r["start"], r["title"], r["minutes"], " (stamped)" if r["stamped"] else ""))
        for x in f["flags"]:
            print("  FLAG " + x)
    print("Candidates %d (skipped: %s)" % (len(cands), ", ".join("%s %d" % kv for kv in skipped.items() if kv[1]) or "none"))
    for i, c in enumerate(cands[:a.limit], 1):
        print("  %d. [%s] %s · %s · %s · %d min (%s) · %s (%s)" % (i, c["prio"], c["block_title"], c["project"] or "no project", c["why"], c["minutes"], c["minutes_from"], c["kind"], c["id"]))


def cmd_meetings(a, w):
    days = range_days(w, a.range)
    res = meetings(w, days, a.tasks or [])
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    if not res["proposals"]:
        print("No meeting suggested.")
    for p in res["proposals"]:
        print("%s · %s · with %s (%s) · %d min + %d prepare\n  %s\n  agenda: %s\n  link task: %s" % (p["signal"], p["project"], p["attendee"], p["attendee_source"], p["minutes"], p["prepare_minutes"], p["reason"], "; ".join(p["agenda"]), p["link_task"]))
    if res["held_back"]:
        print("(%d more held back: at most %d per session)" % (res["held_back"], MAX_MEETINGS))


def cmd_time(a, w):
    start, end = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    plans = {p["id"]: p for p in w.plans if p["date"] and start <= p["date"] <= end}
    bs = [b for b in w.blocks if b["day_id"] in plans]
    kinds = {}
    for b in bs:
        k = kinds.setdefault(b["kind"] or "(none)", dict(planned=0, actual=0))
        if b["status"] != "moved" and b["source"] != "adhoc":
            k["planned"] += b["minutes"] or 0
        k["actual"] += b["actual_minutes"] or 0
    tot = totals(bs)
    no_outcome = len([b for b in bs if b["status"] == "planned" and b["start"] and b["start"].date() < w.today])
    data = dict(from_=a.start, to=a.end, days=len(plans), totals=tot, by_kind=kinds, blocks=len(bs), no_outcome=no_outcome)
    if a.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return
    print("Time %s..%s · %d day(s), %d block(s) · planned %d · actual %d · unplanned %d · no outcome %d" % (a.start, a.end, len(plans), len(bs), tot["planned"], tot["actual"], tot["unplanned"], no_outcome))
    for k, v in sorted(kinds.items()):
        print("  %-20s planned %5d  actual %5d" % (k, v["planned"], v["actual"]))


def cmd_check(a, w):
    findings, replaced = [], successors(w)
    def add(sev, what, ref, fix):
        findings.append(dict(severity=sev, what=what, ref=ref, fix=fix))
    seen = {}
    for p in w.plans:
        if p["date"]:
            seen.setdefault(p["date"], []).append(p["id"])
    for d, ids in seen.items():
        if len(ids) > 1:
            add("high", "%d plan rows for %s" % (len(ids), d), " ".join(ids), "merge the blocks into one and soft-delete the rest")
    for p in w.plans:
        bs = w.blocks_of(p)
        if p["date"] and p["date"] < w.today and p["status"] != "reviewed":
            add("medium", "%s was never reviewed (%s)" % (p["date"], p["status"]), p["id"], "day.py review")
        timed = [dict(s=block_span(b)[0], e=block_span(b)[1], title=b["title"]) for b in bs if holds_time(b) and block_span(b)]
        if p["status"] != "reviewed":  # a closed day can't be replanned, so an old overlap has no fix
            for x, y in overlapping(timed):
                add("medium", "%s: %s overlaps %s" % (p["date"], x["title"], y["title"]), p["id"], "day.py replan one of them")
        if p["capacity"] and totals(bs)["planned"] > p["capacity"]:
            add("low", "%s: planned %d over capacity %d" % (p["date"], totals(bs)["planned"], p["capacity"]), p["id"], "replan or raise capacity")
    plan_ids = {p["id"] for p in w.plans}
    by_id = {b["id"]: b for b in w.blocks}
    for b in w.blocks:
        if not b["day_id"] or b["day_id"] not in plan_ids:
            add("high", "block %s has no active day" % b["title"], b["id"], "link it to a day or soft-delete it")
        if b["status"] == "moved" and not b["reason"]:
            add("medium", "moved block %s has no reason" % b["title"], b["id"], "fill change_reason")
        if b["status"] == "moved" and b["id"] not in replaced:
            add("medium", "moved block %s has no replacement" % b["title"], b["id"], "create one with replaces, or mark it skipped")
        if b["replaces_id"] and b["replaces_id"] in by_id and by_id[b["replaces_id"]]["status"] != "moved":
            add("low", "%s replaces a block that is not marked moved" % b["title"], b["id"], "mark the old block moved")
        if b["source"] == "routine" and not b["routine_id"]:
            add("medium", "routine block %s has no routine link" % b["title"], b["id"], "link it")
        if b["source"] == "adhoc" and b["minutes"]:
            add("low", "adhoc block %s has planned_minutes" % b["title"], b["id"], "clear it or change source to plan")
        t = w.tasks.get(b["task_id"])
        if t and b["status"] == "planned" and b["start"] and b["start"].date() >= w.today and t["prog"] in ("finished_validating", "closed", "cancelled"):
            add("low", "planned block %s points at a %s task" % (b["title"], t["prog"]), b["id"], "skip the block")
    for r in w.routines:
        if not r["active"]:
            continue
        if r["freq"] == "weekly" and not r["weekdays"]:
            add("medium", "weekly routine %s has no weekdays, so it never falls" % r["title"], r["id"], "set weekdays")
        if r["freq"] == "monthly" and r["month_day"] is None:
            add("medium", "monthly routine %s has no month_day, so it never falls" % r["title"], r["id"], "set month_day")
        if r["start"] is None:
            add("medium", "routine %s has no valid start_time" % r["title"], r["id"], "set HH:MM")
    if a.json:
        print(json.dumps(findings, ensure_ascii=False, indent=1))
        return
    print("Day check %s · %d plan(s), %d block(s), %d routine(s) · %d finding(s)" % (w.today, len(w.plans), len(w.blocks), len(w.routines), len(findings)))
    for f in sorted(findings, key=lambda f: ("high", "medium", "low").index(f["severity"])):
        print("[%s] %s (%s) -> %s" % (f["severity"], f["what"], f["ref"], f["fix"]))


def routine_fields(a, creating):
    Q, f = T.ROUTINE, {}
    if a.name:
        f[Q["title"]] = a.name
    if a.kind:
        validate_kind(a.kind, a.name or "routine")
        f[Q["kind"]] = a.kind
    if a.freq:
        f[Q["freq"]] = a.freq
    if a.weekdays:
        days = a.weekdays.split(",")
        if set(days) - set(DOW):
            sys.exit("weekdays must be from %s" % ",".join(DOW))
        f[Q["weekdays"]] = days
    if a.month_day is not None:
        f[Q["month_day"]] = a.month_day
    if a.start:
        if hm(a.start) is None:
            sys.exit("bad --start %r, use HH:MM" % a.start)
        f[Q["start"]] = a.start
    if a.minutes is not None:
        f[Q["minutes"]] = a.minutes
    if a.valid_from:
        f[Q["valid_from"]] = a.valid_from
    if a.valid_until:
        f[Q["valid_until"]] = a.valid_until
    if a.task:
        f[Q["task"]] = {"id": a.task}
    if a.notes:
        f[Q["notes"]] = a.notes
    if creating and not (a.name and a.freq and a.start and a.minutes):
        sys.exit("add needs --name, --freq, --start and --minutes")
    return f


def cmd_routine(a, w):
    if a.action == "list":
        rows = sorted(w.routines, key=lambda r: (not r["active"], r["start"] if r["start"] is not None else 9999))
        if a.json:
            print(json.dumps([dict(r, valid_from=str(r["valid_from"]), valid_until=str(r["valid_until"])) for r in rows], ensure_ascii=False, indent=1))
            return
        for r in rows:
            when = {"weekly": ",".join(r["weekdays"]), "monthly": "day %s" % r["month_day"]}.get(r["freq"], r["freq"])
            print("%s %s %s · %s min · %s · %s%s (%s)" % ("on " if r["active"] else "off", r["start_text"], r["title"], r["minutes"], r["kind"], when, "" if r["freq"] not in ("weekly", "monthly") else " " + r["freq"], r["id"]))
        return
    Q = T.ROUTINE
    if a.action in ("pause", "resume"):
        value = a.action == "resume"
        return run([("routine %s: %s; days already planned keep their blocks" % (a.ref, a.action), lambda: verified(T.ROUTINES, a.ref, {Q["active"]: value or None}))], a)
    if a.action == "add":
        f = routine_fields(a, True)
        W.validate_sets(T.ROUTINES, f)
        def go():
            rec = T.create(T.ROUTINES, [f])[0]
            print("routine", rec["id"])
        return run([("create routine %s" % a.name, go)], a)
    if not a.ref:
        sys.exit("set needs a routine id")
    f = routine_fields(a, False)
    if not f:
        sys.exit("nothing to set")
    run([("routine %s: %d field(s); only days not yet planned change" % (a.ref, len(f)), lambda: verified(T.ROUTINES, a.ref, f))], a)


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true")
    common.add_argument("--at", help="YYYY-MM-DDTHH:MM, Melbourne time; default is the clock")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    add = lambda name, fn: (lambda s: (s.set_defaults(fn=fn), s)[1])(sub.add_parser(name, parents=[common]))
    s = add("brief", cmd_brief)
    s.add_argument("range")
    s.add_argument("--capacity", type=int)
    s.add_argument("--focus-goal")
    s.add_argument("--limit", type=int, default=15)
    s = add("meetings", cmd_meetings)
    s.add_argument("range")
    s.add_argument("--tasks", nargs="*")
    add("now", cmd_now)
    s = add("apply", cmd_apply)
    s.add_argument("--input", required=True)
    s.add_argument("--allow-over", action="store_true", help="the user chose to go over capacity")
    s.add_argument("--yes", action="store_true")
    s = add("start", cmd_start)
    s.add_argument("block", nargs="?")
    s.add_argument("--task")
    s.add_argument("--title")
    s.add_argument("--kind")
    s.add_argument("--yes", action="store_true")
    s = add("finish", cmd_finish)
    s.add_argument("block")
    s.add_argument("--status", required=True, choices=("done", "partial", "skipped"))
    s.add_argument("--minutes", type=int)
    s.add_argument("--reason")
    s.add_argument("--task-progress", choices=("in-progress", "finished_reviewing", "finished_validating", "closed", "onhold"))
    s.add_argument("--evidence")
    s.add_argument("--yes", action="store_true")
    s = add("replan", cmd_replan)
    s.add_argument("block")
    s.add_argument("--reason")
    s.add_argument("--date")
    s.add_argument("--start")
    s.add_argument("--minutes", type=int)
    s.add_argument("--drop", action="store_true", help="no replacement: mark skipped with the reason")
    s.add_argument("--edit", action="store_true", help="edit in place; only an unstarted block on a future day")
    s.add_argument("--yes", action="store_true")
    s = add("review", cmd_review)
    s.add_argument("date", help="YYYY-MM-DD, today or yesterday")
    s.add_argument("--all-as-planned", action="store_true")
    s.add_argument("--leave-unknown", action="store_true", help="close the day without inventing outcomes")
    s.add_argument("--outcomes", help='JSON file: [{"block": "rec...", "status": "done", "minutes": 80, "reason": "..."}]')
    s.add_argument("--text")
    s.add_argument("--text-file")
    s.add_argument("--yes", action="store_true")
    s = add("time", cmd_time)
    s.add_argument("--from", dest="start", required=True)
    s.add_argument("--to", dest="end", required=True)
    add("check", cmd_check)
    s = add("routine", cmd_routine)
    s.add_argument("action", choices=("list", "add", "set", "pause", "resume"))
    s.add_argument("ref", nargs="?")
    s.add_argument("--name")
    s.add_argument("--kind")
    s.add_argument("--freq", choices=("daily", "weekdays", "weekly", "monthly"))
    s.add_argument("--weekdays", help="Mon,Fri")
    s.add_argument("--month-day", type=int, help="-1 = last day of the month")
    s.add_argument("--start", help="HH:MM")
    s.add_argument("--minutes", type=int)
    s.add_argument("--valid-from")
    s.add_argument("--valid-until")
    s.add_argument("--task")
    s.add_argument("--notes")
    s.add_argument("--yes", action="store_true")
    a = p.parse_args()
    at = None
    if a.at:
        at = dt.datetime.fromisoformat(a.at).replace(tzinfo=T.ZoneInfo(T.TZ))
    a.fn(a, World(at))


if __name__ == "__main__":
    main()
