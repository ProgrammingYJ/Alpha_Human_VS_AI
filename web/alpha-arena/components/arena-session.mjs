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
  return failure?.status === 410 && ["room_reset", "room_expired"].includes(failure.code)
    && currentSessionRequest(request, current);
}
