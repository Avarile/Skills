I audited the `knowledges` table (133 entries) and the `knowledge_type` table (42 types) in your data-centre base. I haven't changed anything yet. Here's what needs cleaning up, most urgent first.

## 1. Plaintext secrets (urgent)

About 30 entries contain live credentials in plain text. Any tool or AI session that reads the knowledge base can see them.

**Stored as credentials:**
- #42 **Laptop sshkey**: two full OpenSSH **private keys** (MacBook Pro M2, ROG G14)
- #134 **Google Account Credential**: your Google password
- #52 **iCloud Account**: Gmail password plus a Gmail SMTP/IMAP app password
- #178 **MyGov Credentials**: your MyGov login **and your wife's** (her email and password)
- #132 Apple Account, #71 Sony Game Account
- #70 OPENAI API (2 keys), #9 AI Gateway APIKEY, #133 Cybernetics-CRM API Key (a JWT that expires in 2126), #65 Cybernetics api-token, #64 Self-host Plane (MCP access token)
- #3 **"Wrenai- docker-compose"**: no compose file at all, just a 10-character string that looks like a password

**Inside how-to docs:**
- #130 **K3s-Infras**: about 15 secrets covering Postgres, Redis, MySQL root and app users, MongoDB, RabbitMQ, MinIO keys, the Meilisearch master key, per-app DB passwords and the **Vaultwarden admin token**
- #10 **"env for AARON AI uat - delete later"**: a full .env with AI Gateway, ElevenLabs and other keys
- Compose files and scripts with hard-coded passwords: #1 Plane, #2 Onyx, #15, #16, #22, #23, #32, #53, #7/#40 (the `devops` sudo user password), #13 Clickhouse, #26 Qdrant, #57 WoW, #67 vaultwarden tutorial

