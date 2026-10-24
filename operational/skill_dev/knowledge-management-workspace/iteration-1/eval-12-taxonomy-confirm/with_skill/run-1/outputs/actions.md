## Calls made
- `cat skill_dev/knowledge-management/SKILL.md` + `ls -R skill_dev/knowledge-management`: read the skill; taxonomy changes need the user's OK (rule 5 / autonomy ceiling).
- `cat references/taxonomy.md references/workflows.md`: parent type = bare domain; never write child_types; taxonomy workflow: list with count, OK, apply one by one with --yes, finish with `kb.py types`.
- `python3 skill_dev/knowledge-management/scripts/kb.py types`: 42 types, 129 typed entries. Found 6 `deployment - *` types (new server 11, docker-compose 8, k8s 4, web server 3, caddy 1, private registry 1), all without a parent. No `deployment` type exists. Adjacent: `k3s - operation` (1), `Infra - services` (1).
- `kb.py type-set "deployment" --create --description ...` (dry run) + `kb.py type-set "deployment - k8s" --parent-type "deployment"` (dry run) + `kb.py type deployment`: DENIED by the Claude Code auto-mode permission classifier. Nothing ran and nothing was retried.
- `grep` + `sed -n 752,800p skill_dev/knowledge-management/scripts/kb.py`: read the cmd_type_set source. It is a dry run unless --yes, refuses a duplicate --create, guards against cycles, writes only parent_type (link to a single record), and reads back and verifies.

## Proposed writes
After the user says yes (the user has not answered yet), run one at a time from the repo root. Dry-run each first, then add `--yes`:
1. `python3 skill_dev/knowledge-management/scripts/kb.py type-set "deployment" --create --description "Deploying and operating services and servers: docker-compose, k8s, web servers, registries, new-server setup." --yes`
2. `python3 skill_dev/knowledge-management/scripts/kb.py type-set "deployment - new server" --parent-type "deployment" --yes`
3. `python3 skill_dev/knowledge-management/scripts/kb.py type-set "deployment - docker-compose" --parent-type "deployment" --yes`
4. `python3 skill_dev/knowledge-management/scripts/kb.py type-set "deployment - k8s" --parent-type "deployment" --yes`
5. `python3 skill_dev/knowledge-management/scripts/kb.py type-set "deployment - web server" --parent-type "deployment" --yes`
6. `python3 skill_dev/knowledge-management/scripts/kb.py type-set "deployment - caddy" --parent-type "deployment" --yes`
7. `python3 skill_dev/knowledge-management/scripts/kb.py type-set "deployment - private registry" --parent-type "deployment" --yes`
8. Verify (read-only): `python3 skill_dev/knowledge-management/scripts/kb.py types`

Only if the user opts in: `kb.py type-set "k3s - operation" --parent-type "deployment" --yes` and/or `kb.py type-set "Infra - services" --parent-type "deployment" --yes`.

No entry (`knowledges`) records change, and `child_types` is never written. If `--parent-type "deployment"` comes back ambiguous after step 1 (the bare name also matches the children), use the new type's record id from step 1's output instead.
