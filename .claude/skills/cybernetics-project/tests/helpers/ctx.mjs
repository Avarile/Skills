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
    // Per-region freshness keys must match what the shipped `projectBucket`
    // creates and what `resolve.mjs` gates on. A single bucket-wide
    // `fetchedAt` was renamed during Phase 1 review precisely because it
    // silently meant "states are fresh"; setting the old name here would make
    // every warm-cache test read as stale and fetch, with no queued response.
    cache.byProject[UUID_PROJECT] = {
      states: Object.fromEntries(STATE_LIST.map((s) => [s.name.toLowerCase(), s.id])),
      stateList: STATE_LIST,
      labels: {},
      members: {},
      items: {},
      statesFetchedAt: stamp,
      labelsFetchedAt: stamp,
      itemsFetchedAt: stamp,
      maxSequence: null,
      maxSequenceFetchedAt: null,
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
