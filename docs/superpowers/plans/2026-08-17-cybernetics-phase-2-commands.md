# Cybernetics Skill — Phase 2: Command Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build every command in the spec's command surface on top of the Phase 1 core — projects, work items, metadata, planning, comments, composites, and setup — producing a fully usable CLI.

**Architecture:** Each command group is one file under `src/commands/`, exporting plain async functions of the shape `(ctx) => Promise<void>`. Groups are wired into `REGISTRY` in `src/cli.mjs`; the router needs no structural change. Nothing here reaches the network except through `ctx.client`, and nothing resolves a UUID except through `ctx.resolver`.

**Tech Stack:** Node 24, ESM, zero runtime dependencies. `node:test` for tests.

**Spec:** `docs/superpowers/specs/2026-08-17-cybernetics-skill-design.md`

**Depends on:** `docs/superpowers/plans/2026-08-17-cybernetics-phase-1-core.md` (Tasks 1–7 complete)

## Global Constraints

- Zero runtime dependencies. Built-in modules only.
- Node >= 24. ESM only. All source files `.mjs`. Every file under 500 lines.
- Work items are at `/issues/` on this v2.6.3 fork. Create/update payload keys are `state`, `assignees`, `labels`, `parent`, `priority`, `name`, `description_html`, `target_date`, `start_date`.
- Valid priorities: `urgent`, `high`, `medium`, `low`, `none`. Anything else is rejected client-side before a request is made.
- Default list limit is 30, from `ctx.config.defaults.limit`. Truncation is never silent.
- Default list projection is `['id','sequence_id','name','state','priority','assignees']`; `--full` omits the `fields` param entirely.
- Gated behind `--yes`: `project delete`, `item delete`, `label delete`, `cycle delete`, `module delete`, and any bulk update touching more than 10 items. Refusal exits 2 **without calling the API**.
- Exit codes: `0` ok, `1` general, `2` refused, `3` not found, `4` auth, `5` rate limited.
- Endpoints absent on this instance — never call them: `estimates`, `views`, `issue-properties`, `archived-issues`, `attachments`, `sub-issues`, `issue-relation`, `inbox-issues`. `issue-types` returns 402.
- Tests run with `node --test` from `.claude/skills/cybernetics/` and must pass with no network and no `CYB_TOKEN`.

### Shared context object (from Phase 1)

Every handler receives:

```js
ctx = {
  config,      // { baseUrl, workspace, token, defaultProject, defaults: { limit } }
  client,      // Client — request(), paginate(), wsPath, projectPath()
  cache,       // the loaded cache object
  resolver,    // Resolver — me(), project(), item(), state(), label(), member(), statesFor()
  save,        // () => void, persists the cache
  mode,        // 'json' | 'table' | 'plain'
  streams,     // { stdout, stderr }
  values,      // parsed flags
  positionals, // parsed positional args
}
```

---

### Task 8: Safety Gate and Project Commands

**Files:**
- Create: `.claude/skills/cybernetics/src/safety.mjs`
- Create: `.claude/skills/cybernetics/src/commands/project.mjs`
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (add the `project` group to `REGISTRY`)
- Test: `.claude/skills/cybernetics/tests/safety.test.mjs`
- Test: `.claude/skills/cybernetics/tests/project.test.mjs`

**Interfaces:**
- Consumes: `ctx` (Phase 1), `CybError`/`EXIT` from `src/errors.mjs`, `emit`/`renderTable` from `src/format.mjs`
- Produces:
  - `BULK_THRESHOLD = 10` and `requireConfirmation(ctx, { action, targets }) -> void` from `src/safety.mjs`
  - `list`, `show`, `create`, `update`, `remove` from `src/commands/project.mjs`
  - `PROJECT_COLUMNS` from `src/commands/project.mjs`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/safety.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { requireConfirmation, BULK_THRESHOLD } from '../src/safety.mjs';
import { EXIT } from '../src/errors.mjs';

test('BULK_THRESHOLD matches the spec', () => {
  assert.equal(BULK_THRESHOLD, 10);
});

test('requireConfirmation throws REFUSED when --yes is absent', () => {
  assert.throws(
    () => requireConfirmation({ values: {} }, { action: 'delete project', targets: ['CYB'] }),
    (err) => err.code === EXIT.REFUSED,
  );
});

test('the refusal names the action and the targets', () => {
  try {
    requireConfirmation({ values: {} }, { action: 'delete work item', targets: ['CYB-42', 'CYB-43'] });
    assert.fail('should have thrown');
  } catch (err) {
    assert.match(err.message, /delete work item/);
    assert.match(err.message, /CYB-42/);
    assert.match(err.hint, /--yes/);
  }
});

test('requireConfirmation is a no-op when --yes is present', () => {
  assert.doesNotThrow(() =>
    requireConfirmation({ values: { yes: true } }, { action: 'delete', targets: ['CYB'] }),
  );
});
```

Create `.claude/skills/cybernetics/tests/project.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { list, show, create, remove, PROJECT_COLUMNS } from '../src/commands/project.mjs';
import { Client } from '../src/client.mjs';
import { Resolver } from '../src/resolve.mjs';
import { emptyCache } from '../src/cache.mjs';
import { makeFakeFetch } from './helpers/fake-fetch.mjs';
import { EXIT } from '../src/errors.mjs';

const UUID_A = '50fc7f95-db38-4fe8-850b-41643c1ca2f5';

export function makeCtx(responses, { values = {}, positionals = [], mode = 'json' } = {}) {
  const { fetchImpl, calls } = makeFakeFetch(responses);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });
  const cache = emptyCache('cybernetics');
  const out = [];
  const ctx = {
    config: { baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok', defaultProject: null, defaults: { limit: 30 } },
    client, cache,
    resolver: new Resolver({ client, cache, persist: () => {}, now: () => 1_000_000 }),
    save: () => {},
    mode,
    streams: { stdout: { write: (s) => out.push(s), isTTY: false }, stderr: { write: () => {} } },
    values: { limit: undefined, ...values },
    positionals,
  };
  return { ctx, calls, outText: () => out.join('') };
}

test('PROJECT_COLUMNS exposes key, name and id', () => {
  assert.deepEqual(PROJECT_COLUMNS.map((c) => c.key), ['identifier', 'name', 'id']);
});

test('project list emits the projects it fetched', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ]);
  await list(ctx);
  assert.equal(JSON.parse(outText())[0].identifier, 'CYB');
});

test('project list reports an empty workspace without crashing', async () => {
  const { ctx, outText } = makeCtx([{ status: 200, body: { total_count: 0, results: [] } }], { mode: 'plain' });
  await list(ctx);
  assert.match(outText(), /no results/);
});

test('project show resolves an identifier then fetches the record', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
    { status: 200, body: { id: UUID_A, identifier: 'CYB', name: 'Core', description: 'd' } },
  ], { positionals: ['CYB'] });
  await show(ctx);
  assert.equal(JSON.parse(outText()).id, UUID_A);
});

test('project create posts name and identifier and uppercases the identifier', async () => {
  const { ctx, calls } = makeCtx([{ status: 201, body: { id: UUID_A, identifier: 'CYB', name: 'Core' } }], {
    values: { name: 'Core', identifier: 'cyb' },
  });
  await create(ctx);
  assert.equal(JSON.parse(calls[0].init.body).identifier, 'CYB');
  assert.equal(JSON.parse(calls[0].init.body).name, 'Core');
});

test('project create requires --name and --identifier', async () => {
  const { ctx } = makeCtx([], { values: { name: 'Core' } });
  await assert.rejects(() => create(ctx), (err) => err.code === EXIT.GENERAL);
});

test('project create rejects an identifier over the 10-char instance limit', async () => {
  const { ctx } = makeCtx([], { values: { name: 'Core', identifier: 'WAYTOOLONGIDENT' } });
  await assert.rejects(() => create(ctx), (err) => /10/.test(err.message));
});

test('project delete without --yes refuses and issues no request', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
  ], { positionals: ['CYB'] });
  await assert.rejects(() => remove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});

test('project delete with --yes issues the DELETE', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: UUID_A, identifier: 'CYB', name: 'Core' }] } },
    { status: 204, body: undefined },
  ], { positionals: ['CYB'], values: { yes: true } });
  await remove(ctx);
  assert.equal(calls.at(-1).init.method, 'DELETE');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/safety.test.mjs tests/project.test.mjs`
Expected: FAIL — `Cannot find module '../src/safety.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/safety.mjs`:

