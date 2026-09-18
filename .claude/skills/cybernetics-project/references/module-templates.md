# Module Templates

A Plane **module** groups related work items (`cyb module create`, `cyb
module add-item`) — it is this fork's equivalent of a feature/epic bucket. Left
unstructured, a module degrades into a flat, un-ordered item dump. These
templates give every module the same four-phase skeleton so the *type* of
work item you're looking at is always obvious from its label, and so a
module can't be marked done without an explicit validation step:

1. **Scope** — one item. What is in/out, and what "done" means. Written
   *before* any exploration or execution item exists.
2. **Explore** — one or more items. Facts gathered before committing to an
   approach: root cause, prior art, current-state inventory, a spike.
3. **Build** — one or more items. The actual change, informed by Explore.
4. **Validate** — one item, created last, closed last. Checks the Build
   output against the criteria the Scope item wrote down — never skipped,
   never merged into a Build item.

This ordering is a convention, not something the CLI enforces — nothing
stops you from creating a Build item before a Scope item exists. Follow the
order anyway; it is the entire point of the template.

## One-time setup: phase labels

Create these once per project (labels are project-scoped, not
workspace-scoped):

```bash
cyb label create CYB --name scope    --color "#6e56cf"
cyb label create CYB --name explore  --color "#0091ff"
cyb label create CYB --name build    --color "#f76b15"
cyb label create CYB --name validate --color "#30a46c"
```

Every template below assumes these four labels exist. `cyb item list CYB
--label validate --json` then answers "what's left to validate" across every
module in the project in one call.

## Shared scaffolding shape

Every template:
1. Creates the module.
2. Creates the **Scope** item first, with no `--parent` — it anchors the rest.
3. Creates **Explore**/**Build**/**Validate** items with `--parent <scope-id>`,
   so `cyb item show <scope-ref>` always shows the whole module's lineage
   even if you forget which module it belongs to.
4. Adds every item to the module with `cyb module add-item`.

Substitute the printed `sequence_id` (e.g. `CYB-51`) for `<scope-id>` in the
commands below — `item create`'s JSON output includes it.

---

## 1. Feature development

New user-facing capability, built end to end.

| Phase | Items |
|---|---|
| Scope | Requirements + acceptance criteria for the feature |
| Explore | Prior-art review, UX/API design spike |
| Build | Implementation (one item per component if it spans several) |
| Validate | Acceptance test against the Scope item's criteria + docs updated |

```bash
cyb module create CYB --name "Auth: SSO login" --description "End-to-end SSO support"
cyb item create CYB --name "[Scope] SSO: requirements + acceptance criteria" --label scope --priority high
# capture the printed sequence_id as <S>
cyb item create CYB --name "[Explore] Survey SSO providers, pick one" --label explore --parent <S>
cyb item create CYB --name "[Build] Implement SSO login flow" --label build --parent <S>
cyb item create CYB --name "[Validate] Acceptance-test SSO against criteria; update docs" --label validate --parent <S>
cyb module add-item <S> --module "Auth: SSO login"
cyb module add-item <Explore-id> --module "Auth: SSO login"
cyb module add-item <Build-id> --module "Auth: SSO login"
cyb module add-item <Validate-id> --module "Auth: SSO login"
```

## 2. Bug investigation & fix

A defect that needs root-causing, not just patching.

| Phase | Items |
|---|---|
| Scope | Reproduction steps, affected versions/users, "fixed" definition |
| Explore | Root cause analysis (logs, traces, bisection) |
| Build | The fix + a regression test that would have caught it |
| Validate | Confirm the fix in the affected environment; confirm no new regressions |

```bash
cyb module create CYB --name "Bug: auth timeout under load"
cyb item create CYB --name "[Scope] Repro + affected versions + fix criteria" --label scope --priority urgent
cyb item create CYB --name "[Explore] Root-cause the timeout (trace + logs)" --label explore --parent <S>
cyb item create CYB --name "[Build] Fix + regression test" --label build --parent <S>
cyb item create CYB --name "[Validate] Confirm fixed in prod-like env; no new regressions" --label validate --parent <S>
```

