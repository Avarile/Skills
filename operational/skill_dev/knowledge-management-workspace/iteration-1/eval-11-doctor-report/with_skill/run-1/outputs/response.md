I ran the knowledge base audit (`kb.py doctor`, read-only) and opened the flagged entries to check them. **Nothing has been changed yet.** Every fix below needs your OK, one group at a time.

**Overall:** 133 entries, 42 types, 76 things to fix. There are also two information-only findings (G and H) at the end.

## Decisions I need from you

1. **Duplicates (F):** can I merge or archive the copies listed below?
2. **New Server Init series (C + D):** can I fix its type and give it a hub entry?
3. **Temp, empty and untitled entries (B + E):** keep, retitle or archive? I've suggested one for each.
4. **Type tree (A):** can I add 3 parent types, put the children under them, and rename 4 types?

---

## F. Near-duplicates: 7 pairs flagged, 3 are real

| Pair | What I found | Proposal |
|---|---|---|
| `new-server-ubuntu-26.04=>basic app` (rec2Ug6TCRr1cXEB2DA) vs `New Server Init - Step 1 security` (recg3LHM211E5Dlz6Cy) | **Same body word for word** (user, SSH, UFW, Fail2Ban). The old title is also wrong: this is the security content, not "basic app". | Keep the Step 1 entry. Archive the old one and link the two as related. |
| `new-server-ubuntu-26.04 => security` (recUU9OzVGzIIZn9LuR) vs `New Server Init - Step 2 basic deps for nodejs` (recqhcHmCpmtsOqVchC) | 86% the same body (NVM, pnpm, PM2, Docker, Caddy). The old title is wrong again: it's the basic deps, not security. The two old titles were swapped. | Keep Step 2. Copy any lines only the old one has into it, then archive the old one and link them as related. |
| JUR-629 (rech2Hpkg0pyay4Od4N) vs JUR-629 (recsiOjIozO1LiYDcWm) | The first is an empty, untyped copy of the second. | Archive the empty one. |
| JUR-330 (recUXZ2IZLFGF39vFBR) vs JUR-330 (recZzXzWruedCPu2Yoz) | Same title, but different links (uncensored vs subtitled). | Keep both. Retitle them or link them as related if you like. |
| `Docker Compose - Infra Services` (recensHzE0p2rnRPJIF) vs `New Server Init - Step 2: Docker Compose Services` (recXgCbs4Lq0yHhSmlg) | Same services, but only 44% of the body matches. | Link as related, no merge. Or I can compare them in full first. |
| `Docker Compose - Complete Service Template` (recQAnzSLANbLcNGUSS) vs `docker-compose - Old Micro-server` (recse1nz5Cj1PcM9nNg) | 58% the same body. Looks like an older version vs the current one. | Link as related. |
| JUR-564 vs JUR-624 | Different titles that happen to look alike. | False alarm, nothing to do. |

## C + D. New Server Init series

- `New Server Init - Step 1 security` (recg3LHM211E5Dlz6Cy) has type **deployment - web server**, but the rest of the series uses **deployment - new server**. I'd move it.
- The series has no hub entry, and the step numbers clash (two Step 1s and two Step 2s). I'd create a short hub entry, **"New Server Init"** (type deployment - new server), listing the steps in order:
  1. Step 1 security (recg3LHM211E5Dlz6Cy)
  2. Step 1: Ubuntu 22.04 Setup Script (rec2fFF09HzGOa2mIdX)
  3. Step 2 basic deps for nodejs (recqhcHmCpmtsOqVchC)
  4. Step 2: Docker Compose Services (recXgCbs4Lq0yHhSmlg)
  5. Step 3: SCP Code Transfer Script (recXQfy6FFTVs892WuP)

  Then I'd set all 5 steps' parent to the hub (5 writes). Do you want the steps renumbered 1-5 as well?

## B + E. Untyped, temp, empty and untitled entries (12 entries)