```js
import { CybError, EXIT } from './errors.mjs';

// The command surface in this iteration has no bulk-mutation command, so
// BULK_THRESHOLD has no call site yet. It is exported and tested so the
// spec's bulk rule has one authoritative value when such a command lands.
export const BULK_THRESHOLD = 10;

export function requireConfirmation(ctx, { action, targets }) {
  if (ctx.values?.yes) return;
  const list = targets.join(', ');
  throw new CybError(
    EXIT.REFUSED,
    `refusing to ${action} without confirmation: ${list}`,
    'confirm with the user, then pass --yes',
  );
}
```

Create `.claude/skills/cybernetics/src/commands/project.mjs`:

```js
import { emit } from '../format.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const PROJECT_COLUMNS = [
  { key: 'identifier', label: 'KEY' },
  { key: 'name', label: 'NAME' },
  { key: 'id', label: 'ID' },
];

const IDENTIFIER_MAX = 10;

function requiredProject(ctx) {
  const ref = ctx.positionals[0] ?? ctx.values.project ?? ctx.config.defaultProject;
  if (!ref) {
    throw new CybError(EXIT.GENERAL, 'no project given', 'pass a project key, e.g. cyb project show CYB');
  }
  return ref;
}

export async function list(ctx) {
  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/projects/`, {
    fields: ctx.values.full ? undefined : ['id', 'identifier', 'name'],
  });
  const rows = data?.results ?? [];
  emit(rows, { mode: ctx.mode, columns: PROJECT_COLUMNS, stdout: ctx.streams.stdout });
}

export async function show(ctx) {
  const project = await ctx.resolver.project(requiredProject(ctx));
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/`);
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function create(ctx) {
  const name = ctx.values.name;
  const identifier = ctx.values.identifier;

  if (!name || !identifier) {
    throw new CybError(
      EXIT.GENERAL,
      'project create needs --name and --identifier',
      'example: cyb project create --name "Core" --identifier CYB',
    );
  }
  if (identifier.length > IDENTIFIER_MAX) {
    throw new CybError(
      EXIT.GENERAL,
      `identifier must be at most ${IDENTIFIER_MAX} characters`,
      `"${identifier}" is ${identifier.length}`,
    );
  }

  const body = { name, identifier: identifier.toUpperCase() };
  if (ctx.values.description) body.description = ctx.values.description;

  const { data } = await ctx.client.request('POST', `${ctx.client.wsPath}/projects/`, { body });

  ctx.cache.projects[body.identifier] = {
    id: data.id,
    name: data.name,
    fetchedAt: new Date().toISOString(),
  };
  ctx.save();

  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function update(ctx) {
  const project = await ctx.resolver.project(requiredProject(ctx));
  const body = {};
  if (ctx.values.name) body.name = ctx.values.name;
  if (ctx.values.description) body.description = ctx.values.description;

  if (!Object.keys(body).length) {
    throw new CybError(EXIT.GENERAL, 'nothing to update', 'pass --name or --description');
  }

  const { data } = await ctx.client.request('PATCH', `${ctx.client.projectPath(project.id)}/`, { body });
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function remove(ctx) {
  const ref = requiredProject(ctx);
  const project = await ctx.resolver.project(ref);

  requireConfirmation(ctx, {
    action: 'delete project (this destroys all its work items)',
    targets: [project.identifier ?? project.id],
  });

  await ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/`);

  delete ctx.cache.projects[String(project.identifier ?? '').toUpperCase()];
  delete ctx.cache.byProject[project.id];
  ctx.save();

  emit({ deleted: project.identifier ?? project.id }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs` — add the import and the registry entry:

```js
import * as project from './commands/project.mjs';
```

Then inside `REGISTRY`, after the `doctor` entry:

```js
  project: {
    list: { summary: 'List all projects', options: {}, handler: project.list },
    show: { summary: 'Show one project', options: {}, handler: project.show },
    create: {
      summary: 'Create a project',
      options: {
        name: { type: 'string' },
        identifier: { type: 'string' },
        description: { type: 'string' },
      },
      handler: project.create,
    },
    update: {
      summary: 'Update a project',
      options: { name: { type: 'string' }, description: { type: 'string' } },
      handler: project.update,
    },
    delete: { summary: 'Delete a project (needs --yes)', options: {}, handler: project.remove },
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/safety.test.mjs tests/project.test.mjs`
Expected: PASS — 13 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/safety.mjs \
        .claude/skills/cybernetics/src/commands/project.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/safety.test.mjs \
        .claude/skills/cybernetics/tests/project.test.mjs
git commit -m "feat(cyb): add safety gate and project commands"
```

---

### Task 9: Work Item Read Commands

**Files:**
- Create: `.claude/skills/cybernetics/src/commands/item.mjs`
- Create: `.claude/skills/cybernetics/tests/helpers/ctx.mjs`
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (add the `item` group)
- Test: `.claude/skills/cybernetics/tests/item-read.test.mjs`

**Interfaces:**
- Consumes: `ctx`, `requireConfirmation`, `emit`, `truncationNotice`
- Produces:
  - `ITEM_COLUMNS`, `LIST_FIELDS`, `PRIORITIES` from `src/commands/item.mjs`
  - `list(ctx)`, `show(ctx)` from `src/commands/item.mjs`
  - `decorate(items, { project, states })` — maps raw API items to display rows with `ref` and state name
  - `makeCtx(responses, opts)` from `tests/helpers/ctx.mjs` (extracted from Task 8's inline helper so later tasks reuse it)

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/helpers/ctx.mjs`:

```js
import { Client } from '../../src/client.mjs';
import { Resolver } from '../../src/resolve.mjs';
import { emptyCache } from '../../src/cache.mjs';
import { makeFakeFetch } from './fake-fetch.mjs';

export const UUID_PROJECT = '50fc7f95-db38-4fe8-850b-41643c1ca2f5';
export const UUID_STATE_PROGRESS = '7c9cd656-c9cf-4622-9d2a-b44ad1766112';
export const UUID_STATE_BACKLOG = '8c3d7fcf-662c-44db-8d50-ccb556664063';

export const STATE_LIST = [
  { id: UUID_STATE_BACKLOG, name: 'Backlog', group: 'backlog' },
  { id: UUID_STATE_PROGRESS, name: 'In Progress', group: 'started' },
  { id: 'state-done', name: 'Done', group: 'completed' },
];

export function makeCtx(responses, { values = {}, positionals = [], mode = 'json', warmCache = true } = {}) {
  const { fetchImpl, calls } = makeFakeFetch(responses);
  const client = new Client({
    baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
    fetchImpl, sleep: async () => {}, now: () => 1_000_000,
  });

  const cache = emptyCache('cybernetics');
  if (warmCache) {
    const stamp = new Date(1_000_000).toISOString();
    cache.projects.CYB = { id: UUID_PROJECT, name: 'Core', fetchedAt: stamp };
    cache.byProject[UUID_PROJECT] = {
      states: Object.fromEntries(STATE_LIST.map((s) => [s.name.toLowerCase(), s.id])),
      stateList: STATE_LIST,
      labels: {},
      members: {},
      items: {},
      fetchedAt: stamp,
    };
  }

  const out = [];
  const ctx = {
    config: {
      baseUrl: 'https://example.test', workspace: 'cybernetics', token: 'tok',
      defaultProject: null, defaults: { limit: 30 },
    },
    client, cache,
    resolver: new Resolver({ client, cache, persist: () => {}, now: () => 1_000_000 }),
    save: () => {},
    mode,
    streams: { stdout: { write: (s) => out.push(s), isTTY: false }, stderr: { write: () => {} } },
    values: { ...values },
    positionals,
  };
  return { ctx, calls, outText: () => out.join('') };
}
```

Create `.claude/skills/cybernetics/tests/item-read.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { list, show, decorate, ITEM_COLUMNS, LIST_FIELDS } from '../src/commands/item.mjs';
import { makeCtx, STATE_LIST, UUID_STATE_PROGRESS, UUID_PROJECT } from './helpers/ctx.mjs';

test('LIST_FIELDS is the token-bounded projection from the spec', () => {
  assert.deepEqual(LIST_FIELDS, ['id', 'sequence_id', 'name', 'state', 'priority', 'assignees']);
});

test('ITEM_COLUMNS leads with the human reference', () => {
  assert.equal(ITEM_COLUMNS[0].key, 'ref');
});

test('decorate builds CYB-42 refs and resolves state names', () => {
  const rows = decorate(
    [{ id: 'a', sequence_id: 42, name: 'Fix auth', state: UUID_STATE_PROGRESS, priority: 'high' }],
    { project: { identifier: 'CYB' }, states: STATE_LIST },
  );
  assert.equal(rows[0].ref, 'CYB-42');
  assert.equal(rows[0].state, 'In Progress');
  assert.equal(rows[0].name, 'Fix auth');
});

test('decorate falls back to the raw state id when it is unknown', () => {
  const rows = decorate(
    [{ id: 'a', sequence_id: 1, name: 'x', state: 'unmapped', priority: 'none' }],
    { project: { identifier: 'CYB' }, states: STATE_LIST },
  );
  assert.equal(rows[0].state, 'unmapped');
});

test('item list requests only the projected fields by default', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS, priority: 'low' }], next_page_results: false } },
  ], { positionals: ['CYB'] });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.get('fields'), LIST_FIELDS.join(','));
});

