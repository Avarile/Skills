I looked at your `knowledge_type` table (42 types). There's no `deployment` type yet. Six types are clearly deployment types, going by their `deployment - …` prefix:

| Type | id | Entries |
|---|---|---|
| deployment - docker-compose | reccVgbTtiSGacQURZG | 8 |
| deployment - k8s | recwKFT8vCKe1bm9LYn | 4 |
| deployment - new server | recha4MvklMZcPnILZU | 11 |
| deployment - web server | recKFnqunxQUkHcnWGo | 3 |
| deployment - private registry | recdlqefhAQjKZZQeOE | 1 |
| deployment - caddy | reclMCYETdgQJ6oBZrv | 1 |

**Plan:**
1. Create a new type named **`deployment`** (active, with no parent).
2. Set `parent_type` = `deployment` on each of the six types above. `missav_meta_Ayumi_Ryo → missav_meta` already uses `parent_type` this way.

Nothing else changes. The 28 knowledge entries stay linked to the same types, and I won't rename or delete anything. All of these changes can be undone: clearing `parent_type` and deleting the new parent puts things back as they are now.

**Before I make the change, two questions:**

- **Do you want to add these borderline types too?** They're deployment or infra related, but they don't have the `deployment -` prefix:
  - `k3s - operation` (K3S Cheatsheet). It fits with `deployment - k8s`.
  - `Infra - services` (K3s-Infras)
  - `ci-cd - github-actions` (NestJS CI/CD pipeline)
  - `WOW` (includes "World of Warcraft Deployment"). This is probably not a deployment type, so I'd leave it out.
- **Should I keep the child names as they are?** For example, I could rename `deployment - k8s` to just `k8s` now that the parent shows the grouping. By default I'll leave the names unchanged.

There's also a quirk in the table. It has two hierarchy fields: `parent_type`, and a separate `child_types` field that isn't linked to it. Only `parent_type` is in use, so I'll set that one. The parent's `child_types` column will stay empty unless you want me to fill it in too.

Reply "go" to group just the six `deployment -` types, or tell me which of the extra types to include.
