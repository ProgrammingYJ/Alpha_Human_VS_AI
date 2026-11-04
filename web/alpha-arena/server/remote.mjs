import { ArenaError } from "./logic.mjs";

export const ENGINE_FRESH_MS = 15_000;
export const TILE_INTERVAL_MS = 250;
export const ENGINE_STAGES = new Set(["ready", "waiting_gpu", "reserved", "loading_images", "images_ready", "inferencing", "selecting", "submitted", "error"]);

export function validateRoomMode(value) {
  if (value.mode === undefined) {
    if (value.lane !== undefined) throw new ArenaError("invalid_mode", "레인에는 remote 모드가 필요합니다.");
    return null;
  }
  if (value.mode !== "remote" || !["A", "B"].includes(value.lane)) throw new ArenaError("invalid_mode", "remote 모드와 A/B 레인을 확인해 주세요.");
  return value.lane;
}

export function validateLane(value, remote) {
  if (value === undefined) return;
  if (!["A", "B"].includes(value)) throw new ArenaError("invalid_lane", "A/B 레인을 확인해 주세요.");
  if (!remote || remote.lane !== value) throw new ArenaError("lane_mismatch", "연결 코드의 레인이 다릅니다. A/B 코드를 확인해 주세요.", 409);
}

export function engineConnected(remote, now) {
  return !!remote.engine_token_hash && Number.isFinite(remote.engine_seen_at)
    && remote.engine_seen_at <= now && remote.engine_seen_at >= now - ENGINE_FRESH_MS;
}

export function remoteReady(room, remote, now) {
  return !!room.bot_token_hash && remote.engine_ready === 1 && engineConnected(remote, now)
    && remote.engine_stage !== "error";
}

export function remotePublic(room, remote, role, now) {
  const result = { mode: "remote", lane: remote.lane, viewerConnected: !!room.bot_token_hash,
    engineConnected: engineConnected(remote, now), engineStage: remote.engine_stage,
    engineHeartbeatReceived: Number.isFinite(remote.engine_seen_at),
    gpuReservationSupported: remote.engine_protocol >= 2,
    imageBarrierSupported: remote.engine_protocol === 3,
    sequence: remote.sequence, lastSelectionAt: remote.last_selection_at };
  if (role !== "human") result.selectedIndices = JSON.parse(remote.selected_json);
  return result;
}

export function validateEngineAction(value) {
  if (value.action === "heartbeat") {
    if (!ENGINE_STAGES.has(value.stage)) throw new ArenaError("invalid_stage", "엔진 상태를 확인해 주세요.");
    if (!(value.roundId === null || typeof value.roundId === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.roundId))
      || !Number.isSafeInteger(value.roundNumber) || value.roundNumber < 0) throw new ArenaError("invalid_round", "엔진이 확인한 문제 번호가 필요합니다.");
    if (value.protocolVersion !== undefined && ![1, 2, 3].includes(value.protocolVersion)) throw new ArenaError("protocol_upgrade_required", "PC 원격 실행기를 최신 버전으로 다시 시작해 주세요.", 409);
    if ((value.protocolVersion >= 2 || value.requestId !== undefined) && !(value.requestId === null || typeof value.requestId === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.requestId))) throw new ArenaError("invalid_start_request", "엔진이 확인한 시작 요청 번호가 필요합니다.");
    return;
  }
  if (value.action === "images_ready") {
    if (typeof value.roundId !== "string" || !/^[0-9a-f-]{36}$/i.test(value.roundId)
      || typeof value.requestId !== "string" || !/^[0-9a-f-]{36}$/i.test(value.requestId)
      || typeof value.imageLoadId !== "string" || !/^[0-9a-f-]{36}$/i.test(value.imageLoadId)
      || !Number.isSafeInteger(value.roundNumber) || value.roundNumber < 1) throw new ArenaError("image_load_changed", "현재 사진 준비 상태를 확인해 주세요.", 409);
    return;
  }
  if (value.action === "begin") {
    if (typeof value.requestId !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.requestId)
      || !Number.isSafeInteger(value.roundNumber) || value.roundNumber < 0) throw new ArenaError("invalid_start_request", "현재 GPU 시작 요청과 문제 번호가 필요합니다.");
    return;
  }
  if (value.action === "select") {
    if (!Number.isInteger(value.sequence) || value.sequence < 1 || value.sequence > 9
      || !Number.isInteger(value.tileIndex) || value.tileIndex < 0 || value.tileIndex > 8) {
      throw new ArenaError("invalid_selection", "타일 번호와 선택 순서를 확인해 주세요.");
    }
    return;
  }
  if (value.action === "plan") {
    if (!Array.isArray(value.selectedIndices) || value.selectedIndices.length > 9
      || value.selectedIndices.some(index => !Number.isInteger(index) || index < 0 || index > 8)
      || new Set(value.selectedIndices).size !== value.selectedIndices.length) {
      throw new ArenaError("invalid_selection", "모델이 고른 서로 다른 타일 번호만 보낼 수 있습니다.");
    }
    return;
  }
  if (value.action !== "submit") throw new ArenaError("invalid_action", "엔진 동작을 확인해 주세요.");
}

