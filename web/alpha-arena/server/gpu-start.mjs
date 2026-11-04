import { ArenaError } from "./logic.mjs";
import { engineConnected } from "./remote.mjs";

export const QUEUE_TTL_MS = 120_000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export function validRequestId(value) { return typeof value === "string" && UUID.test(value); }
export function validateStartRevision(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw new ArenaError("invalid_revision", "현재 대기실 상태 번호가 필요합니다.");
}
export function validateStartRequest(value) {
  if (!validRequestId(value)) throw new ArenaError("invalid_start_request", "현재 시작 요청 번호가 필요합니다.");
}
export function queueCancellationReason(room, remote, now) {
  if (room.phase !== "queued") return null;
  if (!room.start_request_id || !Number.isFinite(room.start_expires_at) || room.start_expires_at <= now) return "queue_expired";
  if (remote?.engine_stage === "error") return "engine_error";
  if (!remote || !engineConnected(remote, now)) return "engine_disconnected";
  return null;
}
export function startRequestPublic(room) {
  return room.start_request_id ? { id: room.start_request_id, requestedAt: room.start_requested_at, expiresAt: room.start_expires_at } : null;
}

// A queue request contains NO challenge. Its revision also rejects delayed
// human start retries after a cancellation or a later participant.
export const GPU_QUEUE = `UPDATE arena_rooms SET phase = 'queued', start_request_id = ?, start_requested_at = ?, start_expires_at = ?, last_start_cancel_reason = NULL, revision = revision + 1 WHERE id = ? AND revision = ? AND phase = 'lobby' AND round_id IS NULL AND expires_at > ? AND bot_token_hash IS NOT NULL AND EXISTS (SELECT 1 FROM arena_remote_rooms WHERE room_id = arena_rooms.id AND engine_protocol = 3 AND engine_token_hash IS NOT NULL AND engine_ready = 1 AND engine_stage = 'ready' AND engine_seen_at >= ? AND engine_seen_at <= ?)`;

// D1 executes these two statements in one transaction. Automatic cancellation
// pins the observed heartbeat/stage; a fresh heartbeat racing expiry cannot be
// cleared using an earlier stale read. Human cancellation remains unconditional.
export const GPU_CANCEL_REMOTE = `UPDATE arena_remote_rooms SET selected_json = '[]', sequence = 0, last_selection_at = NULL, engine_ready = 0, engine_stage = ? WHERE room_id = ? AND (? = 'human_cancelled' OR (engine_seen_at IS ? AND engine_stage = ?)) AND EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND phase = 'queued' AND round_id IS NULL AND start_request_id = ? AND revision = ? AND expires_at > ?)`;
export const GPU_CANCEL_ROOM = `UPDATE arena_rooms SET phase = 'lobby', start_request_id = NULL, start_requested_at = NULL, start_expires_at = NULL, last_start_cancel_reason = ?, revision = revision + 1 WHERE id = ? AND phase = 'queued' AND round_id IS NULL AND start_request_id = ? AND revision = ? AND expires_at > ? AND EXISTS (SELECT 1 FROM arena_remote_rooms WHERE room_id = arena_rooms.id AND engine_ready = 0 AND engine_stage = ?)`;

// Retained solely for active v11 compatibility regression fixtures. New
// production reservations use the image-barrier INSERT/UPDATE transaction.
const BEGIN_READY = `EXISTS (SELECT 1 FROM arena_remote_rooms AS remote WHERE remote.room_id = arena_rooms.id AND remote.engine_token_hash = ? AND remote.engine_protocol = 2 AND remote.engine_ready = 1 AND remote.engine_stage IN ('ready','waiting_gpu','reserved') AND remote.engine_seen_at >= ? AND remote.engine_seen_at <= ?)`;
export const GPU_BEGIN_INSERT = `INSERT INTO arena_rounds (id, room_id, number, theme_id, tiles_json, answer_json, start_at, deadline_at) SELECT ?, ?, ?, ?, ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND revision = ? AND round_id IS NULL AND bot_token_hash IS NOT NULL AND phase = 'queued' AND start_request_id = ? AND round_number = ? AND start_expires_at > ? AND expires_at > ? AND ${BEGIN_READY})`;
export const GPU_BEGIN_ROOM = `UPDATE arena_rooms SET round_id = ?, round_number = round_number + 1, phase = 'active', human_ready = 1, revision = revision + 1 WHERE id = ? AND revision = ? AND round_id IS NULL AND bot_token_hash IS NOT NULL AND phase = 'queued' AND start_request_id = ? AND round_number = ? AND start_expires_at > ? AND expires_at > ? AND ${BEGIN_READY} AND EXISTS (SELECT 1 FROM arena_rounds WHERE id = ?)`;
export const GPU_BEGIN_REMOTE = `UPDATE arena_remote_rooms SET engine_stage = 'inferencing' WHERE room_id = ? AND engine_token_hash = ? AND EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND phase = 'active' AND round_id = ? AND start_request_id = ?)`;
