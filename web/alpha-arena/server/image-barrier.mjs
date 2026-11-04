import { ArenaError, THEMES } from "./logic.mjs";
import { ENGINE_FRESH_MS, engineConnected } from "./remote.mjs";

export const IMAGE_LOADING_MS = 60_000;
export const COMMON_COUNTDOWN_MS = 2_000;
// Existing round timestamps are NOT NULL. This value is never public.
export const UNSTARTED_AT = 8_000_000_000_000_000;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function validateImageEpoch(value) {
  if (typeof value !== "string" || !UUID.test(value)) throw new ArenaError("image_load_changed", "현재 사진 준비 번호를 다시 확인해 주세요.", 409);
}
export function prestartImages(room, round, now) {
  return !!round?.image_load_id && (room.phase === "loading" || room.phase === "active" && now < round.start_at);
}
export function imageCancellationReason(room, round, remote, now) {
  if (!prestartImages(room, round, now)) return null;
  if (remote?.engine_stage === "error") return "engine_error";
  if (!remote || !engineConnected(remote, now)) return "engine_disconnected";
  if (room.phase === "loading" && (!Number.isFinite(round.loading_expires_at) || now >= round.loading_expires_at)) return "image_load_timeout";
  return null;
}
export function imageBarrierPublic(state, room, round, now) {
  if (!round?.image_load_id) return state;
  const preparing = room.phase === "loading";
  const beforeStart = preparing || state.phase === "countdown";
  state.imageLoad = { id: round.image_load_id, expiresAt: round.loading_expires_at,
    humanReady: round.human_images_ready === 1, botReady: round.bot_images_ready === 1, engineReady: round.engine_images_ready === 1 };
  if (beforeStart) {
    state.preloadTiles = JSON.parse(round.tiles_json).map(tile => ({ id: tile.id, url: `/api/photos/${tile.id}` }));
    if (!preparing) {
      const theme = THEMES[round.theme_id];
      state.preloadTopic = { id: theme.id, prompt: theme.prompt, condition: theme.condition };
    }
    state.topic = null; state.tiles = [];
  }
  if (preparing) {
    state.phase = "loading"; state.startAt = null; state.deadlineAt = null;
  }
  return state;
}

const NEW_ENGINE = `EXISTS (SELECT 1 FROM arena_remote_rooms AS remote WHERE remote.room_id = arena_rooms.id AND remote.engine_token_hash = ? AND remote.engine_protocol = 3 AND remote.engine_ready = 1 AND remote.engine_stage IN ('ready','waiting_gpu','reserved') AND remote.engine_seen_at >= ? AND remote.engine_seen_at <= ?)`;
export const IMAGE_BEGIN_INSERT = `INSERT INTO arena_rounds (id,room_id,number,theme_id,tiles_json,answer_json,start_at,deadline_at,image_load_id,loading_expires_at) SELECT ?,?,?,?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM arena_rooms WHERE id=? AND revision=? AND round_id IS NULL AND bot_token_hash IS NOT NULL AND phase='queued' AND start_request_id=? AND round_number=? AND start_expires_at>? AND expires_at>? AND ${NEW_ENGINE})`;
export const IMAGE_BEGIN_ROOM = `UPDATE arena_rooms SET round_id=?,round_number=round_number+1,phase='loading',human_ready=1,revision=revision+1 WHERE id=? AND revision=? AND round_id IS NULL AND bot_token_hash IS NOT NULL AND phase='queued' AND start_request_id=? AND round_number=? AND start_expires_at>? AND expires_at>? AND ${NEW_ENGINE} AND EXISTS (SELECT 1 FROM arena_rounds WHERE id=?)`;
export const IMAGE_BEGIN_REMOTE = `UPDATE arena_remote_rooms SET engine_stage='loading_images' WHERE room_id=? AND engine_token_hash=? AND EXISTS (SELECT 1 FROM arena_rooms WHERE id=? AND phase='loading' AND round_id=? AND start_request_id=?)`;

const PRESTART_ROOM = `EXISTS (SELECT 1 FROM arena_rooms WHERE id=? AND round_id=arena_rounds.id AND start_request_id=? AND expires_at>? AND (phase='loading' OR (phase='active' AND arena_rounds.start_at>?)))`;
// A mount invalidates the previous load epoch once. Late mounts/decodes from
// that epoch cannot clear or ready the new one.
export const IMAGE_RESET_ROUND = `UPDATE arena_rounds SET image_load_id=?,human_images_ready=0,bot_images_ready=0,engine_images_ready=0,start_at=?,deadline_at=? WHERE id=? AND image_load_id=? AND ${PRESTART_ROOM}`;
export const IMAGE_RESET_ROOM = `UPDATE arena_rooms SET phase='loading',revision=revision+1 WHERE id=? AND round_id=? AND start_request_id=? AND expires_at>? AND phase IN ('loading','active') AND EXISTS (SELECT 1 FROM arena_rounds WHERE id=arena_rooms.round_id AND image_load_id=? AND start_at=?)`;