**Password reuse:** the password on your Google account (#134) shares a stem with DB and service passwords in 7 infra docs (#13, #18, #22, #26, #53, #57, #67). Sony (#71) uses a close variant, and the MyGov/Gmail passwords share another stem. If any one of those leaks, it points straight at your Google account.

**Recommendation:** you already self-host Vaultwarden, so move all of these into it. Then replace each KB entry's content with a pointer (for example "Stored in Vaultwarden → Infra/K3s") and keep only the non-secret parts (endpoints, ports, notes). Rotate the Google password first. Also rotate any key that has sat here for months: the OpenAI keys, AI Gateway, ElevenLabs, the Cybernetics tokens and the K3s service passwords. Soft-deleting wouldn't fix this, because the secret stays in the row. The content has to be overwritten or the row hard-deleted.

## 2. Content that isn't knowledge: 55 adult-video bookmarks (41% of the KB)

Entries #72–#127 (except #89) are missav.ai links with titles and tags, filed under 6 types: `missav_meta`, `missav_meta_Ayumi_Ryo`, `missav_meta_NTR`, `missav_meta_Mary_Tachibana`, `missav_meta_Meg_Fujiura` and `missav_meta_Morinaga_Iroha`. That's your call, but they swamp search and listings for real knowledge, and every agent that queries the KB pulls them in. Options:
- **(a)** move them to a dedicated table (e.g. `media_bookmarks`), or a separate base, and delete them from `knowledges`
- **(b)** export them and delete them
- **(c)** leave them, but at least fix the problems below

Problems inside this set: #121 and #126 are the same title (JUR-330) with different links, and #96 and #97 are duplicates (JUR-629). #96 is also empty and has no type. #80 has no title. #110 has no type. #72's title is a tag string ("…big_breast big_ass madonna"), and #73 is parented under it, which is the only `knowledge_parent` link in the whole KB.

## 3. Duplicates and mislabelled entries

- **Swapped titles:** #6 "new-server-ubuntu-26.04 => **security**" actually contains the Node/NVM install, and #7 "…=> **basic app**" contains the security hardening.
- **Exact duplicate:** #40 "New Server Init - Step 1 security" is identical to #7. #40 is also filed under `deployment - web server` instead of `deployment - new server`.
- **Near duplicate:** #41 "New Server Init - Step 2 basic deps for nodejs" is about 84% the same as #6.
- **Two parallel new-server series:** the older Ubuntu 22.04 set (#31–#34) and the newer 26.04 set (#6/#7/#40/#41). Infra compose also overlaps across #8, #22 and #32, with #53 "Old Micro-server". I'd consolidate into one current series and mark the 22.04 set as superseded.
- **System-info notes split three ways:** #68 Terminal Commands for System Info (macOS), #135 Linux System Check Commands and #69 Linux System Health Check (a stub). These could be merged into one or two.
- **Editor notes split:** #59 Lazyvim setup (filed under `general - knowledge`) and #35 Neovim config (`development tools - nvim`).

## 4. Empty, stub or unfinished entries

- #61 **mdadm Raid management**: completely empty
- #3 Wrenai docker-compose: no content apart from the password-like string (see section 1)
- #69 Linux System Health Check: one command and a dangling "#"
- #38 Gitea: 3 lines, cut off at "username"
- #9 AI Gateway APIKEY: a bare key with no context
- #20 Database Safety – SSH Tunnel: 2 broken Obsidian image embeds (`![[Pasted image …]]`)
- #129 Python packages and #54 debian firewall: pasted AI chat filler such as "Want me to drop this in a file…?"
- #49 **"temp"**: not knowledge; it's a draft email about Okta/Meta SSO
- #43 "K3S - Migration setup script - TEMP" and #10 "…delete later" both say in their titles that they're temporary

## 5. Taxonomy (`knowledge_type`)

- **Empty types:** `family - knowledge`, `AI Gateway API KEy`, `credential_access_token`, `credential_sshkey`
- **Type named after a secret:** `AI Gateway API KEy` holds no entries. The actual key (#9) is filed under `credentials`. I'd delete this type.
- **Two credential schemes in use:** the old `credentials` type (8 entries) and the newer `credential_apikey/login/access_token/sshkey` types. Proposed re-filing:
  - #9 goes to `credential_apikey`
  - #42 goes to `credential_sshkey`
  - #64 and #65 go to `credential_access_token`
  - #134, #52, #71 and #178 go to `credential_login`
  - #67 "vaultwarden - tutorial" is a how-to, not a credential
  - after that, retire `credentials`
- **Untyped entries:** #69, #131 (Macbook Pro llama.cpp), #96, #110
- **Inconsistent naming:** most types follow `category - topic` in lower case. These don't: `WOW`, `Career`, `Python related`, `TUI control - Tmux`, `Infra - services`, `Linux - Commands`, `TEMP - Records`. Related topics are also split: `deployment - k8s`, `k3s - operation` and `Infra - services`; `deployment - caddy` and `deployment - web server`. Around 20 types hold only one entry each.
- **Schema oddities:**
  - `knowledge_type` has an unused `credentials` text field that's empty everywhere and would be a bad place for secrets anyway.
  - `knowledge_type` has two disconnected hierarchy fields: `parent_type` (one-way, used once) and `child_types` (its paired field is missing).
  - The `related_knowledge` link on `knowledges` points at a paired field that isn't in the schema, and no entry uses it.
- **Title typos:** "K3S initi**te**", "MacOS Firew**a**l", "Tailscal**ing**", "AI Gateway API KE**y**", "Wrenai**-** docker-compose"

## 6. Housekeeping notes

- Every entry is `is_active = true` and none has `deleted_at` set, so the soft-delete fields are unused. Auto-numbers 48, 58, 62, 66 and 136–177 are missing, which means rows have been hard-deleted before.
- Except for that one parent link (#73 under #72), no entry uses `knowledge_parent` or `related_knowledge`. The KB is completely flat.

---

## What I'd do, if you say go

I haven't run any of this. Tell me which batches to apply:

1. **Secrets:** once you confirm the values are in Vaultwarden, overwrite the content of the about 30 entries above with "stored in Vaultwarden → <item>" plus any non-secret notes. Strip the hard-coded passwords from the compose and script docs (replace them with `${VAR}` placeholders). Then rotate the Google password and the API keys yourself.
2. **Adult bookmarks:** choose (a) move to a new table, (b) export and delete, or (c) leave as is.
3. **Duplicates:**
   - swap the titles of #6 and #7
   - soft-delete #40 and #41
   - delete #96 and one of #121/#126
4. **Stubs and temp entries:**
   - soft-delete #61 and #49
   - #10 "delete later": hard-delete it (it's full of keys)
   - fill in or delete #3, #38 and #69
5. **Taxonomy:**
   - re-file the 8 old `credentials` entries
   - type the 4 untyped entries
   - move #40/#59 to the right types
   - delete the `AI Gateway API KEy` and `family - knowledge` types
   - rename the inconsistent types (I'll propose names first)
   - fix the title typos

One question before batch 1: are those credentials already in Vaultwarden, or should I export them to a file you can import first?
