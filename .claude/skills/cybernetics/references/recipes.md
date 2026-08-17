# Recipes

All examples assume `cyb` resolves to `node .claude/skills/cybernetics/bin/cyb`,
run from the repository root.

## Start a project from nothing

```bash
cyb project create --name "Cybernetics Core" --identifier CYB
cyb label create CYB --name bug --color "#e5484d"
cyb label create CYB --name chore --color "#8e8e8e"
cyb state list CYB          # confirm the five default states
```

## Capture a backlog in one pass

```bash
cyb item create CYB --name "Fix auth timeout" --priority high --label bug
cyb item create CYB --name "Update API docs" --priority low --label chore
cyb board CYB               # confirm placement — one request, not one per item
```

## Run a sprint

```bash
cyb cycle create CYB --name "Sprint 1" --start 2026-08-17 --end 2026-08-31
cyb cycle add-item CYB-1 --cycle "Sprint 1"
cyb cycle add-item CYB-2 --cycle "Sprint 1"
cyb cycle list CYB
```

## Daily status sweep

```bash
cyb my --json                                   # what is on your plate
cyb item list CYB --state "In Progress" --json  # what is moving
cyb board CYB                                   # the whole picture, one call
```

Prefer `board` over listing each state separately — it is one request rather
than five, and the 60 req/min budget is shared with everything else you do
this session.

## Move work forward

```bash
cyb item move CYB-42 "In Progress"
cyb comment add CYB-42 "Picked this up; blocked on the schema migration."
cyb item move CYB-42 Done
```

## Triage an unowned backlog

```bash
cyb item list CYB --state Backlog --json
cyb item assign CYB-7 avarile
cyb item update CYB-7 --priority urgent --target-date 2026-08-24
```

## Find something

```bash
cyb search "auth" --project CYB --json
```

`search` filters client-side over at most 500 items — this fork exposes no
server-side search. Narrow with `--project` rather than raising the cap; the
cap is fixed and will not go higher.

## Work interactively across many items in one project

```bash
cyb ui
cyb:-> cd CYB
cyb:CYB> ls --state todo
cyb:CYB> open 42
cyb:CYB> mv 42 "In Progress"
cyb:CYB> exit
```

The session holds one `Client` for its whole lifetime, so `remaining`/
`resetAt` from the rate-limit headers are tracked across every line — closer
to how an agent should treat its own multi-command session budget than
shelling out to `cyb` once per action.

## Clean up (destructive)

Always confirm with the user before running these.

```bash
cyb item delete CYB-42          # exits 2, shows what it would delete
cyb item delete CYB-42 --yes    # actually deletes
```
