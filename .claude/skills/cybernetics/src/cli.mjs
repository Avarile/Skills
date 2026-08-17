import { parseArgs } from 'node:util';
import { loadConfig, CONFIG_PATH } from './config.mjs';
import { loadCache, saveCache, CACHE_PATH } from './cache.mjs';
import { Client } from './client.mjs';
import { Resolver } from './resolve.mjs';
import { pickMode, renderError } from './format.mjs';
import { CybError, EXIT } from './errors.mjs';
import { doctor } from './commands/doctor.mjs';
import * as project from './commands/project.mjs';
import * as item from './commands/item.mjs';
import * as meta from './commands/meta.mjs';
import * as planning from './commands/planning.mjs';
import * as comment from './commands/comment.mjs';
import * as composite from './commands/composite.mjs';
import * as setup from './commands/setup.mjs';

export const GLOBAL_OPTIONS = {
  json: { type: 'boolean', default: false },
  full: { type: 'boolean', default: false },
  limit: { type: 'string' },
  yes: { type: 'boolean', default: false },
  project: { type: 'string' },
  'no-cache': { type: 'boolean', default: false },
  verbose: { type: 'boolean', default: false },
  help: { type: 'boolean', default: false },
};

export const REGISTRY = {
  doctor: {
    __default: {
      summary: 'Check auth, workspace access and rate-limit budget',
      options: { probe: { type: 'boolean', default: false } },
      handler: doctor,
      positionals: [],
    },
  },
  project: {
    list: { summary: 'List all projects', options: {}, handler: project.list, positionals: [] },
    show: { summary: 'Show one project', options: {}, handler: project.show, positionals: ['project'] },
    create: {
      summary: 'Create a project',
      options: {
        name: { type: 'string' },
        identifier: { type: 'string' },
        description: { type: 'string' },
      },
      handler: project.create,
      positionals: [],
    },
    update: {
      summary: 'Update a project',
      options: { name: { type: 'string' }, description: { type: 'string' } },
      handler: project.update,
      positionals: ['project'],
    },
    delete: { summary: 'Delete a project (needs --yes)', options: {}, handler: project.remove, positionals: ['project'] },
  },
  item: {
    list: {
      summary: 'List work items in a project',
      options: {
        state: { type: 'string' },
        priority: { type: 'string' },
        assignee: { type: 'string' },
      },
      handler: item.list,
      positionals: ['project'],
    },
    show: { summary: 'Show one work item', options: {}, handler: item.show, positionals: ['itemRef'] },
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
      positionals: ['project'],
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
      positionals: ['itemRef'],
    },
    move: { summary: 'Move a work item to a state', options: {}, handler: item.move, positionals: ['itemRef', 'state'] },
    assign: { summary: 'Assign a work item to a member', options: {}, handler: item.assign, positionals: ['itemRef', 'member'] },
    delete: { summary: 'Delete a work item (needs --yes)', options: {}, handler: item.remove, positionals: ['itemRef'] },
  },
  state: {
    list: { summary: 'List workflow states in a project', options: {}, handler: meta.stateList, positionals: ['project'] },
  },
  label: {
    list: { summary: 'List labels in a project', options: {}, handler: meta.labelList, positionals: ['project'] },
    create: {
      summary: 'Create a label',
      options: { name: { type: 'string' }, color: { type: 'string' } },
      handler: meta.labelCreate,
      positionals: ['project'],
    },
    delete: { summary: 'Delete a label (needs --yes)', options: {}, handler: meta.labelRemove, positionals: ['project', 'label'] },
  },
  member: {
    list: { summary: 'List workspace members', options: {}, handler: meta.memberList, positionals: [] },
  },
  cycle: {
    list: { summary: 'List cycles', options: {}, handler: planning.cycleList, positionals: ['project'] },
    create: {
      summary: 'Create a cycle',
      options: { name: { type: 'string' }, start: { type: 'string' }, end: { type: 'string' } },
      handler: planning.cycleCreate,
      positionals: ['project'],
    },
    'add-item': {
      summary: 'Add an existing work item to a cycle',
      options: { cycle: { type: 'string' } },
      handler: planning.cycleAddItem,
      positionals: ['itemRef'],
    },
    delete: { summary: 'Delete a cycle (needs --yes)', options: {}, handler: planning.cycleRemove, positionals: ['project', 'cycle'] },
  },
  module: {
    list: { summary: 'List modules', options: {}, handler: planning.moduleList, positionals: ['project'] },
    create: {
      summary: 'Create a module',
      options: { name: { type: 'string' }, description: { type: 'string' } },
      handler: planning.moduleCreate,
      positionals: ['project'],
    },
    'add-item': {
      summary: 'Add an existing work item to a module',
      options: { module: { type: 'string' } },
      handler: planning.moduleAddItem,
      positionals: ['itemRef'],
    },
    delete: { summary: 'Delete a module (needs --yes)', options: {}, handler: planning.moduleRemove, positionals: ['project', 'module'] },
  },
  comment: {
    list: { summary: 'List comments on a work item', options: {}, handler: comment.commentList, positionals: ['itemRef'] },
    add: { summary: 'Add a comment to a work item', options: {}, handler: comment.commentAdd, positionals: ['itemRef', 'text'] },
  },
  // These three exist to defend the 60 req/min budget: each answers a
  // question ("state of this project?", "what's mine?", "where's that
  // item?") in one pass instead of the per-resource loop every other group
  // above would require. `takesPositional` tells parseInvocation() that the
  // first bare token is real positional data (a project ref or a search
  // query), not an attempted action name — see parseInvocation below.
  board: {
    __default: {
      summary: 'Show a project as a kanban summary',
      options: {},
      handler: composite.board,
      takesPositional: true,
      positionals: ['project'],
    },
  },
  my: {
    __default: { summary: 'List work items assigned to you', options: {}, handler: composite.my, positionals: [] },
  },
  search: {
    __default: {
      summary: 'Search work item names in a project',
      options: {},
      handler: composite.search,
      takesPositional: true,
      // The one action whose positional[0] is not a project ref — a query
      // instead. `project?` marks the second slot optional: it falls back
      // to --project / the configured default when omitted. A REPL that
      // otherwise injects its current project as positional[0] must read
      // this metadata rather than assume the usual shape.
      positionals: ['query', 'project?'],
    },
  },
  init: {
    __default: { summary: 'Write ~/.cybernetics/config.json from the current environment', options: {}, handler: setup.init, positionals: [] },
  },
  sync: {
    __default: { summary: 'Discard and rebuild the resolver cache', options: {}, handler: setup.sync, positionals: [] },
  },
  ui: {
    __default: {
      summary: 'Interactive session with a persistent project context',
      options: {},
      handler: null,
      positionals: [],
    },
  },
};