test('item list with --full omits the fields projection', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'], values: { full: true } });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.has('fields'), false);
});

test('item list defaults to a limit of 30', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'] });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.get('per_page'), '30');
});

test('item list filters by state name, resolving it to a uuid', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { total_count: 0, results: [], next_page_results: false } },
  ], { positionals: ['CYB'], values: { state: 'In Progress' } });
  await list(ctx);
  assert.equal(new URL(calls[0].url).searchParams.get('state'), UUID_STATE_PROGRESS);
});

test('item list prints a truncation notice when results were withheld', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { total_count: 77, results: [{ id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'], mode: 'plain' });
  await list(ctx);
  assert.match(outText(), /more \(--limit/);
});

test('item list caches the sequence-to-uuid mapping it saw', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { total_count: 1, results: [{ id: 'item-uuid', sequence_id: 42, name: 'x', state: UUID_STATE_PROGRESS }], next_page_results: false } },
  ], { positionals: ['CYB'] });
  await list(ctx);
  assert.equal(ctx.cache.byProject[UUID_PROJECT].items[42], 'item-uuid');
});

test('item show resolves CYB-42 and fetches the full record', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42, name: 'Fix auth', state: UUID_STATE_PROGRESS } },
  ], { positionals: ['CYB-42'] });
  await show(ctx);
  assert.equal(JSON.parse(outText()).name, 'Fix auth');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/item-read.test.mjs`
Expected: FAIL — `Cannot find module '../src/commands/item.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/commands/item.mjs`:

```js
import { emit, truncationNotice, renderTable } from '../format.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';
import { projectBucket } from '../cache.mjs';

export const PRIORITIES = Object.freeze(['urgent', 'high', 'medium', 'low', 'none']);

export const LIST_FIELDS = ['id', 'sequence_id', 'name', 'state', 'priority', 'assignees'];

export const ITEM_COLUMNS = [
  { key: 'ref', label: 'REF' },
  { key: 'state', label: 'STATE' },
  { key: 'priority', label: 'PRIO' },
  { key: 'name', label: 'NAME' },
];

export function decorate(items, { project, states }) {
  const byId = new Map(states.map((s) => [s.id, s.name]));
  return items.map((item) => ({
    ref: project.identifier ? `${project.identifier}-${item.sequence_id}` : String(item.sequence_id),
    state: byId.get(item.state) ?? item.state,
    priority: item.priority,
    name: item.name,
    id: item.id,
    sequence_id: item.sequence_id,
    assignees: item.assignees,
  }));
}

export function projectRef(ctx) {
  const ref = ctx.positionals[0] ?? ctx.values.project ?? ctx.config.defaultProject;
  if (!ref) {
    throw new CybError(EXIT.GENERAL, 'no project given', 'pass a project key, e.g. cyb item list CYB');
  }
  return ref;
}

export function limitOf(ctx) {
  const raw = ctx.values.limit ?? ctx.config.defaults.limit;
  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    throw new CybError(EXIT.GENERAL, `invalid --limit: ${raw}`, 'pass a positive integer');
  }
  return value;
}

export function validatePriority(priority) {
  if (priority === undefined) return undefined;
  if (!PRIORITIES.includes(priority)) {
    throw new CybError(
      EXIT.GENERAL,
      `invalid priority: ${priority}`,
      `valid: ${PRIORITIES.join(', ')}`,
    );
  }
  return priority;
}

export async function list(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  const limit = limitOf(ctx);

  const query = {};
  if (ctx.values.state) query.state = await ctx.resolver.state(project.id, ctx.values.state);
  if (ctx.values.priority) query.priority = validatePriority(ctx.values.priority);
  if (ctx.values.assignee) query.assignees = await ctx.resolver.member(ctx.values.assignee);

  const path = `${ctx.client.projectPath(project.id)}/issues/`;
  const { data } = await ctx.client.request('GET', path, {
    query: { ...query, per_page: limit },
    fields: ctx.values.full ? undefined : LIST_FIELDS,
  });

  const raw = data?.results ?? [];
  const total = data?.total_count ?? raw.length;

  const bucket = projectBucket(ctx.cache, project.id);
  for (const item of raw) bucket.items[item.sequence_id] = item.id;
  ctx.save();

  if (ctx.mode === 'json') {
    emit(decorate(raw, { project, states }), { mode: ctx.mode, stdout: ctx.streams.stdout });
    return;
  }

  const rows = decorate(raw, { project, states });
  ctx.streams.stdout.write(`${renderTable(rows, ITEM_COLUMNS, { mode: ctx.mode })}\n`);
  const notice = truncationNotice(rows.length, total, limit);
  if (notice) ctx.streams.stdout.write(`${notice}\n`);
}

export async function show(ctx) {
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb item show CYB-42');

  const item = await ctx.resolver.item(ref);
  const { data } = await ctx.client.request(
    'GET',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/`,
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs` — add the import:

```js
import * as item from './commands/item.mjs';
```

And the registry entry (the write actions arrive in Task 10):

```js
  item: {
    list: {
      summary: 'List work items in a project',
      options: {
        state: { type: 'string' },
        priority: { type: 'string' },
        assignee: { type: 'string' },
      },
      handler: item.list,
    },
    show: { summary: 'Show one work item', options: {}, handler: item.show },
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/item-read.test.mjs`
Expected: PASS — 11 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/commands/item.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/helpers/ctx.mjs \
        .claude/skills/cybernetics/tests/item-read.test.mjs
git commit -m "feat(cyb): add work item list and show with bounded projections"
```

---

### Task 10: Work Item Write Commands

**Files:**
- Modify: `.claude/skills/cybernetics/src/commands/item.mjs` (append write handlers)
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (extend the `item` group)
- Test: `.claude/skills/cybernetics/tests/item-write.test.mjs`

**Interfaces:**
- Consumes: `projectRef`, `validatePriority`, `decorate` from Task 9; `requireConfirmation`, `BULK_THRESHOLD`
- Produces: `create(ctx)`, `update(ctx)`, `move(ctx)`, `assign(ctx)`, `remove(ctx)` from `src/commands/item.mjs`, plus `buildItemBody(ctx, { project })` returning the API payload

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/item-write.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { create, update, move, assign, remove } from '../src/commands/item.mjs';
import { makeCtx, UUID_STATE_PROGRESS, UUID_PROJECT } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

test('item create posts name and resolved state', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'new-uuid', sequence_id: 1, name: 'Fix auth', state: UUID_STATE_PROGRESS } },
  ], { positionals: ['CYB'], values: { name: 'Fix auth', state: 'In Progress' } });
  await create(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.name, 'Fix auth');
  assert.equal(body.state, UUID_STATE_PROGRESS);
});

test('item create requires --name', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB'], values: {} });
  await assert.rejects(() => create(ctx), (err) => err.code === EXIT.GENERAL && /--name/.test(err.hint));
});

test('item create rejects an invalid priority before any request', async () => {
  const { ctx, calls } = makeCtx([], { positionals: ['CYB'], values: { name: 'x', priority: 'critical' } });
  await assert.rejects(() => create(ctx), (err) => /invalid priority/.test(err.message));
  assert.equal(calls.length, 0);
});

test('item create maps --description to description_html', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'a', sequence_id: 1, name: 'x' } },
  ], { positionals: ['CYB'], values: { name: 'x', description: 'hello' } });
  await create(ctx);
  assert.equal(JSON.parse(calls.at(-1).init.body).description_html, '<p>hello</p>');
});

test('item create resolves --parent to a uuid', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'parent-uuid', sequence_id: 1 }] } },
    { status: 201, body: { id: 'a', sequence_id: 2, name: 'child' } },
  ], { positionals: ['CYB'], values: { name: 'child', parent: 'CYB-1' } });
  await create(ctx);
  assert.equal(JSON.parse(calls.at(-1).init.body).parent, 'parent-uuid');
});

test('item update PATCHes only the fields supplied', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42, name: 'renamed' } },
  ], { positionals: ['CYB-42'], values: { name: 'renamed' } });
  await update(ctx);
  const patch = calls.at(-1);
  assert.equal(patch.init.method, 'PATCH');
  assert.deepEqual(JSON.parse(patch.init.body), { name: 'renamed' });
});

