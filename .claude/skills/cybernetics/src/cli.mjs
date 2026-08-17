import { parseArgs } from 'node:util';
import { loadConfig, CONFIG_PATH } from './config.mjs';
import { loadCache, saveCache, CACHE_PATH } from './cache.mjs';
import { Client } from './client.mjs';
import { Resolver } from './resolve.mjs';
import { pickMode, renderError } from './format.mjs';
import { CybError, EXIT } from './errors.mjs';
import { doctor } from './commands/doctor.mjs';

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
    lines.push('', `Options for ${group} ${action}:`);
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
  const save = () => {
    try {
      saveCache(cache, { path: cachePath });
    } catch {
      // A read-only cache location must never fail a command.
    }
  };

  const resolver = new Resolver({ client, cache, persist: save, noCache: values['no-cache'] });

  const mode = pickMode({ json: values.json, isTTY: Boolean(streams.stdout.isTTY) });

  return { config, client, cache, resolver, save, mode, streams, values, positionals };
}

export async function main(argv, deps = {}) {
  const streams = deps.streams ?? { stdout: process.stdout, stderr: process.stderr };
  const jsonFlag = argv.includes('--json');

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
      streams.stdout.write(`${renderHelp(group, usesDefault ? undefined : actionName)}\n`);
      return EXIT.OK;
    }

    const ctx = buildContext({ values, positionals, deps: { ...deps, streams } });
    await definition.handler(ctx);
    return EXIT.OK;
  } catch (err) {
    const mode = jsonFlag ? 'json' : 'plain';
    streams.stderr.write(`${renderError(err, { mode })}\n`);
    return typeof err?.code === 'number' ? err.code : EXIT.GENERAL;
  }
}
