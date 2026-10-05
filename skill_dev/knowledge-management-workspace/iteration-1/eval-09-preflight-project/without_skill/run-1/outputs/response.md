**Short answer: nothing in your knowledge base fits this project yet, so I wouldn't link anything for now.**

**What I checked**
- **The project:** "Game Design Nebula-of-Cybernetics" (#33, `recjwiijjBO4wKg2XAl`) is in progress, led by you, and has 11 tasks. Its `refer_knowledge` field is empty, and so is `refer_knowledge` on the tasks I opened ("Clean up existing schemas…" and "Define lore, factions and world identity").
- **The knowledge base:** I read the titles of all 133 entries in `knowledges` and all 42 types in `knowledge_type`.
  - Nothing covers game design, Nebula of Cybernetics, combat or ship rules, lore, or the game's schema and verifier tooling.
  - Most entries are about infrastructure and DevOps (Docker, K3s, databases, Caddy/Nginx, new-server setup), plus credentials and personal notes.

**Closest matches, and why I'd still skip them**
| Entry | Type | Why it doesn't fit |
|---|---|---|
| World of Warcraft Deployment / Install script of install AzerothCore on Debian 13 / Azerothcore Commands | WOW | Running a private game server, not designing a game |
| Sony Game Account | credentials | A login, not design knowledge |
| Python, Linux and tooling notes | various | General tooling, nothing specific to this project |

**Where this project's knowledge actually lives**
The task write-ups show the design work is in a git repo, not in the knowledge base. For example:
- `GamePlay/lore_specification.md`
- `tools/lore_tables.py` and `verify_lore.py`
- `verify_naming.py`
- `Reference/lore.ts`
- `ship.interface` / `player.interface`

**Options**
1. **Leave it unlinked (my recommendation for now).** Linking any of the entries above would only add noise.
2. **Give the game a home in the knowledge base.** I'd add a knowledge type `game design - nebula of cybernetics`, and under it a hub entry "Nebula of Cybernetics - Design Doc Index" listing the repo's docs and verifiers. Then I'd link that entry to the project. Later, settled decisions (the 4 authorities, the 4 hostile factions, the round-vs-turn naming rule) could go in as their own entries. To do this I need:
   - your go-ahead
   - the repo path or URL

I haven't changed anything. Do you want option 2? If so, send me the repo path.