test('item update with no fields is rejected', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
  ], { positionals: ['CYB-42'], values: {} });
  await assert.rejects(() => update(ctx), (err) => /nothing to update/.test(err.message));
});

test('item move is sugar for updating the state', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { id: 'item-uuid', sequence_id: 42 } },
  ], { positionals: ['CYB-42', 'In Progress'] });
  await move(ctx);
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), { state: UUID_STATE_PROGRESS });
});

test('item move requires a target state', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB-42'] });
  await assert.rejects(() => move(ctx), (err) => /state/.test(err.message));
});

test('item assign resolves the member and PATCHes assignees', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'member-uuid', display_name: 'avarile', email: 'a@b.c' }] } },
    { status: 200, body: { id: 'item-uuid' } },
  ], { positionals: ['CYB-42', 'avarile'] });
  await assign(ctx);
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), { assignees: ['member-uuid'] });
});

test('item delete without --yes refuses and issues no DELETE', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
  ], { positionals: ['CYB-42'] });
  await assert.rejects(() => remove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});

test('item delete with --yes issues the DELETE and drops the cache entry', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 204, body: undefined },
  ], { positionals: ['CYB-42'], values: { yes: true } });
  await remove(ctx);
  assert.equal(calls.at(-1).init.method, 'DELETE');
  assert.equal(ctx.cache.byProject[UUID_PROJECT].items[42], undefined);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/item-write.test.mjs`
Expected: FAIL — `create is not a function` (or an import error for the missing exports)

- [ ] **Step 3: Write the implementation**

Append to `.claude/skills/cybernetics/src/commands/item.mjs`:

```js
function itemRef(ctx, index = 0) {
  const ref = ctx.positionals[index];
  if (!ref) {
    throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb item show CYB-42');
  }
  return ref;
}

export async function buildItemBody(ctx, { project }) {
  const body = {};

  if (ctx.values.name) body.name = ctx.values.name;
  if (ctx.values.description) body.description_html = `<p>${ctx.values.description}</p>`;

  const priority = validatePriority(ctx.values.priority);
  if (priority !== undefined) body.priority = priority;

  if (ctx.values.state) body.state = await ctx.resolver.state(project.id, ctx.values.state);

  if (ctx.values.assignee) {
    body.assignees = [await ctx.resolver.member(ctx.values.assignee)];
  }
  if (ctx.values.label) {
    body.labels = [await ctx.resolver.label(project.id, ctx.values.label)];
  }
  if (ctx.values.parent) {
    body.parent = (await ctx.resolver.item(ctx.values.parent)).id;
  }
  if (ctx.values['target-date']) body.target_date = ctx.values['target-date'];
  if (ctx.values['start-date']) body.start_date = ctx.values['start-date'];

  return body;
}

