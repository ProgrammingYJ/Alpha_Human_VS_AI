/**
 * @typedef {{ roomId: string, revision?: number, serverNow: number,
 *   roundNumber: number, roundId: string | null,
 *   phase: "lobby" | "queued" | "loading" | "countdown" | "playing" | "result",
 *   startRequest?: { id: string } | null,
 *   remote?: { sequence: number } }} RoomCursor
 */

/** Keep delayed polls and action replies from restoring a finished participant. */
/** @param {RoomCursor | null} current @param {RoomCursor} next */
export function acceptsRoomState(current, next) {
  if (!next || !Number.isFinite(next.serverNow) || !Number.isInteger(next.roundNumber) || next.roundNumber < 0) return false;
  if (!["lobby", "queued", "loading", "countdown", "playing", "result"].includes(next.phase)) return false;
  if (next.phase === "queued" && (!next.remote || next.roundId !== null || typeof next.startRequest?.id !== "string" || !next.startRequest.id)) return false;
  if (next.revision !== undefined && (!Number.isInteger(next.revision) || next.revision < 0)) return false;
  if (!current) return true;
  if (next.roomId !== current.roomId || next.roundNumber < current.roundNumber) return false;

  const hasRevision = current.revision !== undefined && next.revision !== undefined;
  if (hasRevision && next.revision < current.revision) return false;
  const newerRevision = hasRevision && next.revision > current.revision;
  if (!newerRevision && next.serverNow < current.serverNow) return false;

  // Starting the next game increases roundNumber; next-participant lobby keeps it.
  if (next.roundNumber > current.roundNumber) return next.roundId !== null && next.phase !== "lobby" && next.phase !== "queued";
  if (current.roundId === null && next.roundId === null) {
    if (next.phase !== "lobby" && next.phase !== "queued") return false;
    if (next.phase !== current.phase) return !!next.remote && newerRevision;
    if (next.phase === "queued" && next.startRequest?.id !== current.startRequest?.id) return newerRevision;
    return true;
  }
  if (current.roundId === null) return false;
  if (next.roundId === null) return !!next.remote && (next.phase === "lobby" || next.phase === "queued") && (newerRevision || current.phase === "result" && next.phase === "lobby");
  if (next.roundId !== current.roundId) return false;

  const phaseOrder = { lobby: 0, queued: 1, loading: 2, countdown: 3, playing: 4, result: 5 };
  if (phaseOrder[next.phase] < phaseOrder[current.phase]
    && !(newerRevision && current.phase === "countdown" && next.phase === "loading" && next.imageLoad?.id !== current.imageLoad?.id)) return false;
  if (!newerRevision && current.remote && next.remote && next.remote.sequence < current.remote.sequence) return false;
  return true;
}

/** An old request's failure must not replace a newer reservation or participant. */
/** @param {RoomCursor | null} source @param {RoomCursor | null} current */
export function sameActionContext(source, current) {
  return !!source && !!current && source.roomId === current.roomId
    && source.roundId === current.roundId && source.roundNumber === current.roundNumber
    && source.revision === current.revision
    && (source.phase === "queued" ? source.startRequest?.id : null) === (current.phase === "queued" ? current.startRequest?.id : null);
}

/**
 * A queued response never exposes a playable question, even if fields arrive early.
 * @template TTopic, TTile
 * @param {{phase: string, topic?: TTopic | null, tiles?: TTile[], startAt?: number | null, deadlineAt?: number | null} | null} state
 */
export function publicRoundView(state, serverNow = 0) {
  const queued = state?.phase === "queued";
  const loading = state?.phase === "loading";
  const reveal = ["countdown", "playing", "result"].includes(state?.phase) && !!state?.startAt && serverNow >= state.startAt;
  return { queued, loading, topic: queued || loading || !reveal ? null : state?.topic ?? state?.preloadTopic ?? null,
    tiles: queued ? [] : state?.preloadTiles?.length === 9 ? state.preloadTiles : state?.tiles ?? [],
    startAt: queued || loading ? null : state?.startAt ?? null, deadlineAt: queued || loading ? null : state?.deadlineAt ?? null };
}

/** Keep the faster read-only AI selections visible without increasing idle polls.
 * @param {string} role @param {{phase: string, remote?: unknown} | null} state
 */
export function roomPollIntervalMs(role, state) {
  return role === "bot" && !!state?.remote && state.phase === "playing" && !validSelectionPlan(state) ? 125 : 500;
}

/** Only render server-issued schedules for this round; never infer a winner. */
export function validSelectionPlan(state) {
  const plan = state?.remote?.selectionPlan;
  if (!plan || plan.roundId !== state?.roundId || !Number.isSafeInteger(plan.startAt) || plan.intervalMs !== 250
      || !Array.isArray(plan.selectedIndices) || plan.selectedIndices.length > 9
      || plan.selectedIndices.some(index => !Number.isInteger(index) || index < 0 || index > 8)
      || new Set(plan.selectedIndices).size !== plan.selectedIndices.length
      || plan.submitAt !== plan.startAt + Math.max(0, plan.selectedIndices.length - 1) * plan.intervalMs) return null;
  return plan;
}

/** Smooth read-only playback uses the existing server-clock tick, not an HTTP
 * round trip per tile. A late response catches up, and a winner clips playback.
 */
export function remoteDisplayIndices(state, serverNow) {
  const plan = validSelectionPlan(state);
  if (!plan) return state?.remote?.selectedIndices ?? [];
  const cutoff = Math.min(serverNow, state.result?.finishedAt ?? Infinity, state.deadlineAt ?? Infinity);
  const count = cutoff < plan.startAt ? 0 : Math.min(plan.selectedIndices.length, Math.floor((cutoff - plan.startAt) / plan.intervalMs) + 1);
  return plan.selectedIndices.slice(0, count);
}