| Entry | Problem | Proposal |
|---|---|---|
| `Linux System Health Check` (rec1EzZvHScsSLv2PuR) | no type, 45 chars (one smartctl line) | set type to **Linux - Commands** |
| `Macbook Pro --- llama.cpp` (recGC3HKV6Kph75eqLg) | no type | set type to **general - knowledge** (no local-LLM type exists, and one entry doesn't justify a new one) |
| `UMD-892 ...` (recrpK1QfQC40d4eTEX) | no type | set type to **missav_meta_Mary_Tachibana** |
| JUR-629 empty copy (rech2Hpkg0pyay4Od4N) | no type, empty | archive (see F) |
| untitled (recb3YY9ZHA4xDN8Ygv) | no title | set title to "JUQ-324 Married Woman Personal Trainer Reverse NTR Ryo Ayumi" (taken from its body) |
| `temp` (recKeYy9bxAXG9F3h2K) | the title says nothing. It's actually a draft message asking the Meta business owner to approve Okta SSO | retitle "Okta SSO for Meta Business - Owner Request" and move to general - knowledge. Or archive it if the message has been sent. |
| `K3S - Migration setup script - TEMP` (recukPJGr1EjdCI21G1) | real 5.7k-char guide sitting in TEMP | keep it: retitle "K3S - Migration to Another Machine" and set type to **k3s - operation** |
| `env for AARON AI uat - delete later` (recg1X28d8erjzUJB1m) | the title says to delete it, and the body is a full .env with secrets | archive (soft, reversible) unless that UAT is still live |
| `Wrenai- docker-compose` (recn1oxlt0DlhDmfya5) | the body is just 10 characters, **and it looks like a password**, not a compose file (the secrets check missed it) | retitle "Wrenai - login" and move to **credential_login**. Or paste in the real compose file. |
| `mdadm Raid management` (rec0D0Tt2ufpVmyAXyg) | empty | fill it in (do you have the notes?) or archive it |

If the two TEMP entries get moved or archived, the **TEMP - Records** type ends up empty.

## A. Type tree (42 types)

- **No type has a description.** I can draft one line for each of the 42 for you to review before I write them.
- **3 new parent types:** `deployment` (6 children), `database` (5 children), `search engine` (2 children).
- **Existing parents that need children attached:**
  - `credentials` ← AI Gateway API KEy, credential_apikey, credential_login, credential_access_token, credential_sshkey
  - `missav_meta` ← Mary_Tachibana, Meg_Fujiura, Morinaga_Iroha, NTR (Ayumi_Ryo is already under it)
- **Rename 4 types:**
  - `Career` → "career - knowledge"
  - `Python related` → "development tools - python"
  - `WOW` → "gaming - wow"
  - `AI Gateway API KEy` → "credential_ai_gateway" (it has no entries, so this could instead just go under credentials)
- **Empty types:** AI Gateway API KEy, credential_access_token, credential_sshkey, family - knowledge. I'd leave these as planned types (this skill never deletes types).

## For information only

- **G. Secrets in non-credential entries: 17**, mostly docker-compose and deployment guides with passwords inline. The biggest are Plane - docker-compose (44 hits), Onyx (19), Docker Compose Complete Template (13), Private Docker Registry (12), Old Micro-server (10) and K3s-Infras (6). This is allowed under your readability decision (CR-1), so I'd leave them unless you want any moved to a credential type.
- **H. Links:** none of the 133 entries is linked to a goal, project or task. One has a parent, and none have "see also" links. Fixing F and D adds the first ones; the rest builds up as projects use entries.

**Suggested order:** F, then C + D, then B + E, then A. That's roughly 25 entry writes plus the type changes. After each group I'll re-run the audit and give you before/after counts. Tell me which groups to go ahead with, and your choice on the open questions (UAT env, mdadm, the Okta draft, Wrenai, step renumbering).