export async function create(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));

  if (!ctx.values.name) {
    throw new CybError(
      EXIT.GENERAL,
      'work item needs a name',
      'pass --name, e.g. cyb item create CYB --name "Fix auth"',
    );
  }
  validatePriority(ctx.values.priority);

  const body = await buildItemBody(ctx, { project });
  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/issues/`,
    { body },
  );

  const bucket = projectBucket(ctx.cache, project.id);
  bucket.items[data.sequence_id] = data.id;
  ctx.save();

  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function update(ctx) {
  const item = await ctx.resolver.item(itemRef(ctx));
  const project = await ctx.resolver.project(item.projectId);

  const body = await buildItemBody(ctx, { project: { id: item.projectId, ...project } });
  if (!Object.keys(body).length) {
    throw new CybError(
      EXIT.GENERAL,
      'nothing to update',
      'pass at least one of --name --state --priority --assignee --label --description',
    );
  }

  const { data } = await ctx.client.request(
    'PATCH',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/`,
    { body },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function move(ctx) {
  const stateName = ctx.positionals[1];
  if (!stateName) {
    throw new CybError(
      EXIT.GENERAL,
      'no target state given',
      'example: cyb item move CYB-42 "In Progress"',
    );
  }
  const item = await ctx.resolver.item(itemRef(ctx));
  const state = await ctx.resolver.state(item.projectId, stateName);

  const { data } = await ctx.client.request(
    'PATCH',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/`,
    { body: { state } },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function assign(ctx) {
  const who = ctx.positionals[1];
  if (!who) {
    throw new CybError(EXIT.GENERAL, 'no assignee given', 'example: cyb item assign CYB-42 avarile');
  }
  const item = await ctx.resolver.item(itemRef(ctx));
  const member = await ctx.resolver.member(who);

  const { data } = await ctx.client.request(
    'PATCH',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/`,
    { body: { assignees: [member] } },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function remove(ctx) {
  const ref = itemRef(ctx);
  const item = await ctx.resolver.item(ref);

  requireConfirmation(ctx, { action: 'delete work item', targets: [ref] });

  await ctx.client.request(
    'DELETE',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/`,
  );

  const bucket = projectBucket(ctx.cache, item.projectId);
  delete bucket.items[item.sequence_id];
  ctx.save();

  emit({ deleted: ref }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs` — extend the `item` registry group with:

```js
    create: {
      summary: 'Create a work item',
      options: {
        name: { type: 'string' },
        description: { type: 'string' },
        state: { type: 'string' },
        priority: { type: 'string' },
        assignee: { type: 'string' },
        label: { type: 'string' },
        parent: { type: 'string' },
        'target-date': { type: 'string' },
        'start-date': { type: 'string' },
      },
      handler: item.create,
    },
    update: {
      summary: 'Update a work item',
      options: {
        name: { type: 'string' },
        description: { type: 'string' },
        state: { type: 'string' },
        priority: { type: 'string' },
        assignee: { type: 'string' },
        label: { type: 'string' },
        'target-date': { type: 'string' },
        'start-date': { type: 'string' },
      },
      handler: item.update,
    },
    move: { summary: 'Move a work item to a state', options: {}, handler: item.move },
    assign: { summary: 'Assign a work item to a member', options: {}, handler: item.assign },
    delete: { summary: 'Delete a work item (needs --yes)', options: {}, handler: item.remove },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/item-write.test.mjs`
Expected: PASS — 12 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/commands/item.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/item-write.test.mjs
git commit -m "feat(cyb): add work item create, update, move, assign and gated delete"
```

---

### Task 11: Metadata Commands

**Files:**
- Create: `.claude/skills/cybernetics/src/commands/meta.mjs`
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (add `state`, `label`, `member` groups)
- Test: `.claude/skills/cybernetics/tests/meta.test.mjs`

**Interfaces:**
- Consumes: `ctx`, `projectRef` from `src/commands/item.mjs`, `requireConfirmation`
- Produces: `stateList`, `labelList`, `labelCreate`, `labelRemove`, `memberList`, and the column sets `STATE_COLUMNS`, `LABEL_COLUMNS`, `MEMBER_COLUMNS`

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/meta.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { stateList, labelList, labelCreate, labelRemove, memberList } from '../src/commands/meta.mjs';
import { makeCtx } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

test('state list emits the project states with their groups', async () => {
  const { ctx, outText } = makeCtx([], { positionals: ['CYB'] });
  await stateList(ctx);
  const rows = JSON.parse(outText());
  assert.equal(rows.length, 3);
  assert.equal(rows.find((r) => r.name === 'In Progress').group, 'started');
});

test('label list emits labels', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'l1', name: 'bug', color: '#f00' }] } },
  ], { positionals: ['CYB'] });
  await labelList(ctx);
  assert.equal(JSON.parse(outText())[0].name, 'bug');
});

test('label create posts name and colour', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'l1', name: 'bug', color: '#ff0000' } },
  ], { positionals: ['CYB'], values: { name: 'bug', color: '#ff0000' } });
  await labelCreate(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.name, 'bug');
  assert.equal(body.color, '#ff0000');
});

test('label create requires --name', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB'], values: {} });
  await assert.rejects(() => labelCreate(ctx), (err) => /--name/.test(err.hint));
});

test('label delete without --yes refuses', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { results: [{ id: 'l1', name: 'bug' }] } },
  ], { positionals: ['CYB', 'bug'] });
  await assert.rejects(() => labelRemove(ctx), (err) => err.code === EXIT.REFUSED);
});

test('member list emits workspace members', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', display_name: 'avarile', email: 'a@b.c', role: 20 }] } },
  ]);
  await memberList(ctx);
  assert.equal(JSON.parse(outText())[0].display_name, 'avarile');
});

test('member list never emits raw emails in table mode', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', display_name: 'avarile', email: 'a@b.c', role: 20 }] } },
  ], { mode: 'plain' });
  await memberList(ctx);
  assert.match(outText(), /avarile/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/meta.test.mjs`
Expected: FAIL — `Cannot find module '../src/commands/meta.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/commands/meta.mjs`:

```js
import { emit } from '../format.mjs';
import { projectRef } from './item.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const STATE_COLUMNS = [
  { key: 'name', label: 'NAME' },
  { key: 'group', label: 'GROUP' },
  { key: 'id', label: 'ID' },
];

export const LABEL_COLUMNS = [
  { key: 'name', label: 'NAME' },
  { key: 'color', label: 'COLOR' },
  { key: 'id', label: 'ID' },
];

export const MEMBER_COLUMNS = [
  { key: 'display_name', label: 'NAME' },
  { key: 'role', label: 'ROLE' },
  { key: 'id', label: 'ID' },
];

export async function stateList(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  emit(states, { mode: ctx.mode, columns: STATE_COLUMNS, stdout: ctx.streams.stdout });
}

export async function labelList(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/labels/`, {
    fields: ctx.values.full ? undefined : ['id', 'name', 'color'],
  });
  emit(data?.results ?? [], { mode: ctx.mode, columns: LABEL_COLUMNS, stdout: ctx.streams.stdout });
}

export async function labelCreate(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  if (!ctx.values.name) {
    throw new CybError(
      EXIT.GENERAL,
      'label needs a name',
      'pass --name, e.g. cyb label create CYB --name bug --color "#ff0000"',
    );
  }

  const body = { name: ctx.values.name };
  if (ctx.values.color) body.color = ctx.values.color;

  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/labels/`,
    { body },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function labelRemove(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const name = ctx.positionals[1];
  if (!name) {
    throw new CybError(EXIT.GENERAL, 'no label given', 'example: cyb label delete CYB bug --yes');
  }

  const labelId = await ctx.resolver.label(project.id, name);
  requireConfirmation(ctx, { action: 'delete label', targets: [name] });

  await ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/labels/${labelId}/`);
  emit({ deleted: name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function memberList(ctx) {
  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/members/`);
  const members = data?.results ?? data ?? [];
  emit(members, { mode: ctx.mode, columns: MEMBER_COLUMNS, stdout: ctx.streams.stdout });
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs` — add the import and three groups:

```js
import * as meta from './commands/meta.mjs';
```

```js
  state: {
    list: { summary: 'List workflow states in a project', options: {}, handler: meta.stateList },
  },
  label: {
    list: { summary: 'List labels in a project', options: {}, handler: meta.labelList },
    create: {
      summary: 'Create a label',
      options: { name: { type: 'string' }, color: { type: 'string' } },
      handler: meta.labelCreate,
    },
    delete: { summary: 'Delete a label (needs --yes)', options: {}, handler: meta.labelRemove },
  },
  member: {
    list: { summary: 'List workspace members', options: {}, handler: meta.memberList },
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/meta.test.mjs`
Expected: PASS — 7 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/commands/meta.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/meta.test.mjs
git commit -m "feat(cyb): add state, label and member commands"
```

---

### Task 12: Planning Commands (Cycles and Modules)

**Files:**
- Create: `.claude/skills/cybernetics/src/commands/planning.mjs`
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (add `cycle`, `module` groups)
- Test: `.claude/skills/cybernetics/tests/planning.test.mjs`

**Interfaces:**
- Consumes: `ctx`, `projectRef`, `requireConfirmation`
- Produces: `cycleList`, `cycleCreate`, `cycleAddItem`, `cycleRemove`, `moduleList`, `moduleCreate`, `moduleAddItem`, `moduleRemove`, and `PLANNING_COLUMNS`

Cycles accept `name`, `start_date`, `end_date`. Modules accept `name`, `description`. Adding a work item posts `{ issues: [uuid] }` to the sub-resource collection — `/cycles/{id}/cycle-issues/` and `/modules/{id}/module-issues/`.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/planning.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  cycleList, cycleCreate, cycleAddItem, cycleRemove,
  moduleList, moduleCreate, moduleAddItem, moduleRemove,
} from '../src/commands/planning.mjs';
import { makeCtx } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

test('cycle list emits cycles', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1', start_date: '2026-08-01', end_date: '2026-08-14' }] } },
  ], { positionals: ['CYB'] });
  await cycleList(ctx);
  assert.equal(JSON.parse(outText())[0].name, 'Sprint 1');
});

test('cycle create posts name with start and end dates', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'c1', name: 'Sprint 1' } },
  ], { positionals: ['CYB'], values: { name: 'Sprint 1', start: '2026-08-01', end: '2026-08-14' } });
  await cycleCreate(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.name, 'Sprint 1');
  assert.equal(body.start_date, '2026-08-01');
  assert.equal(body.end_date, '2026-08-14');
});

test('cycle create requires --name', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB'], values: {} });
  await assert.rejects(() => cycleCreate(ctx), (err) => /--name/.test(err.hint));
});

test('cycle add-item posts the issue uuid to cycle-issues', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1' }] } },
    { status: 201, body: {} },
  ], { positionals: ['CYB-42'], values: { cycle: 'Sprint 1' } });
  await cycleAddItem(ctx);
  const post = calls.at(-1);
  assert.match(post.url, /cycle-issues/);
  assert.deepEqual(JSON.parse(post.init.body), { issues: ['item-uuid'] });
});

test('cycle add-item requires --cycle', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB-42'], values: {} });
  await assert.rejects(() => cycleAddItem(ctx), (err) => /--cycle/.test(err.hint));
});

test('cycle add-item reports an unknown cycle by name', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1' }] } },
  ], { positionals: ['CYB-42'], values: { cycle: 'Sprint 9' } });
  await assert.rejects(() => cycleAddItem(ctx), (err) => err.code === EXIT.NOT_FOUND);
});

test('cycle delete without --yes refuses', async () => {
  const { ctx } = makeCtx([
    { status: 200, body: { results: [{ id: 'c1', name: 'Sprint 1' }] } },
  ], { positionals: ['CYB', 'Sprint 1'] });
  await assert.rejects(() => cycleRemove(ctx), (err) => err.code === EXIT.REFUSED);
});

test('module list emits modules', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', name: 'Auth' }] } },
  ], { positionals: ['CYB'] });
  await moduleList(ctx);
  assert.equal(JSON.parse(outText())[0].name, 'Auth');
});

test('module create posts a name', async () => {
  const { ctx, calls } = makeCtx([
    { status: 201, body: { id: 'm1', name: 'Auth' } },
  ], { positionals: ['CYB'], values: { name: 'Auth' } });
  await moduleCreate(ctx);
  assert.equal(JSON.parse(calls.at(-1).init.body).name, 'Auth');
});

test('module add-item posts to module-issues', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'm1', name: 'Auth' }] } },
    { status: 201, body: {} },
  ], { positionals: ['CYB-42'], values: { module: 'Auth' } });
  await moduleAddItem(ctx);
  assert.match(calls.at(-1).url, /module-issues/);
});

test('module delete without --yes refuses and issues no DELETE', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'm1', name: 'Auth' }] } },
  ], { positionals: ['CYB', 'Auth'] });
  await assert.rejects(() => moduleRemove(ctx), (err) => err.code === EXIT.REFUSED);
  assert.ok(calls.every((c) => c.init.method !== 'DELETE'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/planning.test.mjs`
Expected: FAIL — `Cannot find module '../src/commands/planning.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/commands/planning.mjs`:

```js
import { emit } from '../format.mjs';
import { projectRef } from './item.mjs';
import { requireConfirmation } from '../safety.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const PLANNING_COLUMNS = [
  { key: 'name', label: 'NAME' },
  { key: 'start_date', label: 'START' },
  { key: 'end_date', label: 'END' },
  { key: 'id', label: 'ID' },
];

async function collectionList(ctx, kind) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/${kind}/`);
  return { project, rows: data?.results ?? [] };
}

async function findByName(ctx, projectId, kind, name) {
  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(projectId)}/${kind}/`, {
    fields: ['id', 'name'],
  });
  const rows = data?.results ?? [];
  const hit = rows.find((r) => String(r.name).toLowerCase() === String(name).toLowerCase());
  if (!hit) {
    throw new CybError(
      EXIT.NOT_FOUND,
      `no such ${kind.replace(/s$/, '')}: ${name}`,
      rows.length ? `valid: ${rows.map((r) => r.name).join(', ')}` : `no ${kind} exist yet`,
    );
  }
  return hit;
}

export async function cycleList(ctx) {
  const { rows } = await collectionList(ctx, 'cycles');
  emit(rows, { mode: ctx.mode, columns: PLANNING_COLUMNS, stdout: ctx.streams.stdout });
}

export async function cycleCreate(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  if (!ctx.values.name) {
    throw new CybError(
      EXIT.GENERAL,
      'cycle needs a name',
      'pass --name, e.g. cyb cycle create CYB --name "Sprint 1" --start 2026-08-01 --end 2026-08-14',
    );
  }

  const body = { name: ctx.values.name };
  if (ctx.values.start) body.start_date = ctx.values.start;
  if (ctx.values.end) body.end_date = ctx.values.end;

  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/cycles/`,
    { body },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function cycleAddItem(ctx) {
  if (!ctx.values.cycle) {
    throw new CybError(
      EXIT.GENERAL,
      'no cycle given',
      'pass --cycle, e.g. cyb cycle add-item CYB-42 --cycle "Sprint 1"',
    );
  }
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb cycle add-item CYB-42 --cycle "Sprint 1"');

  const item = await ctx.resolver.item(ref);
  const cycle = await findByName(ctx, item.projectId, 'cycles', ctx.values.cycle);

  await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(item.projectId)}/cycles/${cycle.id}/cycle-issues/`,
    { body: { issues: [item.id] } },
  );
  emit({ added: ref, cycle: cycle.name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function cycleRemove(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const name = ctx.positionals[1];
  if (!name) throw new CybError(EXIT.GENERAL, 'no cycle given', 'example: cyb cycle delete CYB "Sprint 1" --yes');

  const cycle = await findByName(ctx, project.id, 'cycles', name);
  requireConfirmation(ctx, { action: 'delete cycle', targets: [name] });

  await ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/cycles/${cycle.id}/`);
  emit({ deleted: name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function moduleList(ctx) {
  const { rows } = await collectionList(ctx, 'modules');
  emit(rows, { mode: ctx.mode, columns: PLANNING_COLUMNS, stdout: ctx.streams.stdout });
}

export async function moduleCreate(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  if (!ctx.values.name) {
    throw new CybError(EXIT.GENERAL, 'module needs a name', 'pass --name, e.g. cyb module create CYB --name Auth');
  }

  const body = { name: ctx.values.name };
  if (ctx.values.description) body.description = ctx.values.description;

  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(project.id)}/modules/`,
    { body },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function moduleAddItem(ctx) {
  if (!ctx.values.module) {
    throw new CybError(
      EXIT.GENERAL,
      'no module given',
      'pass --module, e.g. cyb module add-item CYB-42 --module Auth',
    );
  }
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb module add-item CYB-42 --module Auth');

  const item = await ctx.resolver.item(ref);
  const mod = await findByName(ctx, item.projectId, 'modules', ctx.values.module);

  await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(item.projectId)}/modules/${mod.id}/module-issues/`,
    { body: { issues: [item.id] } },
  );
  emit({ added: ref, module: mod.name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}

export async function moduleRemove(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const name = ctx.positionals[1];
  if (!name) throw new CybError(EXIT.GENERAL, 'no module given', 'example: cyb module delete CYB Auth --yes');

  const mod = await findByName(ctx, project.id, 'modules', name);
  requireConfirmation(ctx, { action: 'delete module', targets: [name] });

  await ctx.client.request('DELETE', `${ctx.client.projectPath(project.id)}/modules/${mod.id}/`);
  emit({ deleted: name }, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs` — add the import and two groups:

```js
import * as planning from './commands/planning.mjs';
```

```js
  cycle: {
    list: { summary: 'List cycles', options: {}, handler: planning.cycleList },
    create: {
      summary: 'Create a cycle',
      options: { name: { type: 'string' }, start: { type: 'string' }, end: { type: 'string' } },
      handler: planning.cycleCreate,
    },
    'add-item': {
      summary: 'Add an existing work item to a cycle',
      options: { cycle: { type: 'string' } },
      handler: planning.cycleAddItem,
    },
    delete: { summary: 'Delete a cycle (needs --yes)', options: {}, handler: planning.cycleRemove },
  },
  module: {
    list: { summary: 'List modules', options: {}, handler: planning.moduleList },
    create: {
      summary: 'Create a module',
      options: { name: { type: 'string' }, description: { type: 'string' } },
      handler: planning.moduleCreate,
    },
    'add-item': {
      summary: 'Add an existing work item to a module',
      options: { module: { type: 'string' } },
      handler: planning.moduleAddItem,
    },
    delete: { summary: 'Delete a module (needs --yes)', options: {}, handler: planning.moduleRemove },
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/planning.test.mjs`
Expected: PASS — 11 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/commands/planning.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/planning.test.mjs
git commit -m "feat(cyb): add cycle and module planning commands"
```

---

### Task 13: Comment Commands

**Files:**
- Create: `.claude/skills/cybernetics/src/commands/comment.mjs`
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (add the `comment` group)
- Test: `.claude/skills/cybernetics/tests/comment.test.mjs`

**Interfaces:**
- Consumes: `ctx`
- Produces: `commentList(ctx)`, `commentAdd(ctx)`, `COMMENT_COLUMNS`

Comments live at `/issues/{id}/comments/` and take `comment_html`.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/comment.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commentList, commentAdd } from '../src/commands/comment.mjs';
import { makeCtx } from './helpers/ctx.mjs';
import { EXIT } from '../src/errors.mjs';

test('comment list fetches the comments for a resolved item', async () => {
  const { ctx, calls, outText } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 200, body: { results: [{ id: 'c1', comment_html: '<p>hi</p>', created_at: '2026-08-17T00:00:00Z' }] } },
  ], { positionals: ['CYB-42'] });
  await commentList(ctx);
  assert.match(calls.at(-1).url, /comments/);
  assert.equal(JSON.parse(outText()).length, 1);
});

test('comment add posts comment_html wrapped from plain text', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 201, body: { id: 'c1' } },
  ], { positionals: ['CYB-42', 'looks good'] });
  await commentAdd(ctx);
  assert.deepEqual(JSON.parse(calls.at(-1).init.body), { comment_html: '<p>looks good</p>' });
});

