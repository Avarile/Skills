# Cybernetics Skill — Phase 3: Interfaces Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the two audience-facing surfaces on top of the Phase 2 command set — the interactive `cyb ui` REPL for the human, and `SKILL.md` plus references for the agent — then prove the whole thing against the live instance with integration tests.

**Architecture:** The REPL contains no API logic. It tokenises a line, translates it into the same argv the CLI already accepts, and calls `main()`. That keeps one tested code path for both audiences and makes the REPL's behaviour unit-testable without a terminal. `SKILL.md` follows three-level progressive disclosure so a triggered skill costs ~3KB, with references loaded only on demand.

**Tech Stack:** Node 24, ESM, zero runtime dependencies. `node:readline` for the REPL, `node:test` for tests.

**Spec:** `docs/superpowers/specs/2026-08-17-cybernetics-skill-design.md`

**Depends on:** Phase 1 (Tasks 1–7) and Phase 2 (Tasks 8–15) complete.

## Global Constraints

- Zero runtime dependencies. Built-in modules only.
- Node >= 24. ESM only. All source files `.mjs`. Every file under 500 lines.
- The REPL must not duplicate command logic — it translates to argv and delegates to `main()`.
- `SKILL.md` frontmatter carries exactly two fields: `name` (max 64 chars) and `description` (max 1024 chars, stating both what and when).
- The API token never appears in `SKILL.md`, `README.md`, references, tests, or any committed file.
- Integration tests run only when `CYB_TOKEN` is set **and** `CYB_RUN_INTEGRATION=1`; otherwise they skip so a token-less run stays green.
- Integration tests create a scratch project and delete it in a `finally` block, exactly as the design probe did.
- Exit codes: `0` ok, `1` general, `2` refused, `3` not found, `4` auth, `5` rate limited.

---

### Task 16: Interactive REPL

**Files:**
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (extract the `dispatch` seam, add `positionals` metadata, add the `ui` group)
- Create: `.claude/skills/cybernetics/src/repl.mjs`
- Test: `.claude/skills/cybernetics/tests/cli.test.mjs` (seam), `.claude/skills/cybernetics/tests/repl.test.mjs`

**Required pre-work, added after Phase 2's final review (do this BEFORE writing `repl.mjs`):**

Phase 2's final review verified the command surface is re-entrant — `main()` was called five
times in one process with interleaved failures and leaked no state — but flagged three
changes to make first. They are not optional; retrofitting them after the REPL exists is
strictly harder.

**1. Extract a `dispatch` seam from `main()`.** Today `main()` parses argv, builds the
context, and dispatches in one function. A REPL calling `main()` per line would re-read
`config.json` and `cache.json` from disk, rebuild `Client` and `Resolver`, and rewrite the
whole cache on every `save()` — once per keystroke-completed line. Split it:

```js
export function parseInvocation(argv)        // → { group, action, definition, values, positionals }
export async function dispatch(invocation, ctx)
export async function main(argv, deps)       // one-shot wrapper: parse → buildContext → dispatch
```

`main`'s external behaviour must not change — same exit codes, same error envelope, same
`--help` handling. Every existing `cli.mjs` test must still pass untouched.

This also gives the REPL a **session-lifetime `Client`**, which keeps `remaining`/`resetAt`
across lines. That is the budget awareness the spec asks for and the one thing the per-call
design cannot provide — it partly closes a deferred finding, so do not skip it.

**2. Add `positionals` metadata to `REGISTRY` entries.** `renderHelp` emits prose with no
argument syntax, so a REPL completer would have to re-derive shapes `REGISTRY` almost knows.
Add a declarative field per action — `['project']`, `['itemRef', 'state']`,
`['query', 'project?']` — and have `renderHelp` render it. Note `search` is the only action
whose `positionals[0]` is **not** a project ref; a REPL that injects the current project
positionally will get that one wrong unless the metadata says so.

**3. Completer warm-up — a decision, not a discovery.** The spec says completion sources
come from the resolver cache "so it costs no extra calls". But `sync` populates `projects`,
`stateList` and `members` while leaving `labels` and `items` empty, so TAB completion for
labels and item ids has nothing to offer immediately after the most natural warm-up.

**Ruling (controller):** the REPL's `cd <PROJECT>` warms that project's labels and items,
rather than making `sync` fetch labels for every project. `cd` is an explicit, user-initiated
context switch where one or two requests are expected and affordable; making `sync` pay
1-more-request-per-project globally taxes every user for a REPL-only benefit. The completer
itself must **never** issue a request — if the cache is cold it returns no suggestions.

**Interfaces:**
- Consumes: `main` from `src/cli.mjs`, the cache shape from `src/cache.mjs`
- Produces:
  - `tokenize(line) -> string[]` — quote-aware splitter
  - `translate(tokens, state) -> { argv } | { setProject } | { exit } | { help } | { error }`
  - `makeCompleter(state, cache) -> (line) => [string[], string]`
  - `startRepl(deps) -> Promise<number>`
  - `REPL_HELP: string`

