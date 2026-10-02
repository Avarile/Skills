**Decisions needed**
1. Evidence for the log line. The skill requires a dated `## Log` entry with evidence (commit, test result, link or your word). Is "Wave 1 cutover is done and validated" your word, or is there something to cite?
2. Please confirm the state first. The task is currently `backlog`, with no `started_at`, in a project that is still `preparing`. Marking it finished would skip `in-progress`. Is that intended?

**What I found**
- k3s Migration (`recNEeZTYI9Z2KQyvXm`, project status `preparing`) has one match: `recfnikTFWJOSLkWPAE` "Step 06 [DO] Wave 1 migration and cutover". It is `backlog`, priority important, due 2026-11-11, with no start or finish date.

**Enum note**
- "finished-validating" (hyphen) is the *project* spelling. The task value is `finished_validating` (underscore). A wrong spelling would silently clear the field, so I would write the underscore form and read it back.

**Nothing written** (read-only run). On your confirmation I would set `progress = finished_validating` and `finished_at = 2026-10-03`. I would also set `started_at = 2026-10-03` if you want it recorded, and append a dated `## Log` line with your evidence. I would not change the project status. If every open task ends up finished, I would only suggest advancing it.