test('comment add requires text', async () => {
  const { ctx } = makeCtx([], { positionals: ['CYB-42'] });
  await assert.rejects(() => commentAdd(ctx), (err) => err.code === EXIT.GENERAL);
});

test('comment add escapes HTML metacharacters in the supplied text', async () => {
  const { ctx, calls } = makeCtx([
    { status: 200, body: { results: [{ id: 'item-uuid', sequence_id: 42 }] } },
    { status: 201, body: { id: 'c1' } },
  ], { positionals: ['CYB-42', 'a < b & c'] });
  await commentAdd(ctx);
  const body = JSON.parse(calls.at(-1).init.body);
  assert.equal(body.comment_html, '<p>a &lt; b &amp; c</p>');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/comment.test.mjs`
Expected: FAIL — `Cannot find module '../src/commands/comment.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/commands/comment.mjs`:

```js
import { emit } from '../format.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const COMMENT_COLUMNS = [
  { key: 'created_at', label: 'WHEN' },
  { key: 'text', label: 'COMMENT' },
];

export function escapeHtml(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function stripHtml(html) {
  return String(html ?? '').replace(/<[^>]*>/g, '').trim();
}

function itemRef(ctx) {
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb comment list CYB-42');
  return ref;
}

export async function commentList(ctx) {
  const item = await ctx.resolver.item(itemRef(ctx));
  const { data } = await ctx.client.request(
    'GET',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/comments/`,
  );
  const rows = (data?.results ?? []).map((c) => ({
    id: c.id,
    created_at: c.created_at,
    text: stripHtml(c.comment_html),
  }));
  emit(rows, { mode: ctx.mode, columns: COMMENT_COLUMNS, stdout: ctx.streams.stdout });
}

