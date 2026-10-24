#!/usr/bin/env python3
"""Offline regression tests (no database): ctx-append table/heading handling and resume blocker resolution."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import write as W, resume as RS  # noqa: E402

ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)

t = "## Risk Register\n| R | L |\n|---|---|\n| a | M |\n\n## Next\nx\n"
out = W.append_section(t, "## Risk Register", "| b | H |")
check("table row stays attached", "| a | M |\n| b | H |\n" in out and "\n\n## Next" in out)
out = W.append_section("## Change Log\n\n## Blockers\n", "## Change Log", "- 2026 · x")
check("no blank line after empty heading", out.startswith("## Change Log\n- 2026 · x\n"))
out = W.append_section("## Log\n- a\n", "## Log", "- b")
check("bullets still contiguous", out == "## Log\n- a\n- b\n")
out = W.append_section("## S\ntext\n", "## S", "- b")
check("prose then bullet keeps blank line", "text\n\n- b" in out)

sec = ("\n- 2026-10-07 · CRM API access not granted, blocks Step 12 · owner A · status open\n"
       "- 2026-10-07 · Vendor contract unsigned · owner B · status open\n"
       "- 2026-10-08 · CRM API access · status cleared 2026-10-08\n")
b = RS.open_blockers(sec)
check("cleared blocker resolved by later matching line", len(b) == 1 and "Vendor" in b[0])
check("reopened after clear stays open", len(RS.open_blockers(sec + "- 2026-10-09 · CRM API access revoked · owner A · status open\n")) == 2)
sys.exit(0 if ok else 1)
