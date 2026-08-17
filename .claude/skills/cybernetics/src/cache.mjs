import { readFileSync, existsSync, mkdirSync, writeFileSync, chmodSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { CONFIG_DIR } from './config.mjs';

export const CACHE_PATH = join(CONFIG_DIR, 'cache.json');
export const CACHE_VERSION = 1;
export const METADATA_TTL_MS = 15 * 60 * 1000;

function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function emptyCache(workspace) {
  return {
    version: CACHE_VERSION,
    workspace,
    me: null,
    capabilities: {},
    projects: {},
    byProject: {},
  };
}

export function loadCache({ path = CACHE_PATH, workspace } = {}) {
  if (!existsSync(path)) return emptyCache(workspace);
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf8'));
    if (parsed?.version !== CACHE_VERSION) return emptyCache(workspace);
    if (parsed?.workspace !== workspace) return emptyCache(workspace);
    return {
      ...emptyCache(workspace),
      ...parsed,
      projects: isPlainObject(parsed.projects) ? parsed.projects : {},
      byProject: isPlainObject(parsed.byProject) ? parsed.byProject : {},
      capabilities: isPlainObject(parsed.capabilities) ? parsed.capabilities : {},
    };
  } catch {
    return emptyCache(workspace);
  }
}

export function saveCache(cache, { path = CACHE_PATH } = {}) {
  const dir = dirname(path);
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  chmodSync(dir, 0o700);
  writeFileSync(path, `${JSON.stringify(cache, null, 2)}\n`, { mode: 0o600 });
  chmodSync(path, 0o600);
}

export function isFresh(fetchedAt, { now = Date.now, ttl = METADATA_TTL_MS } = {}) {
  if (!fetchedAt) return false;
  const at = Date.parse(fetchedAt);
  if (Number.isNaN(at)) return false;
  return now() - at < ttl;
}

export function projectBucket(cache, projectId) {
  cache.byProject[projectId] ??= {
    states: {},
    labels: {},
    members: {},
    items: {},
    fetchedAt: null,
    labelsFetchedAt: null,
  };
  return cache.byProject[projectId];
}
