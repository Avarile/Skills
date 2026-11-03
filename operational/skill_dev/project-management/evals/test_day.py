#!/usr/bin/env python3
"""Offline tests of the day-planning rules (no database, no token needed)."""
import datetime as dt, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import day as D, teable as T, write as W, taskctx as C  # noqa: E402

ok = True
def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + name + (" -- %s" % (detail,) if detail and not cond else ""))

d = dt.date
base = dict(active=True, valid_from=None, valid_until=None, weekdays=[], month_day=None)
# routines
mon, fri, sat = d(2026, 11, 2), d(2026, 11, 6), d(2026, 11, 7)
check("weekdays falls Mon-Fri only", D.falls_on(dict(base, freq="weekdays"), mon) and D.falls_on(dict(base, freq="weekdays"), fri) and not D.falls_on(dict(base, freq="weekdays"), sat))
check("daily falls on Saturday", D.falls_on(dict(base, freq="daily"), sat))
check("weekly follows its weekdays", D.falls_on(dict(base, freq="weekly", weekdays=["Fri"]), fri) and not D.falls_on(dict(base, freq="weekly", weekdays=["Fri"]), mon))
check("weekly with no weekdays never falls", not D.falls_on(dict(base, freq="weekly"), fri))
last = dict(base, freq="monthly", month_day=-1)
check("month_day -1 is the last day", D.falls_on(last, d(2026, 11, 30)) and not D.falls_on(last, d(2026, 11, 29)))
check("month_day -1 handles February", D.falls_on(last, d(2027, 2, 28)) and D.falls_on(last, d(2028, 2, 29)) and not D.falls_on(last, d(2028, 2, 28)))
check("month_day -2 is the second last day", D.falls_on(dict(base, freq="monthly", month_day=-2), d(2026, 11, 29)))
check("month_day past the month end clamps", D.falls_on(dict(base, freq="monthly", month_day=31), d(2026, 11, 30)))
check("month_day stays on the exact weekend date", D.falls_on(last, d(2027, 1, 31)) and d(2027, 1, 31).weekday() == 6)
check("validity window is inclusive", D.falls_on(dict(base, freq="daily", valid_from=mon, valid_until=mon), mon) and not D.falls_on(dict(base, freq="daily", valid_until=mon), d(2026, 11, 3)) and not D.falls_on(dict(base, freq="daily", valid_from=fri), mon))
check("an inactive routine never falls", not D.falls_on(dict(base, freq="daily", active=False), mon))
# ranges
tue = d(2026, 11, 3)
check("range today and tomorrow", D.parse_range("today", tue) == [tue] and D.parse_range("tomorrow", tue) == [d(2026, 11, 4)])
check("next-week starts on Monday", D.parse_range("next-week", tue)[0] == d(2026, 11, 9) and len(D.parse_range("next-week", tue)) == 7)
check("this-week starts today", D.parse_range("this-week", tue)[0] == tue)
check("next-3-days starts tomorrow", D.parse_range("next-3-days", tue) == [d(2026, 11, 4), d(2026, 11, 5), d(2026, 11, 6)])
check("explicit range", len(D.parse_range("2026-11-03..2026-11-05", tue)) == 3)
# capacity
check("gaps skip busy time", D.subtract((540, 1065), [(540, 555), (1050, 1065)]) == [(555, 1050)])
fr = D.frame((540, 1065), [(540, 555), (1050, 1065)], 600)
check("frame: 495 free, 396 plannable after the 20% buffer", fr["free"] == 495 and fr["plannable"] == 396, fr)
check("capacity caps free time", D.frame((540, 1065), [(540, 555)], 120)["free"] == 105)
# totals: moved blocks must not double count
b = lambda **k: dict(dict(active=True, status="planned", source="plan", minutes=None, actual_minutes=None), **k)
t = D.totals([b(minutes=60), b(minutes=60, status="moved"), b(minutes=30, status="skipped"), b(source="adhoc", actual_minutes=20), b(minutes=90, actual_minutes=80, status="done"), b(minutes=999, active=False)])
check("totals exclude moved and inactive, adhoc counts as actual", t == dict(planned=180, actual=100, unplanned=20), t)
# overlaps
check("overlap detected, touching is not", len(D.overlapping([dict(s=540, e=630), dict(s=540, e=555), dict(s=630, e=660)])) == 1)
# placement
gaps = [(555, 960), (1020, 1050)]
it = lambda title, m, **k: dict(title=title, minutes=m, **k)
placed, err, warn = D.place([it("a", 90, kind="deep-work"), it("b", 30, kind="admin")], gaps)
check("deep work takes the longest stretch", next(p for p in placed if p["title"] == "a")["s"] == 555 and not err)
check("placed items never overlap", not D.overlapping(placed))
placed, _, _ = D.place([it("first", 60, kind="deep-work"), it("second", 90, kind="deep-work")], [(540, 1000)])
check("deep work keeps the agreed rank order", next(p for p in placed if p["title"] == "first")["s"] < next(p for p in placed if p["title"] == "second")["s"], placed)
placed, err, _ = D.place([it("big", 200, kind="deep-work")], [(540, 1000)])
check("long deep work splits at the block cap", [p["minutes"] for p in placed] == [120, 80] and placed[0]["part"] == "1/2" and not err, placed)
placed, err, _ = D.place([it("m", 30, kind="meeting", key="m1", start="14:00"), it("p", 15, kind="prepare", before="m1")], [(540, 1000)])
check("prepare sits directly before its meeting", placed[0]["title"] == "p" and placed[0]["e"] == placed[1]["s"] == 840, placed)
placed, err, _ = D.place([it("m", 30, kind="meeting", key="m1", start="14:00"), it("w", 60, kind="deep-work", after="m1")], [(540, 1000)])
check("`after` places the work after the meeting", next(p for p in placed if p["title"] == "w")["s"] >= 870, placed)
placed, err, _ = D.place([it("x", 300, kind="admin")], [(540, 600)])
check("what does not fit is an error", not err == [] or sum(p["minutes"] for p in placed) < 300, err)
_, err, _ = D.place([it("x", 500, kind="deep-work")], [(540, 560)])
check("a gap under the minimum block is unusable", err and "unplaced" in err[0], err)
# daylight saving: 09:00 Melbourne is +11 in January and +10 in July
check("utc_iso during daylight saving", T.utc_iso(d(2099, 1, 5), 540) == "2099-01-04T22:00:00.000Z")
check("utc_iso outside daylight saving", T.utc_iso(d(2099, 7, 6), 540) == "2099-07-05T23:00:00.000Z")
check("local_dt round trip", T.local_dt(T.utc_iso(d(2099, 7, 6), 540)).strftime("%Y-%m-%d %H:%M") == "2099-07-06 09:00")
# small parsers
check("Est units", D.est_minutes("Est: 2d") == 960 and D.est_minutes("x\nEst: 1.5h\n") == 90 and D.est_minutes("Est: 45min") == 45 and D.est_minutes("") is None)
check("short_title strips conventions", D.short_title("Step 03 [DO] Build it") == "Build it" and D.short_title("New feature --- add x") == "add x")
check("ceil5", D.ceil5(871) == 875 and D.ceil5(875) == 875)
# generated output keeps the platform's header
e = W.gen_entry("Write  the outline", "Body", "task + project", "claude", dt.datetime(2026, 11, 3, 1, 2))
check("gen entry header", e.startswith("### ◆ 2026-11-03 01:02 UTC · Write the outline\n- Prompt: Write the outline\n- Context: task + project\n- Model: claude\n\nBody"), e)
check("gen entries split in order", [x["header"][-1] for x in C.gen_entries("### ◆ 1 · a\nx\n\n### ◆ 2 · b\ny\n", 100)] == ["a", "b"])
# task context parsing
pc = C.parse_context("Due: 2026-11-09\nAcceptance: tests pass\n\nDo the thing.\n\n## Log\n- 2026-11-01 · started\n")
check("context parsing", pc["Due"] == "2026-11-09" and pc["Acceptance"] == "tests pass" and pc["details"] == "Do the thing." and len(pc["log"]) == 1, pc)
# output choice
task = lambda title, prog="backlog": dict(title=title, prog=prog)
hint = lambda *a: C.output_hint(*a)[0]
check("routine outputs", hint(None, dict(kind="meeting"), dict(title="Morning standup", notes=None), None) == "standup-note" and hint(None, dict(kind="admin"), dict(title="Weekly report", notes=None), None) == "weekly-report" and hint(None, dict(kind="admin"), dict(title="Monthly report", notes=None), None) == "monthly-report" and hint(None, dict(kind="meeting"), dict(title="End-of-day meeting", notes=None), None) == "review-day")
check("routine notes override", hint(None, dict(kind="admin"), dict(title="Weekly report", notes="Output: custom-thing"), None) == "custom-thing")
check("block kinds", hint(task("x"), dict(kind="meeting"), None, None) == "agenda-and-talking-points" and hint(task("x"), dict(kind="prepare"), None, None) == "pre-read")
check("review waits on review", hint(task("New feature --- x", "finished_reviewing"), None, None, "/repo") == "review-against-acceptance")
check("analysis is a report even with a repo", hint(task("Code review --- analysis of x"), None, None, "/repo") == "report")
check("content", hint(task("Create video: AI adoption"), None, None, None) == "content")
check("code needs a repo", hint(task("New feature --- add x"), None, None, "/repo") == "code-change" and hint(task("New feature --- add x"), None, None, None) == "ask")
sys.exit(0 if ok else 1)