export async function commentAdd(ctx) {
  const ref = itemRef(ctx);
  const text = ctx.positionals.slice(1).join(' ').trim();
  if (!text) {
    throw new CybError(
      EXIT.GENERAL,
      'no comment text given',
      'example: cyb comment add CYB-42 "looks good"',
    );
  }

  const item = await ctx.resolver.item(ref);
  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/comments/`,
    { body: { comment_html: `<p>${escapeHtml(text)}</p>` } },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs`:

```js
import * as comment from './commands/comment.mjs';
```

```js
  comment: {
    list: { summary: 'List comments on a work item', options: {}, handler: comment.commentList },
    add: { summary: 'Add a comment to a work item', options: {}, handler: comment.commentAdd },
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/comment.test.mjs`
Expected: PASS — 4 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/commands/comment.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/comment.test.mjs
git commit -m "feat(cyb): add comment list and add with HTML escaping"
```

---

### Task 14: Composite Commands (`board`, `my`, `search`)

**Files:**
- Create: `.claude/skills/cybernetics/src/commands/composite.mjs`
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (add `board`, `my`, `search` groups)
- Test: `.claude/skills/cybernetics/tests/composite.test.mjs`

**Interfaces:**
- Consumes: `decorate`, `LIST_FIELDS`, `projectRef`, `limitOf` from `src/commands/item.mjs`
- Produces: `board(ctx)`, `my(ctx)`, `search(ctx)`, `groupByState(rows, states)`

`my` filters client-side on the `assignees` array returned by the projection, so it stays correct regardless of whether the server honours the `assignees` query param. `search` filters client-side on `name` for the same reason — no server-side search endpoint is confirmed on v2.6.3.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/composite.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { board, my, search, groupByState } from '../src/commands/composite.mjs';
import { makeCtx, STATE_LIST, UUID_STATE_PROGRESS, UUID_STATE_BACKLOG } from './helpers/ctx.mjs';

test('groupByState buckets rows under their state group in canonical order', () => {
  const grouped = groupByState(
    [
      { ref: 'CYB-1', state: UUID_STATE_PROGRESS },
      { ref: 'CYB-2', state: UUID_STATE_BACKLOG },
      { ref: 'CYB-3', state: UUID_STATE_BACKLOG },
    ],
    STATE_LIST,
  );
  assert.deepEqual(Object.keys(grouped), ['Backlog', 'In Progress', 'Done']);
  assert.equal(grouped.Backlog.length, 2);
  assert.equal(grouped['In Progress'].length, 1);
  assert.equal(grouped.Done.length, 0);
});

test('board fetches once and emits grouped counts', async () => {
  const { ctx, calls, outText } = makeCtx([
    {
      status: 200,
      body: {
        total_count: 2,
        results: [
          { id: 'a', sequence_id: 1, name: 'x', state: UUID_STATE_BACKLOG, priority: 'low' },
          { id: 'b', sequence_id: 2, name: 'y', state: UUID_STATE_PROGRESS, priority: 'high' },
        ],
        next_page_results: false,
      },
    },
  ], { positionals: ['CYB'] });
  await board(ctx);
  assert.equal(calls.length, 1);
  const report = JSON.parse(outText());
  assert.equal(report.Backlog.length, 1);
  assert.equal(report['In Progress'].length, 1);
});

test('my filters to items assigned to the current user', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 1, results: [{ id: 'p1', identifier: 'CYB', name: 'Core' }] } },
    {
      status: 200,
      body: {
        results: [
          { id: 'a', sequence_id: 1, name: 'mine', state: UUID_STATE_BACKLOG, assignees: ['me-uuid'] },
          { id: 'b', sequence_id: 2, name: 'theirs', state: UUID_STATE_BACKLOG, assignees: ['other'] },
        ],
        next_page_results: false,
      },
    },
  ], { positionals: [], warmCache: false });
  await my(ctx);
  const rows = JSON.parse(outText());
  assert.equal(rows.length, 1);
  assert.equal(rows[0].name, 'mine');
});

test('my reports an empty result set without error', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 0, results: [] } },
  ], { positionals: [], warmCache: false, mode: 'plain' });
  await my(ctx);
  assert.match(outText(), /no results|no work items/i);
});

test('search matches names case-insensitively', async () => {
  const { ctx, outText } = makeCtx([
    {
      status: 200,
      body: {
        results: [
          { id: 'a', sequence_id: 1, name: 'Fix AUTH timeout', state: UUID_STATE_BACKLOG },
          { id: 'b', sequence_id: 2, name: 'Update docs', state: UUID_STATE_BACKLOG },
        ],
        next_page_results: false,
      },
    },
  ], { positionals: ['auth'], values: { project: 'CYB' } });
  await search(ctx);
  const rows = JSON.parse(outText());
  assert.equal(rows.length, 1);
  assert.match(rows[0].name, /Fix AUTH/);
});

test('search requires a query', async () => {
  const { ctx } = makeCtx([], { positionals: [] });
  await assert.rejects(() => search(ctx), (err) => /query/.test(err.message));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/composite.test.mjs`
Expected: FAIL — `Cannot find module '../src/commands/composite.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/commands/composite.mjs`:

```js
import { emit, renderTable } from '../format.mjs';
import { decorate, LIST_FIELDS, ITEM_COLUMNS, projectRef, limitOf } from './item.mjs';
import { CybError, EXIT } from '../errors.mjs';

const GROUP_ORDER = ['backlog', 'unstarted', 'started', 'completed', 'cancelled'];

export function groupByState(rows, states) {
  const ordered = [...states].sort(
    (a, b) => GROUP_ORDER.indexOf(a.group) - GROUP_ORDER.indexOf(b.group),
  );
  const byId = new Map(ordered.map((s) => [s.id, s.name]));

  const grouped = {};
  for (const state of ordered) grouped[state.name] = [];

  for (const row of rows) {
    const name = byId.get(row.state) ?? row.state;
    grouped[name] ??= [];
    grouped[name].push(row);
  }
  return grouped;
}

export async function board(ctx) {
  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  const limit = limitOf(ctx);

  const { data } = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/issues/`, {
    query: { per_page: Math.max(limit, 100) },
    fields: LIST_FIELDS,
  });

  const raw = data?.results ?? [];
  const grouped = groupByState(raw, states);

  if (ctx.mode === 'json') {
    const out = {};
    for (const [name, items] of Object.entries(grouped)) {
      out[name] = decorate(items, { project, states });
    }
    emit(out, { mode: ctx.mode, stdout: ctx.streams.stdout });
    return;
  }

  const lines = [];
  for (const [name, items] of Object.entries(grouped)) {
    lines.push(`${name} (${items.length})`);
    for (const row of decorate(items, { project, states })) {
      lines.push(`  ${row.ref}  ${row.name}`);
    }
    lines.push('');
  }
  ctx.streams.stdout.write(`${lines.join('\n').trimEnd()}\n`);
}