export function renderHelp(group, action) {
  if (!group) {
    const lines = ['Usage: cyb <group> <action> [options]', '', 'Groups:'];
    for (const [name, actions] of Object.entries(REGISTRY)) {
      const summary = actions.__default?.summary ?? Object.keys(actions).join(', ');
      lines.push(`  ${name.padEnd(10)} ${summary}`);
    }
    lines.push('', 'Global options:');
    for (const flag of Object.keys(GLOBAL_OPTIONS)) lines.push(`  --${flag}`);
    lines.push('', 'Run `cyb <group> --help` for actions.');
    return lines.join('\n');
  }

  const actions = REGISTRY[group];
  if (!actions) return `unknown command group: ${group}`;

  const lines = [`Usage: cyb ${group} <action> [options]`, '', 'Actions:'];
  for (const [name, def] of Object.entries(actions)) {
    const label = name === '__default' ? '(default)' : name;
    const argSyntax = (def.positionals ?? []).map((p) => `<${p}>`).join(' ');
    const left = argSyntax ? `${label} ${argSyntax}` : label;
    lines.push(`  ${left.padEnd(28)} ${def.summary ?? ''}`);
  }
  if (action && actions[action]?.options) {
    const label = action === '__default' ? '(default)' : action;
    lines.push('', `Options for ${group} ${label}:`);
    for (const flag of Object.keys(actions[action].options)) lines.push(`  --${flag}`);
  }
  return lines.join('\n');
}

