/** Session keys contain only role/mode/lane, never a room code or token. */
export function sessionKey(role, mode, lane) {
  return mode === "remote" ? `alpha-arena-${role}-remote-${lane}` : `alpha-arena-${role}`;
}

export const remoteSessionKeys = Object.freeze(["human", "bot"].flatMap(role =>
  ["A", "B"].map(lane => sessionKey(role, "remote", lane))));

/** Explicit reset affects this origin's four remote roles, without reading them. */
export function clearRemoteSessions(storage) {
  for (const key of remoteSessionKeys) storage.removeItem(key);
}

/** A delayed failure/success from an old connection cannot change its successor. */
export function currentSessionRequest(request, current) {
  return request.generation === current.generation && request.roomId === current.roomId
    && request.storageKey === current.storageKey;
}

export function resetSessionFailure(failure, request, current) {
  return failure?.status === 410 && ["room_reset", "room_expired", "lane_disabled"].includes(failure.code)
    && currentSessionRequest(request, current);
}

/** Resolve only after reading the server's operation mode, before restoring a token. */
export function operationLane(mode, requestedLane, savedLane, remote = true) {
  if (!["single", "dual"].includes(mode)) throw new Error("운영 모드를 확인하지 못했습니다. 화면을 새로고침해 주세요.");
  const candidate = ["A", "B"].includes(requestedLane) ? requestedLane : savedLane === "B" ? "B" : "A";
  return { lane: remote && mode === "single" ? "A" : candidate,
    disabledPreviousLane: remote && mode === "single" && candidate === "B" };
}