export function imageAckStatement(role) {
  if (!["human", "bot", "engine"].includes(role)) throw new Error("Invalid image role");
  const column = role === "bot" ? "bot_images_ready" : `${role}_images_ready`;
  return `UPDATE arena_rounds SET ${column}=1 WHERE id=? AND image_load_id=? AND loading_expires_at>? AND ${PRESTART_ROOM}`;
}
const ALL_IMAGES = `human_images_ready=1 AND bot_images_ready=1 AND engine_images_ready=1`;
const LIVE_BARRIER_ENGINE = `EXISTS (SELECT 1 FROM arena_remote_rooms WHERE room_id=? AND engine_protocol=3 AND engine_ready=1 AND engine_stage IN ('loading_images','images_ready') AND engine_seen_at>=? AND engine_seen_at<=?)`;
export const IMAGE_RELEASE_ROUND = `UPDATE arena_rounds SET start_at=?,deadline_at=? WHERE id=? AND image_load_id=? AND start_at=? AND loading_expires_at>? AND ${ALL_IMAGES} AND EXISTS (SELECT 1 FROM arena_rooms WHERE id=? AND round_id=arena_rounds.id AND phase='loading' AND start_request_id=? AND bot_token_hash IS NOT NULL AND expires_at>?) AND ${LIVE_BARRIER_ENGINE}`;
export const IMAGE_RELEASE_ROOM = `UPDATE arena_rooms SET phase='active',revision=revision+1 WHERE id=? AND round_id=? AND phase='loading' AND start_request_id=? AND expires_at>? AND EXISTS (SELECT 1 FROM arena_rounds WHERE id=arena_rooms.round_id AND image_load_id=? AND start_at=? AND ${ALL_IMAGES})`;

// Cancellation is pinned to the observed epoch/room and, for automatic engine
// expiry, to the exact heartbeat snapshot to preserve a concurrently fresh beat.
export const IMAGE_CANCEL_REMOTE = `UPDATE arena_remote_rooms SET selected_json='[]',sequence=0,last_selection_at=NULL,engine_ready=0,engine_stage=? WHERE room_id=? AND (? IN ('human_cancelled','image_load_failed','image_load_timeout') OR (engine_seen_at IS ? AND engine_stage=?)) AND EXISTS (SELECT 1 FROM arena_rooms AS room JOIN arena_rounds AS round ON round.id=room.round_id WHERE room.id=? AND room.round_id=? AND room.start_request_id=? AND room.revision=? AND room.expires_at>? AND round.image_load_id=? AND (room.phase='loading' OR (room.phase='active' AND round.start_at>?)))`;
export const IMAGE_CANCEL_ROOM = `UPDATE arena_rooms SET phase='lobby',round_id=NULL,start_request_id=NULL,start_requested_at=NULL,start_expires_at=NULL,last_start_cancel_reason=?,revision=revision+1 WHERE id=? AND round_id=? AND start_request_id=? AND revision=? AND expires_at>? AND phase IN ('loading','active') AND EXISTS (SELECT 1 FROM arena_rounds WHERE id=arena_rooms.round_id AND image_load_id=? AND (start_at>? OR start_at=?)) AND EXISTS (SELECT 1 FROM arena_remote_rooms WHERE room_id=arena_rooms.id AND engine_ready=0 AND engine_stage=?)`;

export function imageReleaseBindings(roomId, roundId, ticket, imageLoadId, now, engineFreshMs = ENGINE_FRESH_MS) {
  const startAt = now + COMMON_COUNTDOWN_MS, deadlineAt = startAt + 90_000;
  return { startAt, deadlineAt,
    round: [startAt, deadlineAt, roundId, imageLoadId, UNSTARTED_AT, now, roomId, ticket, now, roomId, now-engineFreshMs, now],
    room: [roomId, roundId, ticket, now, imageLoadId, startAt] };
}

/** Readiness ACKs are idempotent and clients may remember them. A heartbeat
 * can race the release CAS clock, so every loading-state read must retry an
 * already-ready triple rather than relying on another ACK to arrive. */
export async function recoverPreparedImages(room, round, now, commit) {
  if (room.phase !== "loading" || !round?.image_load_id
    || round.human_images_ready !== 1 || round.bot_images_ready !== 1 || round.engine_images_ready !== 1) return false;
  return commit(imageReleaseBindings(room.id, round.id, room.start_request_id, round.image_load_id, now));
}
