This changes the shared type tree (1 new type plus 6 re-parents), so I need your OK before I write anything. Here's the plan.

**Current state.** There are 6 deployment types (28 entries in total), and none of them has a parent. A bare `deployment` type doesn't exist yet.

| Type | Entries | Id |
|---|---|---|
| deployment - new server | 11 | recha4MvklMZcPnILZU |
| deployment - docker-compose | 8 | reccVgbTtiSGacQURZG |
| deployment - k8s | 4 | recwKFT8vCKe1bm9LYn |
| deployment - web server | 3 | recKFnqunxQUkHcnWGo |
| deployment - caddy | 1 | reclMCYETdgQJ6oBZrv |
| deployment - private registry | 1 | recdlqefhAQjKZZQeOE |

**What I'd change (7 writes to `knowledge_type`, 0 to entries):**
1. Create a new type `deployment` with the description: "Deploying and operating services and servers: docker-compose, k8s, web servers, registries, new-server setup."
2. Set `parent_type = deployment` on each of the 6 types above.

None of the 28 entries change. They keep their specific types and simply appear under `deployment` in the tree. I'll write only `parent_type`, never `child_types`. I'll apply the changes one at a time, check each one, and finish by showing you the updated tree.

**Your call:**
- **Go ahead with all 6?** (yes / no / leave some out)
- **Add any of these as well?** They're about deployment but aren't named `deployment - ...`:
  - `k3s - operation` (1 entry, recK65efsm4TPQpUmzH). It could go under `deployment` next to `deployment - k8s`, or be merged into it later.
  - `Infra - services` (1 entry, recQPtbFE0X9fqR6ddI).

  I'd leave both out unless you say otherwise.

Note: I couldn't run the dry-run previews in this session because the permission check blocked them. Before each real write I'll run it once without `--yes` to confirm the preview.
