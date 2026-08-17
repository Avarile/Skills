export function captureStreams() {
  const out = [];
  const err = [];
  return {
    stdout: { write: (s) => out.push(s), isTTY: false },
    stderr: { write: (s) => err.push(s) },
    outText: () => out.join(''),
    errText: () => err.join(''),
  };
}