REPL command mapping, where `state.project` is the current project key:

| Typed | Translates to |
|---|---|
| `ls` | `item list <project>` |
| `ls --state todo` | `item list <project> --state todo` |
| `open 42` | `item show <project>-42` |
| `new "Fix auth"` | `item create <project> --name "Fix auth"` |
| `mv 42 "In Progress"` | `item move <project>-42 "In Progress"` |
| `assign 42 avarile` | `item assign <project>-42 avarile` |
| `board` | `board <project>` |
| `cd CYB` | sets `state.project`, no API call |
| `help` | prints `REPL_HELP` |
| `exit` / `quit` | ends the session |

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/repl.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tokenize, translate, makeCompleter, REPL_HELP } from '../src/repl.mjs';
import { emptyCache } from '../src/cache.mjs';

test('tokenize splits on whitespace', () => {
  assert.deepEqual(tokenize('ls --state todo'), ['ls', '--state', 'todo']);
});

test('tokenize keeps double-quoted phrases together', () => {
  assert.deepEqual(tokenize('mv 42 "In Progress"'), ['mv', '42', 'In Progress']);
});

test('tokenize keeps single-quoted phrases together', () => {
  assert.deepEqual(tokenize("new 'Fix the auth bug'"), ['new', 'Fix the auth bug']);
});

test('tokenize collapses repeated whitespace and trims', () => {
  assert.deepEqual(tokenize('  ls   --json  '), ['ls', '--json']);
});

test('tokenize returns an empty array for a blank line', () => {
  assert.deepEqual(tokenize('   '), []);
});

test('ls translates to item list for the current project', () => {
  assert.deepEqual(translate(['ls'], { project: 'CYB' }), { argv: ['item', 'list', 'CYB'] });
});

test('ls passes trailing flags through', () => {
  assert.deepEqual(translate(['ls', '--state', 'todo'], { project: 'CYB' }), {
    argv: ['item', 'list', 'CYB', '--state', 'todo'],
  });
});

test('open builds a CYB-42 reference', () => {
  assert.deepEqual(translate(['open', '42'], { project: 'CYB' }), {
    argv: ['item', 'show', 'CYB-42'],
  });
});

test('open accepts a full reference unchanged', () => {
  assert.deepEqual(translate(['open', 'OTHER-7'], { project: 'CYB' }), {
    argv: ['item', 'show', 'OTHER-7'],
  });
});

test('mv translates to item move', () => {
  assert.deepEqual(translate(['mv', '42', 'In Progress'], { project: 'CYB' }), {
    argv: ['item', 'move', 'CYB-42', 'In Progress'],
  });
});

test('new translates to item create with --name', () => {
  assert.deepEqual(translate(['new', 'Fix auth'], { project: 'CYB' }), {
    argv: ['item', 'create', 'CYB', '--name', 'Fix auth'],
  });
});

test('assign translates to item assign', () => {
  assert.deepEqual(translate(['assign', '42', 'avarile'], { project: 'CYB' }), {
    argv: ['item', 'assign', 'CYB-42', 'avarile'],
  });
});

test('board translates to the board command', () => {
  assert.deepEqual(translate(['board'], { project: 'CYB' }), { argv: ['board', 'CYB'] });
});

test('cd requests a project change without an argv', () => {
  assert.deepEqual(translate(['cd', 'OTHER'], { project: 'CYB' }), { setProject: 'OTHER' });
});

test('exit and quit both end the session', () => {
  assert.deepEqual(translate(['exit'], { project: 'CYB' }), { exit: true });
  assert.deepEqual(translate(['quit'], { project: 'CYB' }), { exit: true });
});

test('help returns the help marker', () => {
  assert.deepEqual(translate(['help'], { project: 'CYB' }), { help: true });
});

test('an unknown verb returns a descriptive error', () => {
  const result = translate(['frobnicate'], { project: 'CYB' });
  assert.match(result.error, /unknown command: frobnicate/);
});

test('a command needing a project errors when none is selected', () => {
  const result = translate(['ls'], { project: null });
  assert.match(result.error, /no project selected/);
});

test('open without an argument errors', () => {
  assert.match(translate(['open'], { project: 'CYB' }).error, /needs a work item/);
});

test('REPL_HELP documents every supported verb', () => {
  for (const verb of ['ls', 'open', 'new', 'mv', 'assign', 'cd', 'board', 'help', 'exit']) {
    assert.match(REPL_HELP, new RegExp(`\\b${verb}\\b`));
  }
});

test('completer suggests verbs at the start of a line', () => {
  const [hits] = makeCompleter({ project: 'CYB' }, emptyCache('cybernetics'))('bo');
  assert.ok(hits.includes('board'));
});

test('completer suggests state names from the cache after mv', () => {
  const cache = emptyCache('cybernetics');
  cache.projects.CYB = { id: 'p1', name: 'Core', fetchedAt: new Date().toISOString() };
  cache.byProject.p1 = {
    states: { backlog: 's1', 'in progress': 's2' },
    stateList: [{ id: 's1', name: 'Backlog', group: 'backlog' }, { id: 's2', name: 'In Progress', group: 'started' }],
    labels: {}, members: {}, items: {}, statesFetchedAt: new Date().toISOString(),
  };
  const [hits] = makeCompleter({ project: 'CYB' }, cache)('mv 42 In');
  assert.ok(hits.some((h) => /In Progress/.test(h)));
});

