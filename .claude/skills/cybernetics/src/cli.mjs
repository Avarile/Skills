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
    },
  },
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
    lines.push(`  ${label.padEnd(12)} ${def.summary ?? ''}`);
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

  return { config, client, cache, resolver, save, mode, streams, values, positionals };
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

export async function main(argv, deps = {}) {
  const streams = deps.streams ?? { stdout: process.stdout, stderr: process.stderr };
  const jsonFlag = detectJsonFlag(argv);

  try {
    const [group, ...rest] = argv;

    if (!group || group === '--help' || group === 'help') {
      streams.stdout.write(`${renderHelp()}\n`);
      return EXIT.OK;
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
    const usesDefault = Boolean(actions.__default) && (!maybeAction || maybeAction.startsWith('-'));

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
      streams.stdout.write(`${renderHelp(group, actionName)}\n`);
      return EXIT.OK;
    }

    const ctx = buildContext({ values, positionals, deps: { ...deps, streams } });
    await definition.handler(ctx);
    return EXIT.OK;
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
