/** Anchor the shared server clock to monotonic browser time. Slow polls must
 * not shift a prepared countdown; periodically refresh the best RTT sample. */
export function clockSample(previous, serverNow, before, after, frozen = false) {
  if (previous && frozen) return previous;
  if (![serverNow, before, after].every(Number.isFinite) || after < before) return previous;
  const rtt = after - before;
  if (previous && after - previous.sampledAt < 30_000 && rtt > previous.rtt) return previous;
  return { offset: serverNow - (before + after) / 2, rtt, sampledAt: after };
}