export function buildContext({ values, positionals, deps }) {
  const env = deps.env ?? process.env;
  const cwd = deps.cwd ?? process.cwd();
  const streams = deps.streams ?? { stdout: process.stdout, stderr: process.stderr };

  const config = loadConfig({ env, cwd, configPath: deps.configPath ?? CONFIG_PATH });
  if (values.project) config.defaultProject = values.project;

  if (!config.token) {
    throw new CybError(
      EXIT.AUTH,
      'no API token configured',
      'set CYB_TOKEN, or run: cyb init',
    );
  }

  const client = new Client({
    baseUrl: config.baseUrl,
    workspace: config.workspace,
    token: config.token,
    fetchImpl: deps.fetchImpl ?? globalThis.fetch,
    verbose: Boolean(values.verbose),
    logStream: streams.stderr,
    ...(deps.sleep ? { sleep: deps.sleep } : {}),
  });

  const cachePath = deps.cachePath ?? CACHE_PATH;
  const cache = loadCache({ path: cachePath, workspace: config.workspace });
  const SWALLOWED_SAVE_CODES = ['ENOENT', 'EACCES', 'EROFS', 'EPERM', 'ENOSPC'];
  const save = () => {
    try {
      saveCache(cache, { path: cachePath });
    } catch (err) {
      // A read-only or otherwise unwritable cache location must never fail a
      // command — but only for recognised filesystem errors. Anything else
      // (a bug in saveCache) should surface, not vanish silently.
      if (!SWALLOWED_SAVE_CODES.includes(err?.code)) throw err;
      if (values.verbose) {
        streams.stderr.write(`note: cache not saved (${err.code}): ${cachePath}\n`);
      }
    }
  };

  const resolver = new Resolver({ client, cache, persist: save, noCache: values['no-cache'] });

  const mode = pickMode({ json: values.json, isTTY: Boolean(streams.stdout.isTTY) });

  return {
    config, client, cache, resolver, save, mode, streams, values, positionals,
    configPath: deps.configPath ?? CONFIG_PATH,
  };
}

// A tolerant pre-parse used only to decide the error-path output mode. It
// must not throw on `--json=true` the way a strict, boolean-typed parseArgs
// pass would (ERR_PARSE_ARGS_INVALID_OPTION_VALUE) — an agent must always be
// able to tell whether to expect a JSON error envelope, even when the real
// dispatch below is about to fail on that very argument.
function detectJsonFlag(argv) {
  try {
    const { values } = parseArgs({ args: argv, strict: false, allowPositionals: true });
    return Boolean(values.json);
  } catch {
    return false;
  }
}