test('completer returns no hits rather than throwing on a cold cache', () => {
  const [hits] = makeCompleter({ project: 'CYB' }, emptyCache('cybernetics'))('mv 42 In');
  assert.deepEqual(hits, []);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/repl.test.mjs`
Expected: FAIL — `Cannot find module '../src/repl.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/repl.mjs`:

```js
import readline from 'node:readline';
import { loadConfig, CONFIG_PATH } from './config.mjs';
import { loadCache, CACHE_PATH } from './cache.mjs';

export const REPL_HELP = [
  'Commands:',
  '  ls [flags]            list work items in the current project',
  '  open <n|REF>          show one work item',
  '  new "<name>"          create a work item',
  '  mv <n> "<state>"      move a work item to a state',
  '  assign <n> <who>      assign a work item',
  '  board                 kanban summary of the current project',
  '  cd <PROJECT>          switch the current project',
  '  help                  show this help',
  '  exit                  leave the session',
].join('\n');

const VERBS = ['ls', 'open', 'new', 'mv', 'assign', 'board', 'cd', 'help', 'exit', 'quit'];

export function tokenize(line) {
  const tokens = [];
  const pattern = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let match;
  while ((match = pattern.exec(line)) !== null) {
    tokens.push(match[1] ?? match[2] ?? match[3]);
  }
  return tokens;
}

function ref(state, value) {
  return /^\d+$/.test(value) ? `${state.project}-${value}` : value;
}

export function translate(tokens, state) {
  if (!tokens.length) return { argv: null };

  const [verb, ...rest] = tokens;

  if (verb === 'exit' || verb === 'quit') return { exit: true };
  if (verb === 'help') return { help: true };

  if (verb === 'cd') {
    if (!rest[0]) return { error: 'cd needs a project, e.g. cd CYB' };
    return { setProject: rest[0].toUpperCase() };
  }

  if (!VERBS.includes(verb)) {
    return { error: `unknown command: ${verb} (try: help)` };
  }

  if (!state.project) {
    return { error: 'no project selected — use: cd CYB' };
  }

  switch (verb) {
    case 'ls':
      return { argv: ['item', 'list', state.project, ...rest] };

    case 'board':
      return { argv: ['board', state.project, ...rest] };

    case 'open':
      if (!rest[0]) return { error: 'open needs a work item, e.g. open 42' };
      return { argv: ['item', 'show', ref(state, rest[0]), ...rest.slice(1)] };

    case 'new':
      if (!rest[0]) return { error: 'new needs a name, e.g. new "Fix auth"' };
      return { argv: ['item', 'create', state.project, '--name', rest[0], ...rest.slice(1)] };

    case 'mv':
      if (!rest[0] || !rest[1]) return { error: 'mv needs a work item and a state, e.g. mv 42 "In Progress"' };
      return { argv: ['item', 'move', ref(state, rest[0]), rest[1], ...rest.slice(2)] };

    case 'assign':
      if (!rest[0] || !rest[1]) return { error: 'assign needs a work item and a member, e.g. assign 42 avarile' };
      return { argv: ['item', 'assign', ref(state, rest[0]), rest[1], ...rest.slice(2)] };

    default:
      return { error: `unknown command: ${verb} (try: help)` };
  }
}

export function makeCompleter(state, cache) {
  return (line) => {
    const tokens = tokenize(line);
    const trailingSpace = /\s$/.test(line);

    if (tokens.length <= 1 && !trailingSpace) {
      const prefix = tokens[0] ?? '';
      return [VERBS.filter((v) => v.startsWith(prefix)), prefix];
    }

    const verb = tokens[0];
    const partial = trailingSpace ? '' : (tokens.at(-1) ?? '');

    const projectId = cache.projects?.[state.project]?.id;
    const bucket = projectId ? cache.byProject?.[projectId] : null;

    if (verb === 'mv') {
      const names = (bucket?.stateList ?? []).map((s) => s.name);
      return [names.filter((n) => n.toLowerCase().startsWith(partial.toLowerCase())), partial];
    }

    if (verb === 'assign') {
      const names = Object.keys(cache.members ?? {});
      return [names.filter((n) => n.startsWith(partial.toLowerCase())), partial];
    }

    if (verb === 'cd') {
      const keys = Object.keys(cache.projects ?? {});
      return [keys.filter((k) => k.startsWith(partial.toUpperCase())), partial];
    }

    if (verb === 'open' || verb === 'mv') {
      const seqs = Object.keys(bucket?.items ?? {});
      return [seqs.filter((s) => s.startsWith(partial)), partial];
    }

    return [[], partial];
  };
}

export async function startRepl(deps = {}) {
  const { main } = await import('./cli.mjs');

  const env = deps.env ?? process.env;
  const cwd = deps.cwd ?? process.cwd();
  const config = loadConfig({ env, cwd, configPath: deps.configPath ?? CONFIG_PATH });
  const cache = loadCache({ path: deps.cachePath ?? CACHE_PATH, workspace: config.workspace });

  const state = { project: config.defaultProject ?? Object.keys(cache.projects ?? {})[0] ?? null };

  const input = deps.input ?? process.stdin;
  const output = deps.output ?? process.stdout;

  const rl = readline.createInterface({
    input,
    output,
    prompt: '',
    completer: makeCompleter(state, cache),
  });

  const setPrompt = () => rl.setPrompt(`cyb:${state.project ?? '-'}> `);
  setPrompt();

  output.write(`${REPL_HELP}\n\n`);
  rl.prompt();

  for await (const line of rl) {
    const result = translate(tokenize(line), state);

    if (result.exit) break;

    if (result.help) {
      output.write(`${REPL_HELP}\n`);
    } else if (result.error) {
      output.write(`error: ${result.error}\n`);
    } else if (result.setProject) {
      state.project = result.setProject;
      setPrompt();
    } else if (result.argv) {
      await main(result.argv, deps);
    }

    rl.prompt();
  }

  rl.close();
  return 0;
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs` — register the `ui` group. Because the REPL builds its own context per command, its handler bypasses `buildContext`; add it as a special case at the top of `main`, immediately after the top-level help check:

```js
    if (group === 'ui') {
      const { startRepl } = await import('./repl.mjs');
      return await startRepl(deps);
    }
```

And add a registry entry so `cyb --help` lists it:

```js
  ui: {
    __default: { summary: 'Interactive session with a persistent project context', options: {}, handler: null },
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/repl.test.mjs`
Expected: PASS — 23 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/repl.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/repl.test.mjs
git commit -m "feat(cyb): add interactive REPL that delegates to the CLI router"
```

---

### Task 17: Skill Documentation

**Files:**
- Create: `.claude/skills/cybernetics/SKILL.md`
- Create: `.claude/skills/cybernetics/README.md`
- Create: `.claude/skills/cybernetics/references/api-surface.md`
- Create: `.claude/skills/cybernetics/references/recipes.md`
- Create: `.claude/skills/cybernetics/references/troubleshooting.md`
- Test: `.claude/skills/cybernetics/tests/skill-doc.test.mjs`

**Interfaces:**
- Consumes: the finished command surface from Phase 2
- Produces: the agent-facing entry point. No code exports.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/skill-doc.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SKILL = join(ROOT, 'SKILL.md');

function frontmatter() {
  const text = readFileSync(SKILL, 'utf8');
  const match = /^---\n([\s\S]*?)\n---/.exec(text);
  assert.ok(match, 'SKILL.md must open with YAML frontmatter');
  const fields = {};
  for (const line of match[1].split('\n')) {
    const eq = line.indexOf(':');
    if (eq === -1) continue;
    fields[line.slice(0, eq).trim()] = line.slice(eq + 1).trim().replace(/^"|"$/g, '');
  }
  return fields;
}

test('SKILL.md exists', () => {
  assert.ok(existsSync(SKILL));
});

test('frontmatter has exactly name and description', () => {
  assert.deepEqual(Object.keys(frontmatter()).sort(), ['description', 'name']);
});

test('name is within 64 characters', () => {
  assert.ok(frontmatter().name.length <= 64);
});

test('description is within 1024 characters and states when to use the skill', () => {
  const description = frontmatter().description;
  assert.ok(description.length <= 1024);
  assert.match(description, /use when/i);
});

test('description carries the trigger words from the spec', () => {
  const description = frontmatter().description.toLowerCase();
  for (const word of ['cybernetics', 'plane', 'task', 'projects.avarile.com']) {
    assert.ok(description.includes(word), `description missing trigger word: ${word}`);
  }
});

test('no committed doc contains a live API token', () => {
  for (const file of ['SKILL.md', 'README.md', 'references/api-surface.md', 'references/recipes.md', 'references/troubleshooting.md']) {
    const text = readFileSync(join(ROOT, file), 'utf8');
    assert.ok(!/plane_api_[a-f0-9]{16,}/.test(text), `${file} contains what looks like a real token`);
  }
});

test('SKILL.md body stays lean for progressive disclosure', () => {
  const body = readFileSync(SKILL, 'utf8').replace(/^---[\s\S]*?---/, '');
  assert.ok(body.length < 6000, `SKILL.md body is ${body.length} bytes; keep it under 6000`);
});

test('SKILL.md states the safety rule and the json contract', () => {
  const text = readFileSync(SKILL, 'utf8');
  assert.match(text, /--yes/);
  assert.match(text, /--json/);
  assert.match(text, /confirm/i);
});

test('reference files exist', () => {
  for (const file of ['references/api-surface.md', 'references/recipes.md', 'references/troubleshooting.md']) {
    assert.ok(existsSync(join(ROOT, file)), `missing ${file}`);
  }
});

test('api-surface records the endpoints known to be absent', () => {
  const text = readFileSync(join(ROOT, 'references/api-surface.md'), 'utf8');
  for (const absent of ['estimates', 'attachments', 'sub-issues', 'issue-relation']) {
    assert.match(text, new RegExp(absent));
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/skill-doc.test.mjs`
Expected: FAIL — `ENOENT` for `SKILL.md`

- [ ] **Step 3: Write the documentation**

Create `.claude/skills/cybernetics/SKILL.md`:

```markdown
---
name: "Cybernetics Project Management"
description: "Manage projects, tasks and work items on the remote Cybernetics instance (a Plane fork at projects.avarile.com) through the zero-dependency cyb CLI. Use when asked to create, list, update, assign, move, comment on, or search project tasks and work items; to inspect a backlog, sprint, cycle or module; or whenever Cybernetics, projects.avarile.com, or Plane project management is mentioned."
---

# Cybernetics Project Management

Manage the remote Cybernetics instance through the `cyb` CLI. Never call the
API directly with curl — the CLI handles auth, UUID resolution, rate limiting
and pagination for you.

## Invocation

```bash
node .claude/skills/cybernetics/bin/cyb <group> <action> [options]
```

Check the connection first if anything looks wrong:

```bash
node .claude/skills/cybernetics/bin/cyb doctor
```

## Output contract

- Add `--json` whenever you intend to parse the result. Human tables are for people.
- Lists default to **30** items. Pass `--limit N` deliberately; the footer tells you how many were withheld.
- Errors go to stderr. Under `--json` they arrive as `{"error":{"code","message","hint"}}`.
- Exit codes: `0` ok · `1` general · `2` refused · `3` not found · `4` auth · `5` rate limited.

## The eight commands you will use most

```bash
cyb project list                                   # what projects exist
cyb item list CYB --json                           # the backlog
cyb item list CYB --state "In Progress" --json     # filtered
cyb item show CYB-42 --json                        # one work item
cyb item create CYB --name "Fix auth" --priority high
cyb item move CYB-42 "In Progress"                 # change status
cyb item assign CYB-42 avarile
cyb board CYB --json                               # everything, grouped by state
```

Work items are referenced as `<PROJECT>-<number>`, e.g. `CYB-42`. States,
labels and members are referenced by name, case-insensitively — the CLI
resolves them to UUIDs for you.

## Safety

`delete` on any resource requires `--yes`. **Confirm with the user before
passing it.** Without `--yes` the command prints what it would destroy and
exits 2 without calling the API. The same gate applies to bulk updates
touching more than 10 items.

## Staying inside the rate limit

The instance allows **60 requests per minute**. Do not loop over items issuing
one request each. Use the composite commands instead:

- `cyb board CYB` — the whole project grouped by state, in one pass
- `cyb my` — everything assigned to you
- `cyb search "auth" --project CYB` — name search

If a name lookup fails, the error lists the valid values. Read the hint rather
than guessing again.

## Deeper reference

- `references/api-surface.md` — which endpoints exist on this fork, and which return 404/402/403
- `references/recipes.md` — multi-step workflows (sprint setup, triage, status sweep)
- `references/troubleshooting.md` — what each exit code means and how to recover
```

Create `.claude/skills/cybernetics/references/api-surface.md`:

```markdown
# Cybernetics API Surface

Instance: `https://projects.avarile.com` · workspace `cybernetics` ·
Plane **v2.6.3**, `PLANE_COMMERCIAL`, self-managed.

Verified by live probe on 2026-08-17.

## Conventions

- Base path `/api/v1`. The bare `/api` prefix is the internal session-auth API and returns 401 for API keys.
- Auth header is `X-Api-Key`. `Authorization: Bearer` returns 401 — never use it.
- Rate limit 60 req/min, reported via `x-ratelimit-remaining` and `x-ratelimit-reset`.
- `?fields=a,b` projects the response down to those keys. Use it — it is the difference between 2 keys and 31 per record.
- `?expand=`, `?per_page=`, `?order_by=` are all accepted.

## Present

| Resource | Path |
|---|---|
| Projects | `/workspaces/{ws}/projects/` |
| Work items | `/workspaces/{ws}/projects/{id}/issues/` (also served at `/work-items/`) |
| States | `.../states/` |
| Labels | `.../labels/` |
| Members | `/workspaces/{ws}/members/` and `.../projects/{id}/members/` |
| Cycles | `.../cycles/`, items via `.../cycles/{id}/cycle-issues/` |
| Modules | `.../modules/`, items via `.../modules/{id}/module-issues/` |
| Comments | `.../issues/{id}/comments/` |
| Links | `.../issues/{id}/links/` |
| Activities | `.../issues/{id}/activities/` |
| Intake | `.../intake-issues/` (present; no command yet) |
| Pages | `/workspaces/{ws}/pages/` |

## Absent — returns 404, never call

`estimates`, `views`, `issue-properties`, `archived-issues`, `attachments`,
`sub-issues`, `issue-relation`, `inbox-issues`.

Sub-items are expressed through the `parent` field on a work item, not through
a `sub-issues` endpoint.

## Gated

| Resource | Status | Meaning |
|---|---|---|
| `issue-types` | 402 | not licensed on this instance |
| `initiatives` | 403 | not available to this workspace |
| `teamspaces` | 403 | not available to this workspace |

## Field notes

- Work items carry `sequence_id`, which is what makes `CYB-42` references possible.
- Default states are Backlog (`backlog`), Todo (`unstarted`), In Progress (`started`), Done (`completed`), Cancelled (`cancelled`).
- `priority` is a strict enum: `urgent`, `high`, `medium`, `low`, `none`. Anything else returns 400.
- Create/update payload keys: `name`, `description_html`, `state`, `assignees` (array), `labels` (array), `parent`, `priority`, `target_date`, `start_date`.
- Project identifiers are capped at 10 characters on this instance.

Run `cyb doctor` to re-probe; the fork may drift from this table.
```

Create `.claude/skills/cybernetics/references/recipes.md`:

```markdown
# Recipes

All examples assume `cyb` resolves to `node .claude/skills/cybernetics/bin/cyb`.

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
cyb board CYB               # confirm placement
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
than five, and the 60/min budget is shared with everything else.

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
server-side search. Narrow with `--project` rather than raising the cap.

## Clean up (destructive)

Always confirm with the user before running these.

```bash
cyb item delete CYB-42          # exits 2, shows what it would delete
cyb item delete CYB-42 --yes    # actually deletes
```
```

Create `.claude/skills/cybernetics/references/troubleshooting.md`:

```markdown
# Troubleshooting

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | success | — |
| 1 | general error | read the message; usually a missing or malformed flag |
| 2 | refused by the safety gate | confirm with the user, then add `--yes` |
| 3 | not found / unresolvable | the hint lists valid values — use one of them |
| 4 | auth failure | token missing, wrong or revoked; run `cyb doctor` |
| 5 | rate limited | 60 req/min exhausted; wait for the reset, then use composite commands |

## "no API token configured" (exit 4)

Precedence is `CYB_TOKEN` env var, then `~/.cybernetics/config.json`, then a
gitignored `.env` in the working directory. Set one:

```bash
export CYB_TOKEN='<your token>'
cyb doctor
```

To persist it outside the repo:

```bash
cyb init      # writes ~/.cybernetics/config.json at mode 0600
```

Never commit a token. This repository is public.

## "no such state" / "no such label" / "no such member" (exit 3)

The hint lists valid values and suggests the nearest match. Names are matched
case-insensitively. If the value was created moments ago in the web UI, the
cache may be stale:

```bash
cyb sync
```

## "no such project" with an empty list

The workspace may genuinely have no projects. Create one:

```bash
cyb project create --name "Cybernetics Core" --identifier CYB
```

Identifiers are capped at 10 characters.

## Rate limited (exit 5)

The client already waits for the reset window and retries. Repeated hits mean
the access pattern is wrong — you are probably looping. Replace the loop with
`cyb board`, `cyb my`, or a single `cyb item list --limit N`.

## Stale results

The resolver caches project, state, label and member lookups for 15 minutes.
Force a refresh with `cyb sync`, or bypass the cache for one command with
`--no-cache`.

## A command that used to work now 404s

The fork may have changed. Re-probe:

```bash
cyb doctor
```

Then check `references/api-surface.md` against what `doctor` reports.
```

Create `.claude/skills/cybernetics/README.md`:

```markdown
# cyb — Cybernetics CLI

A zero-dependency Node CLI for the Cybernetics project instance
(`https://projects.avarile.com`, a Plane fork).

One codebase serves two audiences: agents invoke it with `--json`, humans use
the tables and the interactive session.

## Requirements

Node 24 or newer. No `npm install` — there are no dependencies.

## Setup

```bash
export CYB_TOKEN='<your Plane API token>'
node bin/cyb doctor        # verify connectivity
node bin/cyb init          # persist config to ~/.cybernetics/config.json (0600)
```

Credentials are stored outside this repository. The CLI never prints your
token — only a fingerprint like `plane_api_…ab76`.

Optionally put `cyb` on your PATH:

```bash
npm link            # from this directory
cyb doctor
```

## Everyday use

```bash
cyb project list
cyb item list CYB
cyb item create CYB --name "Fix auth timeout" --priority high
cyb item move CYB-42 "In Progress"
cyb board CYB
cyb my
```

## Interactive session

```bash
cyb ui
```

```
cyb:CYB> ls --state todo
cyb:CYB> open 42
cyb:CYB> mv 42 "In Progress"
cyb:CYB> cd OTHER
cyb:CYB> exit
```

Tab completion draws on the local cache, so it costs no API calls.

## Safety

Deleting anything requires `--yes`. Without it the command shows what it would
destroy and exits 2 without touching the API.

## Tests

```bash
npm test                    # unit tests, no network needed
CYB_TOKEN='<token>' CYB_RUN_INTEGRATION=1 npm run test:integration
```

Integration tests create a scratch project and delete it afterwards.

## Documentation

- `SKILL.md` — the agent-facing entry point
- `references/api-surface.md` — what this fork does and does not expose
- `references/recipes.md` — multi-step workflows
- `references/troubleshooting.md` — exit codes and recovery
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/skill-doc.test.mjs`
Expected: PASS — 10 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/SKILL.md \
        .claude/skills/cybernetics/README.md \
        .claude/skills/cybernetics/references/ \
        .claude/skills/cybernetics/tests/skill-doc.test.mjs
git commit -m "docs(cyb): add SKILL.md, README and reference documentation"
```

---

### Task 18: Integration Tests Against the Live Instance

**Files:**
- Create: `.claude/skills/cybernetics/tests/integration/live.test.mjs`
- Test: the file is its own test

**Interfaces:**
- Consumes: `main` from `src/cli.mjs`
- Produces: nothing importable. This task proves the stack end to end.

The suite creates one scratch project, exercises the full lifecycle, and
deletes it in a `finally` block — the same discipline the design probe used.
It skips entirely unless both `CYB_TOKEN` and `CYB_RUN_INTEGRATION=1` are set.

- [ ] **Step 1: Write the test**

Create `.claude/skills/cybernetics/tests/integration/live.test.mjs`:

```js
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { main } from '../../src/cli.mjs';

const ENABLED = Boolean(process.env.CYB_TOKEN) && process.env.CYB_RUN_INTEGRATION === '1';
const IDENTIFIER = 'ZZITEST';

const scratch = mkdtempSync(join(tmpdir(), 'cyb-int-'));
const deps = () => ({
  env: { CYB_TOKEN: process.env.CYB_TOKEN },
  cwd: scratch,
  configPath: join(scratch, 'config.json'),
  cachePath: join(scratch, 'cache.json'),
});

function capture() {
  const out = [];
  const err = [];
  return {
    stdout: { write: (s) => out.push(s), isTTY: false },
    stderr: { write: (s) => err.push(s) },
    outText: () => out.join(''),
    errText: () => err.join(''),
  };
}

async function run(argv) {
  const streams = capture();
  const code = await main([...argv, '--json'], { ...deps(), streams });
  return { code, out: streams.outText(), err: streams.errText() };
}

async function cleanup() {
  await run(['project', 'delete', IDENTIFIER, '--yes']).catch(() => {});
}

before(async () => {
  if (!ENABLED) return;
  await cleanup();
});

after(async () => {
  if (!ENABLED) return;
  await cleanup();
});

test('doctor authenticates against the live instance', { skip: !ENABLED }, async () => {
  const { code, out } = await run(['doctor']);
  assert.equal(code, 0);
  const report = JSON.parse(out);
  assert.equal(report.workspace, 'cybernetics');
  assert.ok(report.user.id);
  assert.match(report.token, /^plane_api_…/);
});

test('full work item lifecycle against the live instance', { skip: !ENABLED }, async () => {
  try {
    const created = await run(['project', 'create', '--name', 'ZZ Integration Test', '--identifier', IDENTIFIER]);
    assert.equal(created.code, 0);
    assert.ok(JSON.parse(created.out).id);

    const states = await run(['state', 'list', IDENTIFIER]);
    assert.equal(states.code, 0);
    const stateNames = JSON.parse(states.out).map((s) => s.name);
    assert.ok(stateNames.includes('In Progress'), `expected default states, got ${stateNames}`);

    const item = await run(['item', 'create', IDENTIFIER, '--name', 'Integration item', '--priority', 'high']);
    assert.equal(item.code, 0);
    const ref = `${IDENTIFIER}-${JSON.parse(item.out).sequence_id}`;

    const listed = await run(['item', 'list', IDENTIFIER]);
    assert.equal(listed.code, 0);
    assert.ok(JSON.parse(listed.out).some((r) => r.ref === ref));

    const moved = await run(['item', 'move', ref, 'In Progress']);
    assert.equal(moved.code, 0);

    const shown = await run(['item', 'show', ref]);
    assert.equal(JSON.parse(shown.out).priority, 'high');

    const commented = await run(['comment', 'add', ref, 'integration comment']);
    assert.equal(commented.code, 0);

    const comments = await run(['comment', 'list', ref]);
    assert.ok(JSON.parse(comments.out).some((c) => /integration comment/.test(c.text)));

    const board = await run(['board', IDENTIFIER]);
    assert.equal(board.code, 0);
    assert.ok(JSON.parse(board.out)['In Progress'].some((r) => r.ref === ref));

    const refused = await run(['item', 'delete', ref]);
    assert.equal(refused.code, 2, 'delete without --yes must be refused');
    assert.equal(JSON.parse(refused.err).error.code, 2);

    const deleted = await run(['item', 'delete', ref, '--yes']);
    assert.equal(deleted.code, 0);
  } finally {
    await cleanup();
  }
});

test('an unresolvable state name fails with exit 3 and lists valid states', { skip: !ENABLED }, async () => {
  try {
    await run(['project', 'create', '--name', 'ZZ Integration Test', '--identifier', IDENTIFIER]);
    const bad = await run(['item', 'create', IDENTIFIER, '--name', 'x', '--state', 'Nonexistent']);
    assert.equal(bad.code, 3);
    assert.match(JSON.parse(bad.err).error.hint, /Backlog|In Progress/);
  } finally {
    await cleanup();
  }
});

test('an invalid priority is rejected locally with exit 1', { skip: !ENABLED }, async () => {
  const bad = await run(['item', 'create', 'ANY', '--name', 'x', '--priority', 'critical']);
  assert.equal(bad.code, 1);
  assert.match(JSON.parse(bad.err).error.message, /invalid priority/);
});
```

- [ ] **Step 2: Verify it skips cleanly without a token**

Run: `cd .claude/skills/cybernetics && node --test tests/integration/*.test.mjs`
Expected: all tests report as skipped, exit code 0. No network access attempted.

- [ ] **Step 3: Run it against the live instance**

Run:
```bash
cd .claude/skills/cybernetics
CYB_TOKEN='<the real token>' CYB_RUN_INTEGRATION=1 node --test tests/integration/*.test.mjs
```
Expected: PASS — 4 tests. Afterwards verify the scratch project is gone:
```bash
CYB_TOKEN='<the real token>' node bin/cyb project list
```
`ZZITEST` must not appear.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/cybernetics/tests/integration/live.test.mjs
git commit -m "test(cyb): add token-gated integration suite with scratch project teardown"
```

---

### Task 19: Final Verification and Handoff

**Files:**
- Modify: `.claude/skills/cybernetics/README.md` (record verified status)
- Verify: every file created in Phases 1–3

**Interfaces:**
- Consumes: everything
- Produces: a verified, committed skill

- [ ] **Step 1: Run the complete unit suite**

Run: `cd .claude/skills/cybernetics && node --test`
Expected: PASS — 192 tests across 19 files, no network required, exit code 0.

If any test fails, fix it before continuing. Do not proceed on a red suite.

- [ ] **Step 2: Confirm no file exceeds 500 lines**

Run:
```bash
cd .claude/skills/cybernetics
find . -name '*.mjs' -o -name '*.md' | grep -v node_modules | xargs wc -l | sort -rn | head -20
```
Expected: every entry under 500 lines. If `src/commands/item.mjs` has grown past it, split the write handlers into `src/commands/item-write.mjs` and re-export from `item.mjs`.

- [ ] **Step 3: Confirm no secret is committed**

Run:
```bash
cd /Users/avarilewang/Documents/agentSkills
git grep -nE 'plane_api_[a-f0-9]{16,}' -- .claude/skills/cybernetics/ || echo "clean: no token in tracked files"
```
Expected: `clean: no token in tracked files`

Also verify the config path is outside the repo:
```bash
git check-ignore -v .env || echo ".env is gitignored via the repo root rule"
```

- [ ] **Step 4: Verify the skill is discoverable**

Run: `cd /Users/avarilewang/Documents/agentSkills && ls .claude/skills/cybernetics/SKILL.md`
Expected: the path exists. Restart Claude Code and confirm the skill appears in the available-skills listing as "Cybernetics Project Management".

- [ ] **Step 5: End-to-end human check**

Run:
```bash
cd .claude/skills/cybernetics
export CYB_TOKEN='<the real token>'
node bin/cyb --help
node bin/cyb doctor
node bin/cyb project list
```
Expected: help lists every group (`doctor`, `project`, `item`, `state`, `label`, `member`, `cycle`, `module`, `comment`, `board`, `my`, `search`, `init`, `sync`, `ui`); `doctor` reports the workspace and a fingerprinted token.

- [ ] **Step 6: Update the README status line and commit**

Add near the top of `README.md`, after the opening paragraph:

```markdown
**Status:** verified against Plane v2.6.3 at `projects.avarile.com` on 2026-08-17.
Unit tests run offline; integration tests require `CYB_TOKEN` and `CYB_RUN_INTEGRATION=1`.
```

```bash
git add .claude/skills/cybernetics/README.md
git commit -m "docs(cyb): record verified status"
```

- [ ] **Step 7: Rotate the token**

The API token was shared in conversation during design and appears in this
session's history. Rotate it in Plane: **Profile settings → Personal access
tokens** → revoke the old token, create a new one, then:

```bash
export CYB_TOKEN='<the new token>'
node bin/cyb doctor      # confirm the new token works
node bin/cyb init        # persist it to ~/.cybernetics/config.json
```

This step is not optional. The repository is public.

---

## Phase 3 Exit Criteria

- `node --test` passes offline with no `CYB_TOKEN` set.
- The integration suite passes against the live instance and leaves no scratch project behind.
- `cyb ui` runs an interactive session with tab completion and a persistent project.
- `SKILL.md` is under 6KB, has valid two-field frontmatter, and is discoverable by Claude Code.
- No tracked file contains an API token.
- The design-time token has been rotated.