Add each to the module with `cyb module add-item` as in template 1.

## 3. Research / spike

A question that needs an answer before any commitment is made — the module
may end in a decision, not code.

| Phase | Items |
|---|---|
| Scope | The question, constraints, and the decision deadline |
| Explore | Data gathering, prototypes, options compared |
| Build | *(often skipped)* — write the recommendation/ADR if the answer needs one |
| Validate | Peer review / stakeholder sign-off on the recommendation |

```bash
cyb module create CYB --name "Spike: pick a queue backend"
cyb item create CYB --name "[Scope] Question, constraints, decision deadline" --label scope
cyb item create CYB --name "[Explore] Prototype top 2 candidates" --label explore --parent <S>
cyb item create CYB --name "[Build] Write recommendation ADR" --label build --parent <S>
cyb item create CYB --name "[Validate] Get sign-off on the recommendation" --label validate --parent <S>
```

If Build is genuinely not needed, skip it — don't create a placeholder item
just to keep the phase count even.

## 4. Migration / refactor

Moving from one implementation/system to another without changing external
behavior.

| Phase | Items |
|---|---|
| Scope | Migration boundary (what's in/out) + rollback requirement |
| Explore | Inventory current usages/dependencies, risk assessment |
| Build | Phased migration steps (one item per phase or component) |
| Validate | Parity checks, rollback drill actually run, old path decommissioned |

```bash
cyb module create CYB --name "Migrate: legacy queue -> new queue"
cyb item create CYB --name "[Scope] Migration boundary + rollback plan" --label scope --priority high
cyb item create CYB --name "[Explore] Inventory current usages + dependency risk" --label explore --parent <S>
cyb item create CYB --name "[Build] Phase 1: dual-write" --label build --parent <S>
cyb item create CYB --name "[Build] Phase 2: cut over readers" --label build --parent <S>
cyb item create CYB --name "[Validate] Parity check + rollback drill + decommission old path" --label validate --parent <S>
```

Do not decommission anything as part of Build — decommissioning belongs in
Validate, after parity is proven.

## 5. Security review / audit

| Phase | Items |
|---|---|
| Scope | Assets/attack surface in scope, explicit exclusions, compliance target |
| Explore | Threat modeling, dependency/CVE scan, exploratory testing |
| Build | One remediation item per finding |
| Validate | Re-test each remediated finding; sign-off/attestation |

```bash
cyb module create CYB --name "Security review: payments API"
cyb item create CYB --name "[Scope] Assets in scope + exclusions + compliance target" --label scope --priority urgent
cyb item create CYB --name "[Explore] Threat model + dependency scan" --label explore --parent <S>
cyb item create CYB --name "[Build] Remediate: <finding 1>" --label build --parent <S>
cyb item create CYB --name "[Validate] Re-test remediations; sign-off" --label validate --parent <S>
```

Create one `[Build]` item per finding as Explore surfaces them, rather than
guessing the count up front.

## 6. Performance optimization

| Phase | Items |
|---|---|
| Scope | Target metric + budget (e.g. "p95 < 200ms"), baseline measurement task |
| Explore | Profiling, bottleneck identification |
| Build | The optimization itself |
| Validate | Benchmark against the budget; add a perf regression guard |

```bash
cyb module create CYB --name "Perf: checkout p95 latency"
cyb item create CYB --name "[Scope] Target: checkout p95 < 200ms; baseline measurement" --label scope
cyb item create CYB --name "[Explore] Profile checkout path, identify bottleneck" --label explore --parent <S>
cyb item create CYB --name "[Build] Optimize <bottleneck>" --label build --parent <S>
cyb item create CYB --name "[Validate] Benchmark vs budget; add perf regression guard" --label validate --parent <S>
```

A Build item with no preceding Explore item is a guess at what's slow, not
an optimization — don't skip the phase even under time pressure.

---

## Checking module health

```bash
cyb item list CYB --label validate --json     # every module's pending validation
cyb board CYB --json                          # state distribution across all modules at once
```

A module with items but no `validate`-labeled item anywhere in it has not
had its scope closed out — treat that as unfinished regardless of what state
its Build items are in.