// Pure argv -> invocation translation. No I/O: it never touches config,
// cache, the network, or a Client — everything it needs is the static
// REGISTRY. Split out of main() (Task 16 pre-work) so the REPL can turn each
// typed line into the same shape main() would build, without re-parsing
// argv through a function that also reloads config/cache and rebuilds
// Client/Resolver on every call — see dispatch() and startRepl() in
// repl.mjs for why that distinction matters for the 60 req/min budget.
//
// Returns `{ help: true, group, action }` for every path that used to print
// help and return early (bare argv, `--help`/`help`, or a resolved action's
// own `--help`) — `group`/`action` are null for the top-level case. Otherwise
// returns `{ group, action, definition, values, positionals }`. Throws the
// same CybErrors main() used to throw directly for an unknown group, an
// unknown action, or a `__default` group invoked with no action and no
// positional data.
//
// A leading `--help` on a group with no `__default` (e.g. `cyb item --help`)
// is also a help invocation, with `action: null` — there is no default
// action for parseArgs to attach `values.help` to, so it has to be caught
// here rather than falling out of the parseArgs branch below the way
// `cyb item list --help` or a `__default` group's own `--help` do.
export function parseInvocation(argv) {
  const [group, ...rest] = argv;

  if (!group || group === '--help' || group === 'help') {
    return { help: true, group: null, action: null };
  }

  const actions = REGISTRY[group];
  if (!actions) {
    throw new CybError(
      EXIT.GENERAL,
      `unknown command group: ${group}`,
      `valid groups: ${Object.keys(REGISTRY).join(', ')}`,
    );
  }

  const maybeAction = rest[0];
  // A bare first token is normally ambiguous for a `__default` group: is it
  // an attempted (unknown) action name, or data for the default handler?
  // `doctor` takes no positional args, so treating any bare word as a
  // typo'd action (the `startsWith('-')` check below) is right for it.
  // `board`/`search` take a real leading positional (project ref / search
  // query) that is never a subcommand name, so their `__default` opts in
  // via `takesPositional` to always dispatch there instead.
  const usesDefault = Boolean(actions.__default) &&
    (!maybeAction || maybeAction.startsWith('-') || Boolean(actions.__default.takesPositional));

  // A group with no `__default` has no action for a bare leading `--help` to
  // resolve into — left alone it falls through to `actionName = '--help'`,
  // an unregistered action, and throws `unknown action`. Catch it here as a
  // request for the group's own help (action list + positional syntax) —
  // `__default` groups don't need this: `usesDefault` above already routes
  // their `--help` into the default action, where it reaches parseArgs and
  // sets `values.help` below, giving the more specific default-action help.
  if (!usesDefault && maybeAction === '--help') {
    return { help: true, group, action: null };
  }

  if (!maybeAction && !usesDefault) {
    throw new CybError(
      EXIT.GENERAL,
      `no action specified for ${group}`,
      `run: cyb ${group} --help`,
    );
  }

  const actionName = usesDefault ? '__default' : maybeAction;
  const argsForParse = usesDefault ? rest : rest.slice(1);

  const definition = actions[actionName];
  if (!definition) {
    throw new CybError(
      EXIT.GENERAL,
      `unknown action: ${group} ${maybeAction}`,
      `valid actions: ${Object.keys(actions).filter((k) => k !== '__default').join(', ') || '(none)'}`,
    );
  }

  const { values, positionals } = parseArgs({
    args: argsForParse,
    options: { ...GLOBAL_OPTIONS, ...(definition.options ?? {}) },
    allowPositionals: true,
  });

  if (values.help) {
    return { help: true, group, action: actionName };
  }

  return { group, action: actionName, definition, values, positionals };
}

// Runs an already-resolved invocation against an already-built ctx. This is
// the whole seam: it does not load config or cache, does not construct a
// Client or Resolver, and does not decide help or exit codes — callers that
// need those (main() below, or a REPL driving many invocations against one
// long-lived ctx) own that themselves.
export async function dispatch(invocation, ctx) {
  await invocation.definition.handler(ctx);
  return EXIT.OK;
}

// One-shot wrapper kept for the plain CLI entry point and for every existing
// caller/test: parseInvocation -> buildContext -> dispatch, in one process
// per call. External behaviour (exit codes, the `{"error":{...}}` envelope,
// `--help` handling) is unchanged from before this split — see
// task-16-report.md for how that was verified.
export async function main(argv, deps = {}) {
  const streams = deps.streams ?? { stdout: process.stdout, stderr: process.stderr };
  const jsonFlag = detectJsonFlag(argv);

  try {
    const invocation = parseInvocation(argv);

    if (invocation.help) {
      streams.stdout.write(`${renderHelp(invocation.group, invocation.action)}\n`);
      return EXIT.OK;
    }

    // `ui` builds and reuses its own session-lifetime ctx per line (that's
    // the entire point of it existing) rather than the one buildContext()
    // would build for a single call, so it bypasses buildContext/dispatch
    // here rather than going through them like every other group.
    if (invocation.group === 'ui') {
      const { startRepl } = await import('./repl.mjs');
      return await startRepl(deps);
    }

    const ctx = buildContext({ values: invocation.values, positionals: invocation.positionals, deps: { ...deps, streams } });
    return await dispatch(invocation, ctx);
  } catch (err) {
    const mode = jsonFlag ? 'json' : 'plain';
    streams.stderr.write(`${renderError(err, { mode })}\n`);
    // Only codes the CLI itself owns may be returned. A structural
    // `typeof === 'number'` test is not sufficient: a DOMException's legacy
    // numeric `.code` (e.g. AbortError === 20) would otherwise pass through
    // and contradict the `code` printed in the JSON envelope for the same
    // error.
    const code = err?.code;
    return Number.isInteger(code) && code >= EXIT.OK && code <= EXIT.RATE_LIMIT
      ? code
      : EXIT.GENERAL;
  }
}
