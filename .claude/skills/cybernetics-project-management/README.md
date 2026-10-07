# plane-project-management

A Claude skill for the Plane workspace behind `projects.avarile.com` (MCP server `cybernetics-project-management`, 96 tools). It sits next to `project-management` (cybernetics-data) and does not replace it.

## Scope
Projects, work items, modules, cycles, intake, estimates and agentic members, as a PDCA practice. Verbs: plate, status, portfolio, capture, plan-project, start/finish/hold/cancel, assign/lead/workload, block/risk/change, cycle-plan, triage, report/checkin/healthcheck, close, link, doctor, agent-run, find, comment, history, estimate, members, workflow, agents, restore. `members`, `workflow`, `agents` and `restore` are human mode only.

## Install
The skill is discovered from `.claude/skills/plane-project-management/` in this repo. The MCP server must be connected in Claude Code; the skill loads tool schemas with ToolSearch on demand.

## Layout
- `SKILL.md` modes, verbs, 19 core rules, disambiguation
- `references/tool-catalogue.md` every tool, args, enums
- `references/quirks.md` 50 behaviours (tested / schema / untested)
- `references/model-mapping.md` PDCA and OKR onto Plane
- `references/tool-map.md` verb to call sequence
- `references/workflows.md` flows and output formats
- `references/agent-protocol.md` autonomy ceiling and agentic-member flow
- `assets/templates/` HTML snippets and weekly report
- `evals/evals.json` 18 prompts (1-12: 41/45 with skill, 38/45 baseline; 13-18: 24/24 with skill, 19/24 baseline; single runs)

## Known limits
No OKR object in Plane (convention in the project description); no way to remove a relation or clear a field through MCP; guest permissions untested; pages and file upload unavailable.

## Origin
Built by Plane project PLANESKILL (workspace `cybernetics`); its items hold the evidence for each step. The extension (find, comment, history, estimate, members, workflow, agents, restore) was probed on the archived scratch project PMSKX with a designer and a developer agent.
