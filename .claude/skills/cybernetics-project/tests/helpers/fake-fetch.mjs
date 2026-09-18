export function makeFakeFetch(responses) {
  const queue = [...responses];
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    const next = queue.shift();
    if (!next) throw new Error(`fake-fetch: no queued response for ${url}`);
    return {
      status: next.status,
      headers: { get: (k) => (next.headers ?? {})[k.toLowerCase()] ?? null },
      text: async () => (next.body === undefined ? '' : JSON.stringify(next.body)),
    };
  };
  return { fetchImpl, calls };
}
