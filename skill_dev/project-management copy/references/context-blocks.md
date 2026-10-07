# `context` block templates and write protocol

`context` is Markdown and the only log store (until a `project_logs` table exists). Use these exact H2 headings so sections can be found and appended without rewriting prose.

## Write protocol (always)

1. `get_record` for the row immediately before writing.
2. Change only the target section (append for logs; replace only the block being edited).
3. `update_record` with the full new `context`.
4. `get_record` again; confirm every other section is byte-identical. If a human edited in between, merge and re-write; never overwrite their text.

## Goal

```
## Key Results
| KR | Metric | Baseline | Target | Current | Score | Owner | Date |
|---|---|---|---|---|---|---|---|
| KR1 | ... | 87% | 94% | 87% | 0.00 | ... | 2026-12-31 |

## Check-ins
### 2026-10-02 · avg 0.35
KR1 0.2 (+0.1) ... blockers: ... decisions: ...
```

## Project

```
Moves: KR1 (goal: <title>)
Repo: <path or URL>           <- agents match their working directory to this line (comma-separate several; scripts/resume.py)
Shape: build                   <- the task template used; close.py files the estimate record under it

## Charter
- Scope: ...
- Out of scope: ...
- Acceptance criteria: 1) ... 2) ...
- Fixed constraint: scope | time | cost
- Estimate: best 20d / likely 28d / worst 40d; buffer 20% (declared)   <- close.py parses this exact shape (d or w)
- Assumptions: ...
- Sponsor / sign-off: ...

## Risk Register
| Risk | Likelihood | Impact | Owner | Mitigation | Status |
|---|---|---|---|---|---|

## Communication Plan
Daily async, weekly status to sponsor, bi-weekly steering, on-milestone sign-off, on-risk-trigger escalation within 24 h.

## Change Log
- 2026-10-02 · CR-1 · <change> · reason · impact (scope/time/cost) · decision approved|rejected by <who>

## Blockers
- 2026-10-02 · <blocker> · owner · status open|cleared 2026-10-04

## Status Log
### 2026-10-02 · 🟡 AMBER
Accomplished: ... Planned: ... Risks & issues: ... Decisions needed: ... Metrics: completion 40%, SPI 0.9, overdue 2

## Health Check
### 2026-11-25
Objectives still valid? Scope crept? Timeline/budget realistic? Risks materialised? Stakeholders aligned? Team sustainable? -> findings, actions.

## Retro
Went well / didn't / confused us / do differently (owner + date) / expectation gaps.

## Lessons
- <lesson> -> knowledge: <entry title>

## Estimation Record
| Project | Shape | Likely | Actual | Actual/Likely | On-time | Finished |
|---|---|---|---|---|---|---|
(one row, produced by `scripts/close.py stats`)
```

Blockers are append-only. To clear one, append a line whose blocker text matches the open one and says `status cleared YYYY-MM-DD` (e.g. `- 2026-10-08 · CRM API access · status cleared 2026-10-08`); `resume.py` then stops listing it. `ctx-append` keeps table rows and bullet lists contiguous.

RAG emoji: 🟢 GREEN, 🟡 AMBER, 🔴 RED. Append new Status Log, Check-in and Change Log entries at the end of their section, newest last.

## Task

```
Due: 2026-10-09
Gate: no DO task starts until this is finished     (optional)
Depends: Step 03                                    (optional)
Est: 2d                                             (optional)
Acceptance: <observable condition>                  (optional)

<details>

## Log
- 2026-10-02 · in-progress · started
- 2026-10-03 · finished_reviewing · PR #12 merged, tests pass (commit abc1234)
```