/** Reads only server-owned state. A duplicate ACK never changes its timestamp. */
export function selectionDecision(remote, sequence, tileIndex, now) {
  const selected = JSON.parse(remote.selected_json);
  if (sequence <= remote.sequence) {
    if (selected[sequence - 1] === tileIndex) return "duplicate";
    throw new ArenaError("sequence_conflict", "선택 순서가 이미 다른 타일로 처리됐습니다.", 409);
  }
  if (sequence !== remote.sequence + 1) throw new ArenaError("sequence_conflict", "다음 선택 순서를 확인해 주세요.", 409);
  if (selected.includes(tileIndex)) throw new ArenaError("duplicate_selection", "이미 선택한 타일입니다.", 409);
  if (remote.last_selection_at !== null && now - remote.last_selection_at < TILE_INTERVAL_MS) {
    throw new ArenaError("selection_too_fast", "타일 선택 사이에는 최소 0.25초가 필요합니다.", 429);
  }
  return "append";
}

// The same live-room predicates are part of the write, not merely a prior read.
const LIVE_ENGINE = `EXISTS (SELECT 1 FROM arena_rooms AS room JOIN arena_rounds AS round ON round.id = room.round_id AND round.room_id = room.id WHERE room.id = arena_remote_rooms.room_id AND room.round_id = ? AND room.phase = 'active' AND room.expires_at > ? AND round.start_at <= ? AND round.deadline_at > ? AND round.bot_plan_indices_json IS NULL AND COALESCE(round.human_correct,0) <> 1 AND COALESCE(round.bot_correct,0) <> 1)`;
export const REMOTE_HEARTBEAT = `UPDATE arena_remote_rooms SET engine_seen_at = ?, engine_stage = ?, engine_protocol = ?, engine_ready = CASE WHEN ? = 'ready' THEN 1 WHEN ? = 'error' THEN 0 ELSE engine_ready END WHERE room_id = ? AND engine_token_hash = ? AND (engine_seen_at IS NULL OR engine_seen_at <= ?) AND EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND expires_at > ? AND round_id IS ? AND round_number = ? AND start_request_id IS ? AND (? <> 'ready' OR phase = 'lobby') AND (? NOT IN ('waiting_gpu','reserved') OR phase = 'queued') AND (phase <> 'queued' OR (? = 3 AND ? IN ('waiting_gpu','reserved','error'))) AND (phase <> 'result' OR ? IN ('submitted','inferencing','error')) AND NOT EXISTS (SELECT 1 FROM arena_rounds AS r WHERE r.id=arena_rooms.round_id AND r.image_load_id IS NOT NULL AND (arena_rooms.phase='loading' OR (arena_rooms.phase='active' AND r.start_at>?)) AND (? <> 3 OR ? NOT IN ('loading_images','images_ready','error'))))`;
export const REMOTE_SELECT = `UPDATE arena_remote_rooms SET selected_json = json_insert(selected_json, '$[#]', ?), sequence = ?, last_selection_at = ?, engine_stage = 'selecting' WHERE room_id = ? AND engine_token_hash = ? AND engine_seen_at >= ? AND engine_seen_at <= ? AND engine_ready = 1 AND engine_stage <> 'error' AND sequence = ? AND (last_selection_at IS NULL OR last_selection_at <= ?) AND NOT EXISTS (SELECT 1 FROM json_each(selected_json) WHERE value = ?) AND ${LIVE_ENGINE}`;

// Reset remote state before the room write in the SAME transaction. The result
// + round + revision guard makes a duplicate batch a no-op, even after re-ready.
export const REMOTE_NEXT_RESET = `UPDATE arena_remote_rooms SET selected_json = '[]', sequence = 0, last_selection_at = NULL, engine_ready = 0, engine_stage = 'connected' WHERE room_id = ? AND EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND phase = 'result' AND round_id = ? AND revision = ? AND expires_at > ?)`;
export const REMOTE_NEXT_ROOM = `UPDATE arena_rooms SET phase = 'lobby', round_id = NULL, bot_ready = 0, human_ready = 1, start_request_id = NULL, start_requested_at = NULL, start_expires_at = NULL, last_start_cancel_reason = NULL, revision = revision + 1 WHERE id = ? AND phase = 'result' AND round_id = ? AND revision = ? AND expires_at > ? AND EXISTS (SELECT 1 FROM arena_remote_rooms WHERE room_id = arena_rooms.id)`;
export const REMOTE_SUBMITTED_STAGE = `UPDATE arena_remote_rooms SET engine_stage = 'submitted' WHERE room_id = ? AND engine_token_hash = ? AND sequence = ? AND selected_json = ? AND EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND round_id = ? AND phase IN ('active','result'))`;

// A selection append racing a submission invalidates this exact snapshot.
export const REMOTE_SUBMIT = `UPDATE arena_rounds SET bot_submitted_at = ?, bot_correct = ?, bot_elapsed_ms = ? WHERE id = ? AND bot_plan_indices_json IS NULL AND bot_submitted_at IS NULL AND COALESCE(human_correct,0) <> 1 AND COALESCE(bot_correct,0) <> 1 AND start_at <= ? AND deadline_at > ? AND EXISTS (SELECT 1 FROM arena_rooms AS room JOIN arena_remote_rooms AS remote ON remote.room_id = room.id WHERE room.id = ? AND room.round_id = arena_rounds.id AND room.phase = 'active' AND room.expires_at > ? AND remote.engine_token_hash = ? AND remote.engine_seen_at >= ? AND remote.engine_seen_at <= ? AND remote.engine_ready = 1 AND remote.engine_stage <> 'error' AND remote.sequence = ? AND remote.selected_json = ?)`;
