# Model mapping: OKR + PDCA onto goals / projects / tasks

| Layer | Role | Where |
|---|---|---|
| Goal | OKR Objective: qualitative, memorable, slightly uncomfortable | `goals.title`; `deadline` = period end; KRs in `## Key Results` |
| Project | One PDCA cycle that serves a KR (an Initiative) | `projects`; `context` says `Moves: KR1` |
| Task | A step inside a PDCA phase | `tasks`, title `Step NN [PHASE] ...` |
| Knowledge | Inputs at Plan, lessons at Act | `refer_knowledge`, `related_knowledge` |

Depth on the methods lives in `project_frameworks` (`OKR`, `PDCA`). Read it only when the user asks for method detail or a template needs checking.

## OKR rules (lint at `plan-goal` and `checkin`)

- <=3 Objectives per period, <=3 Key Results per Objective.
- Every KR: metric, baseline, target, date, owner. Score 0.0-1.0 = (current - baseline) / (target - baseline), clipped. Healthy average about 0.7; 1.0 usually means the target was too easy.
- KRs are outcomes, never deliverables or activity. "Ship the new layer" is an Initiative (project); "task success rate >= 94%" is a KR. Reject and rewrite KRs that are tasks.
- Check-in weekly, review monthly, close quarterly. Flag a KR that drops >0.2 in a week, or is below 0.4 at the midpoint.
- Never tie scoring to performance review.

## PDCA phases and what each must produce

| Phase | Outputs (project `context` blocks / tasks) |
|---|---|
| PLAN | Charter (scope, out-of-scope, acceptance criteria, fixed constraint, estimate range + declared buffer 20-30%, assumptions), Risk Register (top 3+), Communication Plan, charter sign-off **gate task** |
| DO | Change Log, Blockers, weekly Status Log entries, demos each 1-2 week increment; no build work before the gate |
| CHECK | Milestone sign-offs in writing, mid-project Health Check (projects >3 months or at 50% of timeline), retrospective, honest metrics |
| ACT | Blameless post-mortem with owned actions, lessons written to knowledge, estimation norms updated, next-cycle draft |

## Project status ladder

| `projects.progress` | Meaning | Entry criteria (check; ask if unmet) |
|---|---|---|
| `backlog` | Idea, no commitment | none |
| `preparing` | PLAN in progress | charter drafting started |
| `initiated` | PLAN gate passed | charter complete (scope, out-of-scope, acceptance, estimate range + buffer, top-3 risks, comms plan) and sign-off task finished |
| `in-progress` | DO | `initiated` criteria met |
| `finished-reviewing` | CHECK 1: deliverables reviewed by peer or sponsor | all DO tasks finished; review recorded |
| `finished-validating` | CHECK 2: validated against acceptance criteria | each criterion has an evidence line |
| `finished-testing` | CHECK 3: tests, UAT, security review passed | test evidence recorded |
| `finalized` | ACT complete | retro done, lessons in knowledge, estimation norms updated, links set |
| `onhold` / `cancelled` | Paused / stopped | reason logged in `## Change Log` |

Never auto-advance. Suggest: "all 6 tasks finished; move project to `finished-reviewing`?".

## Ownership (who is responsible)

- `projects.lead_by` = the single accountable owner of the project (answers "who do I ask?"). The sponsor is a person in the Charter, not a field.
- `tasks.assigned_to` = the single person or agent persona responsible for doing the task. Contacts include agent personas, so assignment works the same for humans and agents.
- A task with no assignee is *claimable*, not ownerless: `plate` lists it under Unassigned, `resume --as` offers it to an agent. In-progress work should always have an assignee.
- Default split when scaffolding: the lead takes PLAN, CHECK and ACT; the doer takes DO. Confirm with the user.
- Workload limit: more than 3 tasks in progress for one person is flagged by `assign.py workload`.

## Task conventions

- Title: `Step NN [PLAN|DO|CHECK|ACT] Verb object`. Start with a verb. Milestones end `(M1)`. Split anything larger than about 2 working days.
- `context` line 1: `Due: YYYY-MM-DD`. Optional lines: `Gate: <what it unlocks>`, `Depends: Step 03`, `Est: 2d`, `Acceptance: ...`. Then `## Log` (append-only, dated, with evidence).
- A **gate task** blocks every later DO task. Starting a DO task while its gate is unfinished is flagged, not silently allowed.
- Every project has at least one CHECK and one ACT task (retro, lessons -> knowledge).
- Status: default start `backlog`. "Done" = `finished_validating`; `finished_reviewing` = delivered, awaiting check; `closed` = closed out (user asked to close, or project close).
- Priority: `urgent` (today/blocking), `important`, `prioritise`, `normal` (default), `can wait`.

## Task skeleton templates (derived from the existing mock rows; Phase 1 stores them in `assets/templates/`)

| Shape | Steps | Distinguishing elements |
|---|---|---|
| personal-small | ~6 | scope, do, verify, one takeaway |
| build | ~14 | data audit, design, build views, mid-point, verify, retro, lessons |
| client-delivery | ~25 | sponsor alignment, charter gate, M1-M3 with written sign-offs, health check, independent review, UAT, go-live |
| program | ~18 | workstreams, dependency map, steering committee, change control board, KPI review |
| infra-build | ~10 | landing zone, security baseline, DR test, penetration test |
| migration | ~11 | inventory, wave plan, cutover per wave, verification |

All include: charter gate, mid-point check, retro, post-mortem, lessons -> knowledge, estimation update. Due dates derive from the estimate range plus declared buffer and are shown in the preview, never invented silently.

## Escalation ladder

L1 own it (within team capacity; log it). L2 inform sponsor in writing (milestone affected). L3 steering within 24 h (delivery or budget threatened). L4 executive with options and a recommendation. Impact <5%: absorb and log. Impact >5%: written notice within 24 h.
