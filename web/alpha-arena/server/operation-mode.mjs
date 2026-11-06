import { ArenaError } from "./logic.mjs";
import { SESSION_PHOTO_FOR_CURRENT_ROUND } from "./session-reset.mjs";

/** Internal A remains stable so existing A rooms need no schema/token change. */
export function operationMode(raw) {
  if (raw === undefined || raw === "single") return "single";
  if (raw === "dual") return "dual";
  throw new ArenaError("operation_mode_unavailable", "운영 모드 설정을 확인해 주세요.", 503);
}

export function operationRequest(value, raw) {
  const mode = operationMode(raw);
  if (mode === "single" && value.lane === "B") {
    throw new ArenaError("lane_disabled", "현재 한 대결만 운영합니다. 기본 주소에서 새 대결방으로 연결해 주세요.", 409);
  }
  return mode === "single" && value.mode === "remote" && value.lane === undefined
    ? { ...value, lane: "A" } : value;
}

export function requireOperationLane(lane, raw) {
  if (operationMode(raw) === "single" && lane === "B") {
    throw new ArenaError("lane_disabled", "이전 B 구역 연결은 운영을 종료했습니다. 기본 주소에서 새 대결방으로 연결해 주세요.", 410);
  }
}

// Policy reads use the same D1 request as the room/photo read, without another
// network round trip. Internal metadata is never exposed in public snapshots.
export const OPERATION_ROOM_BY_ID = "SELECT room.*, remote.lane AS operation_lane FROM arena_rooms AS room LEFT JOIN arena_remote_rooms AS remote ON remote.room_id=room.id WHERE room.id = ?";
export const OPERATION_ROOM_BY_CODE = "SELECT room.*, remote.lane AS operation_lane FROM arena_rooms AS room LEFT JOIN arena_remote_rooms AS remote ON remote.room_id=room.id WHERE room.code = ?";
export const OPERATION_PHOTO_FOR_CURRENT_ROUND = SESSION_PHOTO_FOR_CURRENT_ROUND.replace(
  "SELECT p.*", "SELECT p.*, (SELECT lane FROM arena_remote_rooms WHERE room_id=room.id) AS operation_lane");
