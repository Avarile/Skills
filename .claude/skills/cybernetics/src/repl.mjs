import readline from 'node:readline';
import { buildContext, parseInvocation, dispatch, renderHelp } from './cli.mjs';
import { projectBucket } from './cache.mjs';
import { pickMode, renderError } from './format.mjs';

// The REPL contains no API logic of its own: tokenize() and translate() turn
// a typed line into the same argv the plain CLI accepts, and startRepl()
// dispatches it through the very same parseInvocation/dispatch seam main()
// uses (cli.mjs). That keeps exactly one tested code path for both the CLI
// and the interactive session.

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

// Reads only what is already cached — see the module comment on
// startRepl()'s `cd` handling for why. No argument here is a client or ctx,
// which is what makes "the completer never issues a request" true by
// construction rather than by discipline: there is nothing here it could
// fetch with.
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

// Ruling (Phase 3 controller, recorded in task-16-brief.md): `cd <PROJECT>`
// warms that project's labels and items — the two regions `sync` (setup.mjs)
// deliberately leaves cold — rather than having `sync` fetch labels for
// every project workspace-wide. `cd` is an explicit, user-initiated context
// switch where one or two extra requests are expected and affordable;
// taxing every `sync` with a request per project for a REPL-only benefit is
// not. This is the only place in the REPL that issues a request outside of
// a translated command — makeCompleter() above must never do so.
//
// A project that doesn't resolve propagates (the caller decides whether to
// switch state.project at all). Once the project itself is confirmed to
// exist, the labels/items warm-up is best-effort: a rate limit or network
// blip here must not block switching projects, so failures there are
// swallowed — the completer simply has nothing to offer until a later
// successful warm-up.
async function warmProject(ctx, key) {
  const project = await ctx.resolver.project(key);
  const bucket = projectBucket(ctx.cache, project.id);

  try {
    const { data: labelData } = await ctx.client.request(
      'GET',
      `${ctx.client.projectPath(project.id)}/labels/`,
      { fields: ['id', 'name'] },
    );
    const labels = labelData?.results ?? [];
    bucket.labels = {};
    for (const label of labels) bucket.labels[label.name.toLowerCase()] = label.id;
    bucket.labelsFetchedAt = ctx.resolver.stamp();

    const { data: itemData } = await ctx.client.request(
      'GET',
      `${ctx.client.projectPath(project.id)}/issues/`,
      { fields: ['id', 'sequence_id'], query: { per_page: ctx.config.defaults.limit } },
    );
    const items = itemData?.results ?? [];
    for (const item of items) bucket.items[item.sequence_id] = item.id;
    bucket.itemsFetchedAt = ctx.resolver.stamp();

    ctx.save();
  } catch {
    // Best-effort, per the ruling above.
  }

  return project;
}

// One-shot per process, unlike main(): buildContext() runs exactly once
// here, producing a single Client (and therefore a single `remaining`/
// `resetAt` pair) and a single Resolver/cache that every line for the rest
// of the session shares. That's the whole point of the Task 16 pre-work in
// cli.mjs — a REPL built on calling main() per line would rebuild both on
// every line and could never track budget across commands. Each line still
// gets its own `values`/`positionals` (from parseInvocation) and its own
// `mode` (a line can pass --json even if the session didn't start with it),
// layered onto the one shared ctx via dispatch().
export async function startRepl(deps = {}) {
  const input = deps.input ?? process.stdin;
  const output = deps.output ?? process.stdout;
  // Defaults to `output` for stdout (an interactive session has one visible
  // stream, unlike the plain CLI's stdout/stderr split) but real stderr
  // otherwise — not `output` for both — so a dispatched `--json` command's
  // truncation notices still land on stderr, same as the one-shot CLI, and
  // --json's stdout stays a clean parseable payload even inside a session.
  const streams = deps.streams ?? { stdout: output, stderr: process.stderr };

  const ctx = buildContext({ values: {}, positionals: [], deps: { ...deps, streams } });

  const state = {
    project: ctx.config.defaultProject ?? Object.keys(ctx.cache.projects ?? {})[0] ?? null,
  };

  const rl = readline.createInterface({
    input,
    output,
    prompt: '',
    completer: makeCompleter(state, ctx.cache),
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
      try {
        await warmProject(ctx, result.setProject);
        state.project = result.setProject;
        setPrompt();
      } catch (err) {
        output.write(`${renderError(err, { mode: 'plain' })}\n`);
      }
    } else if (result.argv) {
      try {
        const invocation = parseInvocation(result.argv);
        if (invocation.help) {
          output.write(`${renderHelp(invocation.group, invocation.action)}\n`);
        } else {
          const lineCtx = {
            ...ctx,
            values: invocation.values,
            positionals: invocation.positionals,
            mode: pickMode({ json: Boolean(invocation.values.json), isTTY: Boolean(streams.stdout.isTTY) }),
          };
          await dispatch(invocation, lineCtx);
        }
      } catch (err) {
        output.write(`${renderError(err, { mode: 'plain' })}\n`);
      }
    }

    // A synthetic (non-TTY) input stream can hit EOF and auto-close the
    // interface between the time a 'line' event was queued and the time
    // this loop body finishes handling it — the for-await iterator still
    // yields the already-buffered line, but prompting into an interface
    // that has since closed throws ERR_USE_AFTER_CLOSE. A real terminal
    // never produces lines faster than a human types them, so this only
    // bites synthetic input (tests, piped scripts) — guard rather than crash.
    if (!rl.closed) rl.prompt();
  }

  if (!rl.closed) rl.close();
  return 0;
}