export async function my(ctx) {
  const me = await ctx.resolver.me();
  const limit = limitOf(ctx);

  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/projects/`, {
    fields: ['id', 'identifier', 'name'],
  });
  const projects = data?.results ?? [];

  const rows = [];
  for (const project of projects) {
    const states = await ctx.resolver.statesFor(project.id);
    const page = await ctx.client.request('GET', `${ctx.client.projectPath(project.id)}/issues/`, {
      query: { assignees: me.id, per_page: limit },
      fields: LIST_FIELDS,
    });
    const mine = (page.data?.results ?? []).filter((item) =>
      Array.isArray(item.assignees) && item.assignees.includes(me.id),
    );
    rows.push(...decorate(mine, { project, states }));
    if (rows.length >= limit) break;
  }

  const trimmed = rows.slice(0, limit);

  if (ctx.mode === 'json') {
    emit(trimmed, { mode: ctx.mode, stdout: ctx.streams.stdout });
    return;
  }
  ctx.streams.stdout.write(`${renderTable(trimmed, ITEM_COLUMNS, { mode: ctx.mode })}\n`);
}

export async function search(ctx) {
  const query = ctx.positionals[0];
  if (!query) {
    throw new CybError(EXIT.GENERAL, 'no search query given', 'example: cyb search "auth" --project CYB');
  }

  const project = await ctx.resolver.project(projectRef(ctx));
  const states = await ctx.resolver.statesFor(project.id);
  const limit = limitOf(ctx);
  const needle = query.toLowerCase();

  const matches = [];
  for await (const item of ctx.client.paginate(`${ctx.client.projectPath(project.id)}/issues/`, {
    fields: LIST_FIELDS,
    limit: 500,
  })) {
    if (String(item.name).toLowerCase().includes(needle)) matches.push(item);
    if (matches.length >= limit) break;
  }

  const rows = decorate(matches, { project, states });

  if (ctx.mode === 'json') {
    emit(rows, { mode: ctx.mode, stdout: ctx.streams.stdout });
    return;
  }
  ctx.streams.stdout.write(`${renderTable(rows, ITEM_COLUMNS, { mode: ctx.mode })}\n`);
}
```

Note: `search` reads at most 500 items — a deliberate cap so a large project cannot exhaust the 60 req/min budget. Because it is a cap, `renderTable` showing fewer rows than exist is expected; the SKILL.md recipes tell the agent to narrow with `--project` rather than raise it.

Modify `.claude/skills/cybernetics/src/cli.mjs`:

```js
import * as composite from './commands/composite.mjs';
```

```js
  board: {
    __default: { summary: 'Show a project as a kanban summary', options: {}, handler: composite.board },
  },
  my: {
    __default: { summary: 'List work items assigned to you', options: {}, handler: composite.my },
  },
  search: {
    __default: { summary: 'Search work item names in a project', options: {}, handler: composite.search },
  },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/composite.test.mjs`
Expected: PASS — 6 tests

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/cybernetics/src/commands/composite.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/composite.test.mjs
git commit -m "feat(cyb): add board, my and search composite commands"
```

---

### Task 15: Setup Commands (`init`, `sync`)

**Files:**
- Create: `.claude/skills/cybernetics/src/commands/setup.mjs`
- Modify: `.claude/skills/cybernetics/src/cli.mjs` (add `init`, `sync` groups)
- Test: `.claude/skills/cybernetics/tests/setup.test.mjs`

**Interfaces:**
- Consumes: `saveConfig`, `CONFIG_PATH`, `fingerprint` from `src/config.mjs`; `emptyCache`, `saveCache` from `src/cache.mjs`
- Produces: `init(ctx)`, `sync(ctx)`

`init` is non-interactive: it writes the resolved configuration (base URL, workspace, token, optional default project) to `~/.cybernetics/config.json` at mode 0600. It never prints the token. `sync` discards the cache and refetches projects, states and members.

- [ ] **Step 1: Write the failing test**

Create `.claude/skills/cybernetics/tests/setup.test.mjs`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, existsSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { init, sync } from '../src/commands/setup.mjs';
import { makeCtx, UUID_PROJECT } from './helpers/ctx.mjs';

function tmpFile(name) {
  return join(mkdtempSync(join(tmpdir(), 'cyb-setup-')), name);
}

test('init writes config with 0600 and reports only a fingerprint', async () => {
  const configPath = tmpFile('config.json');
  const { ctx, outText } = makeCtx([], { values: { 'config-path': configPath } });
  ctx.config.token = 'plane_api_ffffffffffffffffffffffffffffbeef';
  ctx.configPath = configPath;

  await init(ctx);

  assert.ok(existsSync(configPath));
  assert.equal(statSync(configPath).mode & 0o777, 0o600);
  assert.equal(JSON.parse(readFileSync(configPath, 'utf8')).workspace, 'cybernetics');
  assert.ok(!outText().includes('ffffffffffff'));
  assert.match(outText(), /beef/);
});

test('init records the default project when one is set', async () => {
  const configPath = tmpFile('config.json');
  const { ctx } = makeCtx([], { values: { project: 'CYB' } });
  ctx.config.token = 'tok-value-1234';
  ctx.config.defaultProject = 'CYB';
  ctx.configPath = configPath;

  await init(ctx);
  assert.equal(JSON.parse(readFileSync(configPath, 'utf8')).defaultProject, 'CYB');
});

test('init never writes the token into the repo path it was given', async () => {
  const configPath = tmpFile('config.json');
  const { ctx } = makeCtx([]);
  ctx.config.token = 'plane_api_secret_value_here';
  ctx.configPath = configPath;
  await init(ctx);
  assert.equal(JSON.parse(readFileSync(configPath, 'utf8')).token, 'plane_api_secret_value_here');
  assert.ok(configPath.startsWith(tmpdir()));
});

test('sync clears stale cache entries and refetches projects', async () => {
  const { ctx, outText } = makeCtx([
    { status: 200, body: { id: 'me-uuid', display_name: 'avarile' } },
    { status: 200, body: { total_count: 1, results: [{ id: UUID_PROJECT, identifier: 'CYB', name: 'Core' }] } },
    { status: 200, body: { results: [{ id: 's1', name: 'Backlog', group: 'backlog' }] } },
    { status: 200, body: { results: [{ id: 'm1', display_name: 'avarile', email: 'a@b.c' }] } },
  ]);
  ctx.cache.projects.STALE = { id: 'gone', name: 'Gone', fetchedAt: '2020-01-01T00:00:00Z' };

  await sync(ctx);

  assert.equal(ctx.cache.projects.STALE, undefined);
  assert.equal(ctx.cache.projects.CYB.id, UUID_PROJECT);
  assert.match(outText(), /CYB|1/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .claude/skills/cybernetics && node --test tests/setup.test.mjs`
Expected: FAIL — `Cannot find module '../src/commands/setup.mjs'`

- [ ] **Step 3: Write the implementation**

Create `.claude/skills/cybernetics/src/commands/setup.mjs`:

```js
import { saveConfig, CONFIG_PATH, fingerprint } from '../config.mjs';
import { emptyCache, projectBucket } from '../cache.mjs';
import { emit } from '../format.mjs';

export async function init(ctx) {
  const configPath = ctx.configPath ?? CONFIG_PATH;

  const record = {
    baseUrl: ctx.config.baseUrl,
    workspace: ctx.config.workspace,
    token: ctx.config.token,
    defaults: { limit: ctx.config.defaults.limit },
  };
  if (ctx.config.defaultProject) record.defaultProject = ctx.config.defaultProject;

  saveConfig(record, { configPath });

  emit(
    {
      wrote: configPath,
      workspace: record.workspace,
      baseUrl: record.baseUrl,
      token: fingerprint(record.token),
      defaultProject: record.defaultProject ?? null,
    },
    { mode: ctx.mode, stdout: ctx.streams.stdout },
  );
}

export async function sync(ctx) {
  const fresh = emptyCache(ctx.config.workspace);
  ctx.cache.projects = fresh.projects;
  ctx.cache.byProject = fresh.byProject;
  ctx.cache.members = {};
  ctx.cache.me = null;

  const me = await ctx.resolver.me();

  const { data } = await ctx.client.request('GET', `${ctx.client.wsPath}/projects/`, {
    fields: ['id', 'identifier', 'name'],
  });
  const projects = data?.results ?? [];
  const stamp = new Date().toISOString();

  for (const project of projects) {
    ctx.cache.projects[String(project.identifier).toUpperCase()] = {
      id: project.id,
      name: project.name,
      fetchedAt: stamp,
    };
    projectBucket(ctx.cache, project.id);
    await ctx.resolver.statesFor(project.id);
  }

  const members = await ctx.client.request('GET', `${ctx.client.wsPath}/members/`);
  const memberRows = members.data?.results ?? members.data ?? [];
  ctx.cache.members = {};
  for (const member of memberRows) {
    if (member.display_name) ctx.cache.members[member.display_name.toLowerCase()] = member.id;
    if (member.email) ctx.cache.members[member.email.toLowerCase()] = member.id;
  }

  ctx.save();

  emit(
    {
      user: me.display_name,
      projects: projects.map((p) => p.identifier),
      members: memberRows.length,
      calls: ctx.client.callCount,
    },
    { mode: ctx.mode, stdout: ctx.streams.stdout },
  );
}
```

Modify `.claude/skills/cybernetics/src/cli.mjs` — add the import, the groups, and pass `configPath` into the context.

```js
import * as setup from './commands/setup.mjs';
```

```js
  init: {
    __default: { summary: 'Write ~/.cybernetics/config.json from the current environment', options: {}, handler: setup.init },
  },
  sync: {
    __default: { summary: 'Discard and rebuild the resolver cache', options: {}, handler: setup.sync },
  },
```

In `buildContext`, add `configPath` to the returned object so `init` can honour a test override:

```js
  return {
    config, client, cache, resolver, save, mode, streams, values, positionals,
    configPath: deps.configPath ?? CONFIG_PATH,
  };
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .claude/skills/cybernetics && node --test tests/setup.test.mjs`
Expected: PASS — 4 tests

- [ ] **Step 5: Run the full Phase 1 + 2 suite**

Run: `cd .claude/skills/cybernetics && node --test`
Expected: PASS — 159 tests across 17 files, no network required

- [ ] **Step 6: Smoke test against the live instance**

Run:
```bash
cd .claude/skills/cybernetics
export CYB_TOKEN='<the real token>'
node bin/cyb doctor
node bin/cyb project list
node bin/cyb project create --name "Cybernetics Core" --identifier CYB
node bin/cyb item create CYB --name "First work item" --priority high
node bin/cyb item list CYB
node bin/cyb board CYB
node bin/cyb item move CYB-1 "In Progress"
node bin/cyb my
node bin/cyb item delete CYB-1        # expect exit 2, refused
node bin/cyb item delete CYB-1 --yes  # expect success
```
Expected: each command succeeds; the refusal prints a `--yes` hint and exits 2. Leave the `CYB` project in place if you want it, or remove it with `node bin/cyb project delete CYB --yes`.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/cybernetics/src/commands/setup.mjs \
        .claude/skills/cybernetics/src/cli.mjs \
        .claude/skills/cybernetics/tests/setup.test.mjs
git commit -m "feat(cyb): add init and sync setup commands"
```

---

## Phase 2 Exit Criteria

- Every command in the spec's command surface is implemented and unit-tested.
- `node --test` passes with no network and no `CYB_TOKEN`.
- Destructive commands refuse without `--yes` and issue no API call when refusing.
- Invalid priorities and unresolvable names fail before a request, with hints naming the valid values.
- The live smoke test in Task 15 Step 6 completes end to end.

Phase 3 (`docs/superpowers/plans/2026-08-17-cybernetics-phase-3-interfaces.md`) adds the REPL, the skill documentation, and integration tests.
