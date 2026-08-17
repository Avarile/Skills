import { readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { CybError, EXIT } from './errors.mjs';

export const CONFIG_DIR = join(homedir(), '.cybernetics');
export const CONFIG_PATH = join(CONFIG_DIR, 'config.json');

export const DEFAULTS = Object.freeze({
  baseUrl: 'https://projects.avarile.com',
  workspace: 'cybernetics',
  limit: 30,
});

export function parseDotEnv(text) {
  const out = {};
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    const quoted =
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"));
    if (quoted && value.length >= 2) value = value.slice(1, -1);
    out[key] = value;
  }
  return out;
}

function readJson(path) {
  if (!existsSync(path)) return {};
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (err) {
    throw new CybError(
      EXIT.GENERAL,
      `config file is not valid JSON: ${path}`,
      'fix the file by hand, or delete it and run: cyb init',
    );
  }
}

function stripSlash(url) {
  return typeof url === 'string' ? url.replace(/\/+$/, '') : url;
}

export function loadConfig({ env = process.env, cwd = process.cwd(), configPath = CONFIG_PATH } = {}) {
  const file = readJson(configPath);

  const dotEnvPath = join(cwd, '.env');
  const dotEnv = existsSync(dotEnvPath) ? parseDotEnv(readFileSync(dotEnvPath, 'utf8')) : {};

  const token = env.CYB_TOKEN ?? file.token ?? dotEnv.CYB_TOKEN ?? null;

  return {
    baseUrl: stripSlash(env.CYB_BASE_URL ?? file.baseUrl ?? dotEnv.CYB_BASE_URL ?? DEFAULTS.baseUrl),
    workspace: env.CYB_WORKSPACE ?? file.workspace ?? dotEnv.CYB_WORKSPACE ?? DEFAULTS.workspace,
    token,
    defaultProject: env.CYB_PROJECT ?? file.defaultProject ?? null,
    defaults: { limit: Number(file.defaults?.limit ?? DEFAULTS.limit) },
  };
}

export function saveConfig(config, { configPath = CONFIG_PATH } = {}) {
  const dir = dirname(configPath);
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
}

export function fingerprint(token) {
  if (!token) return '(none)';
  if (token.length <= 14) return '…';
  return `${token.slice(0, 10)}…${token.slice(-4)}`;
}
