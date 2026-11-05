/** Server-owned creation-time fence; never deletes data or changes credentials. */
import { ArenaError } from "./logic.mjs";
import { PHOTO_FOR_CURRENT_ROUND } from "./statements.mjs";

function unavailable() {
  return new ArenaError("session_reset_unavailable", "운영 세션 초기화 설정을 확인해 주세요.", 503);
}

/** An absent binding disables the fence. A present malformed/future binding fails closed. */
export function sessionResetCutoff(raw, now = Date.now()) {
  if (raw === undefined) return 0;
  if (typeof raw !== "string" || !/^[1-9][0-9]{0,15}$/.test(raw)
      || !Number.isSafeInteger(now) || now < 0) throw unavailable();
  const cutoff = Number(raw);
  if (!Number.isSafeInteger(cutoff) || cutoff > now) throw unavailable();
  return cutoff;
}

/** The same fence applies before authorization to humans, viewers and engines. */
export function requireCurrentSession(room, raw, now = Date.now()) {
  const cutoff = sessionResetCutoff(raw, now);
  if (!cutoff) return;
  if (!Number.isSafeInteger(room?.created_at) || room.created_at < 0) throw unavailable();
  if (room.created_at <= cutoff) {
    throw new ArenaError("room_reset", "운영자가 연결을 초기화했습니다. 새 대결방으로 다시 연결해 주세요.", 410);
  }
}

// Public opaque-photo reads bypass getRoom(). Add only internal creation-time
// metadata to its existing query so revoked rounds cannot bypass the fence.
// This field is used by the server guard and is never returned as JSON.
export const SESSION_PHOTO_FOR_CURRENT_ROUND = PHOTO_FOR_CURRENT_ROUND.replace(
  "SELECT p.*,", "SELECT p.*, room.created_at AS session_created_at,");
