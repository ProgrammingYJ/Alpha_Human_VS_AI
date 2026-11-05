import { env } from "cloudflare:workers";
import { ArenaError, THEMES, bankReadiness, exactMatch, makeChallenge, randomInt, validatePhotoMetadata, validateSelection } from "./logic.mjs";
import { START_ROUND_INSERT, START_ROOM_UPDATE, FINISH_IF_CORRECT, submitStatement } from "./statements.mjs";
import { sessionResetCutoff, requireCurrentSession, SESSION_PHOTO_FOR_CURRENT_ROUND } from "./session-reset.mjs";
import { ownerMatches } from "./authorization.mjs";
import { ACTIVATE_PHOTO_BANK, SELECT_PHOTO_BANK, validateActivePhotoBank, validateActivePhotoIds } from "./photo-bank.mjs";
import { projectStateAfterRemoteRead } from "./state-projection.mjs";
import { ENGINE_FRESH_MS, TILE_INTERVAL_MS, REMOTE_HEARTBEAT, REMOTE_SELECT, REMOTE_SUBMIT, REMOTE_NEXT_RESET, REMOTE_NEXT_ROOM, REMOTE_SUBMITTED_STAGE,
  engineConnected, remoteReady, selectionDecision, validateEngineAction, validateLane, validateRoomMode } from "./remote.mjs";
import { QUEUE_TTL_MS, GPU_QUEUE, GPU_CANCEL_REMOTE, GPU_CANCEL_ROOM,
  queueCancellationReason, validateStartRevision, validateStartRequest } from "./gpu-start.mjs";
import { PLAN_BUFFER_MS, PLAN_ACCEPT, PLAN_SETTLE_ROUND, PLAN_HUMAN_SUBMIT, planFor, samePlan, validatePlanIndices } from "./selection-plan.mjs";
import { IMAGE_LOADING_MS, UNSTARTED_AT, IMAGE_BEGIN_INSERT, IMAGE_BEGIN_ROOM, IMAGE_BEGIN_REMOTE,
  IMAGE_RESET_ROUND, IMAGE_RESET_ROOM, IMAGE_RELEASE_ROUND, IMAGE_RELEASE_ROOM, IMAGE_CANCEL_REMOTE, IMAGE_CANCEL_ROOM,
  imageAckStatement, imageReleaseBindings, imageCancellationReason, prestartImages, validateImageEpoch, recoverPreparedImages } from "./image-barrier.mjs";

type Role = "human" | "bot" | "engine";
type Bindings = { DB?: D1Database; BUCKET?: R2Bucket; ADMIN_KEY?: string; ADMIN_OWNER_ID?: string; ARENA_SESSION_RESET_BEFORE_MS?: string };
type Room = {
  id: string; code: string; human_token_hash: string; bot_token_hash: string | null;
  human_ready: number; bot_ready: number; phase: string; round_id: string | null;
  round_number: number; revision: number; created_at: number; expires_at: number;
  start_request_id: string | null; start_requested_at: number | null; start_expires_at: number | null; last_start_cancel_reason: string | null;
};
type Round = {
  id: string; room_id: string; number: number; theme_id: keyof typeof THEMES;
  tiles_json: string; answer_json: string; start_at: number; deadline_at: number;
  human_submitted_at: number | null; human_correct: number | null; human_elapsed_ms: number | null;
  bot_submitted_at: number | null; bot_correct: number | null; bot_elapsed_ms: number | null;
  bot_plan_indices_json: string | null; bot_plan_start_at: number | null; bot_plan_submit_at: number | null; bot_plan_correct: number | null;
  image_load_id: string | null; loading_expires_at: number | null; human_images_ready: number; bot_images_ready: number; engine_images_ready: number;
};
type Photo = { id: string; object_key: string; mime_type: string; byte_size: number; sha256: string; group_id: string; metadata_json: string; created_at: number; active: number };
type RemoteRoom = { room_id: string; lane: "A" | "B"; engine_token_hash: string | null;
  engine_seen_at: number | null; engine_stage: string; engine_ready: number; engine_protocol: number; selected_json: string;
  sequence: number; last_selection_at: number | null };
const ROUND_DURATION_MS = 90_000;
const ROOM_DURATION_MS = 24 * 60 * 60 * 1000;
const UPLOAD_LIMIT = 8 * 1024 * 1024;
const RESPONSE_HEADERS = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };

function bindings() { return env as unknown as Bindings; }
function db() {
  const result = bindings().DB;
  if (!result) throw new ArenaError("storage_unavailable", "공유 저장소 연결이 준비되지 않았습니다.", 503);
  return result;
}
function bucket() {
  const result = bindings().BUCKET;
  if (!result) throw new ArenaError("storage_unavailable", "사진 저장소 연결이 준비되지 않았습니다.", 503);
  return result;
}
function json(value: unknown, status = 200) { return Response.json(value, { status, headers: RESPONSE_HEADERS }); }
export async function arenaHealth() {
  sessionResetCutoff(bindings().ARENA_SESSION_RESET_BEFORE_MS);
  await db().prepare("SELECT image_load_id FROM arena_rounds LIMIT 1").first();
  bucket();
  return json({ ok: true, protocolVersion: 3, imageReadinessBarrier: true, sessionResetSupported: true,
    minimumTileIntervalMs: TILE_INTERVAL_MS, serverNow: Date.now() });
}
export async function route(action: () => Promise<Response>) {
  try {
    // Invalid reset configuration must never silently restore old capabilities.
    sessionResetCutoff(bindings().ARENA_SESSION_RESET_BEFORE_MS);
    return await action();
  } catch (error) {
    if (error instanceof ArenaError) return json({ error: error.message, code: error.code }, error.status);
    // SQL, object keys, provenance and secret values must never enter an error response.
    console.error("[alpha-arena] request failed", error instanceof Error ? error.name : "UnknownError");
    return json({ error: "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.", code: "internal_error" }, 500);
  }
}
function checkOrigin(request: Request) {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin) throw new ArenaError("invalid_origin", "같은 사이트에서 다시 요청해 주세요.", 403);
}
async function boundedBytes(request: Request, limit: number) {
  const advertised = request.headers.get("content-length");
  if (advertised && (!/^\d+$/.test(advertised) || Number(advertised) > limit)) throw new ArenaError("body_too_large", "요청이 너무 큽니다.", 413);
  const reader = request.body?.getReader(); if (!reader) return new Uint8Array();
  const chunks: Uint8Array[] = []; let size = 0;
  while (true) {
    const part = await reader.read(); if (part.done) break;
    size += part.value.byteLength;
    if (size > limit) { await reader.cancel(); throw new ArenaError("body_too_large", "요청이 너무 큽니다.", 413); }
    chunks.push(part.value);
  }
  const bytes = new Uint8Array(size); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return bytes;
}
async function payload(request: Request): Promise<Record<string, unknown>> {
  checkOrigin(request);
  if (!request.headers.get("content-type")?.includes("application/json")) throw new ArenaError("invalid_body", "JSON 요청이 필요합니다.", 415);
  try {
    const value = JSON.parse(new TextDecoder().decode(await boundedBytes(request, 8192)));
    if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error();
    return value;
  } catch (error) { if (error instanceof ArenaError) throw error; throw new ArenaError("invalid_body", "요청 내용을 확인해 주세요."); }
}
async function digest(value: string | Uint8Array) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  const buffer = new Uint8Array(bytes).buffer;
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", buffer))].map((n) => n.toString(16).padStart(2, "0")).join("");
}
function constantEqual(first: string, second: string) {
  if (first.length !== second.length) return false;
  let difference = 0; for (let i = 0; i < first.length; i++) difference |= first.charCodeAt(i) ^ second.charCodeAt(i);
  return difference === 0;
}
function newToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
}
function newCode() {
  const letters = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  return Array.from({ length: 8 }, () => letters[randomInt(letters.length)]).join("");
}
function validId(value: string) { return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value); }
async function getRoom(id: string) {
  if (!validId(id)) throw new ArenaError("not_found", "대기실을 찾을 수 없습니다.", 404);
  const room = await db().prepare("SELECT * FROM arena_rooms WHERE id = ?").bind(id).first<Room>();
  if (!room) throw new ArenaError("not_found", "대기실을 찾을 수 없습니다.", 404);
  requireCurrentSession(room, bindings().ARENA_SESSION_RESET_BEFORE_MS);
  if (Date.now() >= room.expires_at) throw new ArenaError("room_expired", "대기실이 만료됐습니다. 새로 만들어 주세요.", 410);
  return room;
}
async function authorize(request: Request, room: Room): Promise<Role> {
  const header = request.headers.get("authorization") ?? "";
  if (!/^Bearer [A-Za-z0-9_-]{43}$/.test(header)) throw new ArenaError("unauthorized", "대기실 연결 정보가 필요합니다.", 401);
  const hash = await digest(header.slice(7));
  if (constantEqual(hash, room.human_token_hash)) return "human";
  if (room.bot_token_hash && constantEqual(hash, room.bot_token_hash)) return "bot";
  const remote = await getRemote(room.id);
  if (remote?.engine_token_hash && constantEqual(hash, remote.engine_token_hash)) return "engine";
  throw new ArenaError("unauthorized", "대기실 연결 정보를 확인해 주세요.", 401);
}
async function getRemote(id: string) {
  return db().prepare("SELECT * FROM arena_remote_rooms WHERE room_id = ?").bind(id).first<RemoteRoom>();
}
async function getRound(room: Room) {
  if (!room.round_id) return null;
  return db().prepare("SELECT * FROM arena_rounds WHERE id = ? AND room_id = ?").bind(room.round_id, room.id).first<Round>();
}
async function cancelPending(room: Room, remote: RemoteRoom, reason: string, now: number) {
  const stage = reason === "engine_error" ? "error" : "connected";
  await db().batch([
    db().prepare(GPU_CANCEL_REMOTE).bind(stage, room.id, reason, remote.engine_seen_at, remote.engine_stage, room.id, room.start_request_id, room.revision, now),
    db().prepare(GPU_CANCEL_ROOM).bind(reason, room.id, room.start_request_id, room.revision, now, stage),
  ]);
  return getRoom(room.id);
}
async function cancelImageLoad(room: Room, round: Round, remote: RemoteRoom, reason: string, now: number) {
  const stage = reason === "engine_error" ? "error" : "connected";
  await db().batch([
    db().prepare(IMAGE_CANCEL_REMOTE).bind(stage, room.id, reason, remote.engine_seen_at, remote.engine_stage,
      room.id, round.id, room.start_request_id, room.revision, now, round.image_load_id, now),
    db().prepare(IMAGE_CANCEL_ROOM).bind(reason, room.id, round.id, room.start_request_id, room.revision,
      now, round.image_load_id, now, UNSTARTED_AT, stage),
  ]);
  return getRoom(room.id);
}
async function settlePending(room: Room) {
  const round = await getRound(room);
  if (prestartImages(room, round, Date.now())) {
    const remote = await getRemote(room.id); const now = Date.now();
    const reason = imageCancellationReason(room, round, remote, now);
    if (reason && remote && round) return cancelImageLoad(room, round, remote, reason, now);
    const released = await recoverPreparedImages(room, round, now, async (release: ReturnType<typeof imageReleaseBindings>) => {
      const results = await db().batch([
        db().prepare(IMAGE_RELEASE_ROUND).bind(...release.round),
        db().prepare(IMAGE_RELEASE_ROOM).bind(...release.room),
      ]);
      return results[1].meta.changes === 1;
    });
    return released ? getRoom(room.id) : room;
  }
  if (room.phase !== "queued") return room;
  const remote = await getRemote(room.id); const now = Date.now();
  if (!remote) throw new ArenaError("storage_unavailable", "원격 대기실 상태를 확인할 수 없습니다.", 503);
  const reason = queueCancellationReason(room, remote, now);
  return reason ? cancelPending(room, remote, reason, now) : room;
}
async function settleRoom(room: Room, round: Round | null, now: number) {
  if (room.phase === "active" && round?.bot_plan_indices_json != null && round.bot_correct === null && round.bot_plan_submit_at !== null && now >= round.bot_plan_submit_at) {
    await db().batch([
      db().prepare(PLAN_SETTLE_ROUND).bind(round.id, now, room.id, now),
      db().prepare(FINISH_IF_CORRECT).bind(room.id, round.id, round.id),
    ]);
    room = await getRoom(room.id);
  }
  if (room.phase === "active" && round && (now >= round.deadline_at || round.human_correct === 1 || round.bot_correct === 1)) {
    await db().prepare("UPDATE arena_rooms SET phase = 'result', revision = revision + 1 WHERE id = ? AND round_id = ? AND phase = 'active'").bind(room.id, round.id).run();
    return getRoom(room.id);
  }
  return room;
}
async function stateFor(id: string, role: Role) {
  for (let attempt = 0; attempt < 3; attempt++) {
    let room = await settlePending(await getRoom(id)); let round = await getRound(room); const now = Date.now();
    const revision = room.revision;
    room = await settleRoom(room, round, now);
    // A concurrent correct submission may have ended the room while timeout
    // settlement was running. Read its round again before projecting a winner.
    if (room.revision !== revision) continue;
    // A due wrong plan records its single attempt without ending the round.
    if (round?.bot_plan_submit_at != null && round.bot_correct === null && now >= round.bot_plan_submit_at) round = await getRound(room);
    const latest = await getRoom(id);
    if (latest.revision !== room.revision || latest.round_id !== round?.id && latest.round_id !== null) continue;
    return projectStateAfterRemoteRead(room, round, role, getRemote);
  }
  throw new ArenaError("room_changed", "경기 상태가 바뀌었습니다. 다시 확인해 주세요.", 409);
}
async function activePhotos() {
  const result = await db().prepare("SELECT * FROM arena_photos WHERE active = 1 ORDER BY id LIMIT 5000").all<Photo>();
  return result.results.map((row) => ({ id: row.id, groupId: row.group_id, sha256: row.sha256, metadata: JSON.parse(row.metadata_json) }));
}

export async function createRoom(request: Request) {
  const value = await payload(request); const lane = validateRoomMode(value);
  const id = crypto.randomUUID(), token = newToken(), hash = await digest(token), now = Date.now();
  // A same-millisecond creation must not return a room that is already fenced.
  requireCurrentSession({ created_at: now }, bindings().ARENA_SESSION_RESET_BEFORE_MS, now);
  for (let attempt = 0; attempt < 5; attempt++) {
    const code = newCode();
    try {
      const insert = db().prepare("INSERT INTO arena_rooms (id, code, human_token_hash, human_ready, bot_ready, phase, round_number, revision, created_at, expires_at) VALUES (?, ?, ?, 1, 0, 'lobby', 0, 0, ?, ?)").bind(id, code, hash, now, now + ROOM_DURATION_MS);
      if (lane) await db().batch([insert, db().prepare("INSERT INTO arena_remote_rooms (room_id,lane) VALUES (?,?)").bind(id, lane)]);
      else await insert.run();
      return json({ roomId: id, code, token, state: await stateFor(id, "human") }, 201);
    } catch (error) { if (!(error instanceof Error) || !String(error.message).includes("UNIQUE")) throw error; }
  }
  throw new ArenaError("busy", "대기실을 다시 만들어 주세요.", 503);
}
export async function joinRoom(request: Request) {
  const value = await payload(request);
  if (!["bot", "engine"].includes(value.role as string) || typeof value.code !== "string" || !/^[A-Z2-9]{8}$/.test(value.code.trim().toUpperCase())) throw new ArenaError("invalid_code", "8자리 대기실 코드를 확인해 주세요.");
  const code = value.code.trim().toUpperCase();
  const room = await db().prepare("SELECT * FROM arena_rooms WHERE code = ?").bind(code).first<Room>();
  if (!room) throw new ArenaError("not_found", "참가 가능한 대기실을 찾을 수 없습니다.", 404);
  requireCurrentSession(room, bindings().ARENA_SESSION_RESET_BEFORE_MS);
  if (Date.now() >= room.expires_at) throw new ArenaError("not_found", "참가 가능한 대기실을 찾을 수 없습니다.", 404);
  const remote = await getRemote(room.id); validateLane(value.lane, remote);
  if (value.role === "engine" && !remote) throw new ArenaError("invalid_mode", "원격 엔진은 remote 대기실에만 연결할 수 있습니다.", 409);
  const token = newToken();
  if (value.role === "engine") {
    const result = await db().prepare("UPDATE arena_remote_rooms SET engine_token_hash = ?, engine_stage = 'connected', engine_ready = 0 WHERE room_id = ? AND engine_token_hash IS NULL AND EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND phase = 'lobby' AND expires_at > ?)").bind(await digest(token), room.id, room.id, Date.now()).run();
    if (result.meta.changes !== 1) throw new ArenaError("engine_already_connected", "이미 로컬 엔진이 연결됐습니다. 기존 PC 엔진을 유지하고 결과 화면에서 다음 참가자를 준비해 주세요.", 409);
    return json({ roomId: room.id, code: room.code, token, state: await stateFor(room.id, "engine") });
  }
  const result = await db().prepare("UPDATE arena_rooms SET bot_token_hash = ?, bot_ready = 0, revision = revision + 1 WHERE id = ? AND bot_token_hash IS NULL AND phase = 'lobby'").bind(await digest(token), room.id).run();
  if (result.meta.changes !== 1) throw new ArenaError("bot_already_connected", "이미 AI 기기가 연결됐습니다. 해당 기기에서 계속해 주세요.", 409);
  return json({ roomId: room.id, code: room.code, token, state: await stateFor(room.id, "bot") });
}
export async function readRoom(request: Request, id: string) {
  const room = await getRoom(id); const role = await authorize(request, room);
  return json(await stateFor(room.id, role));
}
export async function readyRoom(request: Request, id: string) {
  const value = await payload(request); const room = await getRoom(id); const role = await authorize(request, room);
  if (role === "engine" || role === "bot" && await getRemote(id)) throw new ArenaError("forbidden", "원격 봇 화면은 읽기 전용입니다. 로컬 엔진의 준비를 기다려 주세요.", 403);
  if (typeof value.ready !== "boolean") throw new ArenaError("invalid_body", "준비 상태를 확인해 주세요.");
  const column = role === "human" ? "human_ready" : "bot_ready";
  const result = await db().prepare(`UPDATE arena_rooms SET ${column} = ?, revision = revision + 1 WHERE id = ? AND phase IN ('lobby', 'result')`).bind(value.ready ? 1 : 0, id).run();
  if (!result.meta.changes) throw new ArenaError("round_in_progress", "문제가 진행 중입니다.", 409);
  return json({ state: await stateFor(id, role) });
}
export async function startRound(request: Request, id: string) {
  const value = await payload(request); let room = await getRoom(id); const role = await authorize(request, room);
  if (role !== "human") throw new ArenaError("forbidden", "사람 화면에서 시작해 주세요.", 403);
  room = await settlePending(room);
  room = await settleRoom(room, await getRound(room), Date.now());
  const remote = await getRemote(id); const checkedAt = Date.now();
  if (!remote && room.round_number > 0) throw new ArenaError("already_played", "한 참가자는 한 판만 진행합니다. 다음 참가자는 새 대기실을 만들어 주세요.", 409);
  if (remote && (room.phase !== "lobby" || room.round_id !== null)) throw new ArenaError("round_in_progress", "결과 화면에서 다음 참가자 준비를 먼저 눌러 주세요.", 409);
  if (remote) {
    validateStartRevision(value.expectedRevision);
    if (value.expectedRevision !== room.revision) throw new ArenaError("room_changed", "대기실 상태가 바뀌었습니다. 다시 확인해 주세요.", 409);
    if (remote.engine_protocol !== 3) throw new ArenaError("protocol_upgrade_required", "사진 준비를 지원하는 최신 PC 실행기로 다시 시작해 주세요.", 409);
  }
  if (remote ? !remoteReady(room, remote, checkedAt) || remote.engine_stage !== "ready" : !room.bot_token_hash || !room.bot_ready) throw new ArenaError("bot_not_ready", "AI 화면 연결과 로컬 엔진의 준비를 기다려 주세요.", 409);
  if (!["lobby", "result"].includes(room.phase)) throw new ArenaError("round_in_progress", "이미 문제가 시작됐습니다.", 409);
  const photos = await activePhotos(); const readiness = bankReadiness(photos);
  if (readiness.some((item) => !item.ready)) throw new ArenaError("bank_not_ready", "사진 문제은행이 준비되지 않았습니다. 운영자에게 문의해 주세요.", 409);
  if (remote) {
    const now = Date.now();
    const result = await db().prepare(GPU_QUEUE).bind(crypto.randomUUID(), now, now + QUEUE_TTL_MS, id, room.revision, now, now - ENGINE_FRESH_MS, now).run();
    if (result.meta.changes !== 1) throw new ArenaError("room_changed", "준비나 연결 상태가 바뀌었습니다. 다시 확인해 주세요.", 409);
    return json({ state: await stateFor(id, role) });
  }
  const themeIds = Object.keys(THEMES); const themeId = themeIds[randomInt(themeIds.length)];
  const challenge = makeChallenge(photos, themeId); const roundId = crypto.randomUUID();
  const startAt = Date.now() + 2000; const deadlineAt = startAt + ROUND_DURATION_MS;
  // D1 batch is a single transaction. Both writes use the same room revision;
  // concurrent starts or ready changes cannot mint two active rounds.
  const results = await db().batch([
    db().prepare(START_ROUND_INSERT).bind(roundId, id, room.round_number + 1, themeId, JSON.stringify(challenge.tiles), JSON.stringify(challenge.answerTileIds), startAt, deadlineAt, id, room.revision),
    db().prepare(START_ROOM_UPDATE).bind(roundId, id, room.revision, roundId),
  ]);
  if (results[1].meta.changes !== 1) throw new ArenaError("room_changed", "대기실 상태가 바뀌었습니다. 다시 시작해 주세요.", 409);
  return json({ state: await stateFor(id, role) });
}
export async function cancelStart(request: Request, id: string) {
  const value = await payload(request); let room = await getRoom(id); const role = await authorize(request, room);
  if (role !== "human") throw new ArenaError("forbidden", "사람 화면에서 시작 대기를 취소해 주세요.", 403);
  const remote = await getRemote(id);
  if (!remote) throw new ArenaError("invalid_mode", "원격 대기실에서만 시작 대기를 취소할 수 있습니다.", 409);
  validateStartRequest(value.requestId);
  room = await settlePending(room);
  const round = await getRound(room);
  if (round && prestartImages(room, round, Date.now()) && room.start_request_id === value.requestId) {
    await cancelImageLoad(room, round, remote, "human_cancelled", Date.now());
    return json({ state: await stateFor(id, role) });
  }
  if (room.phase !== "queued" || room.start_request_id !== value.requestId) throw new ArenaError("start_request_changed", "시작 요청이 이미 취소됐거나 진행 상태가 바뀌었습니다.", 409);
  await cancelPending(room, remote, "human_cancelled", Date.now());
  return json({ state: await stateFor(id, role) });
}
async function isResetLobby(room: Room, expectedRound: string) {
  if (room.phase !== "lobby" || room.round_id !== null || room.round_number < 1) return false;
  const latest = await db().prepare("SELECT id FROM arena_rounds WHERE room_id = ? AND number = ?").bind(room.id, room.round_number).first<{ id: string }>();
  return latest?.id === expectedRound;
}
export async function nextParticipant(request: Request, id: string) {
  const value = await payload(request); let room = await getRoom(id); const role = await authorize(request, room);
  if (role !== "human") throw new ArenaError("forbidden", "인간 화면에서 다음 참가자를 준비해 주세요.", 403);
  if (!await getRemote(id)) throw new ArenaError("invalid_mode", "기존 OS 대결은 새 대기실을 만들어 주세요.", 409);
  if (typeof value.roundId !== "string" || !validId(value.roundId)) throw new ArenaError("invalid_round", "종료한 문제 번호가 필요합니다.");
  const expected = value.roundId;
  room = await settleRoom(room, await getRound(room), Date.now());
  if (await isResetLobby(room, expected)) return json({ state: await stateFor(id, role) });
  if (room.round_id !== expected) throw new ArenaError("round_changed", "이미 다른 참가자 문제로 바뀌었습니다.", 409);
  if (room.phase !== "result") throw new ArenaError("round_in_progress", "현재 대결이 끝난 뒤 다음 참가자를 준비해 주세요.", 409);
  const now = Date.now();
  const results = await db().batch([
    db().prepare(REMOTE_NEXT_RESET).bind(id, id, expected, room.revision, now),
    db().prepare(REMOTE_NEXT_ROOM).bind(id, expected, room.revision, now),
  ]);
  if (results[1].meta.changes !== 1) {
    const latest = await getRoom(id);
    if (!await isResetLobby(latest, expected)) throw new ArenaError("round_changed", "참가자 상태가 바뀌었습니다. 다시 확인해 주세요.", 409);
  }
  return json({ state: await stateFor(id, role) });
}
export async function submitRound(request: Request, id: string) {
  const value = await payload(request); const room = await getRoom(id); const role = await authorize(request, room); const round = await getRound(room); const now = Date.now();
  if (role === "engine" || role === "bot" && await getRemote(id)) throw new ArenaError("forbidden", "원격 봇 선택과 제출은 로컬 엔진만 수행합니다.", 403);
  if (!round || value.roundId !== round.id) throw new ArenaError("round_changed", "현재 문제를 다시 확인해 주세요.", 409);
  if (room.phase !== "active") throw new ArenaError("round_ended", "이미 경기가 끝났습니다.", 409);
  if (now < round.start_at) throw new ArenaError("not_started", "공통 시작 시각을 기다려 주세요.", 409);
  if (now >= round.deadline_at) { await settleRoom(room, round, now); throw new ArenaError("round_ended", "시간이 끝났습니다.", 409); }
  const tiles: { id: string; photoId: string }[] = JSON.parse(round.tiles_json);
  const selected = validateSelection(value.tileIds, tiles.map((tile) => tile.id));
  const correct = exactMatch(selected, JSON.parse(round.answer_json)); const elapsedMs = now - round.start_at;
  const humanSubmit = role === "human" ? db().prepare(PLAN_HUMAN_SUBMIT).bind(correct ? now : null, correct ? 1 : 0, elapsedMs, round.id, now, now, id, round.id, now)
    : db().prepare(submitStatement(role)).bind(correct ? now : null, correct ? 1 : 0, elapsedMs, round.id, now, now, id, round.id);
  const results = await db().batch([
    db().prepare(PLAN_SETTLE_ROUND).bind(round.id, now, id, now),
    humanSubmit,
    db().prepare(FINISH_IF_CORRECT).bind(id, round.id, round.id),
  ]);
  if (results[1].meta.changes !== 1) throw new ArenaError("round_ended", "이미 정답이 제출됐거나 경기가 종료됐습니다.", 409);
  return json({ correct, elapsedMs, state: await stateFor(id, role) });
}

async function acknowledgeImages(value: Record<string, unknown>, room: Room, role: Role) {
  const round = await getRound(room); let now = Date.now();
  validateStartRequest(value.requestId); validateImageEpoch(value.imageLoadId);
  if (!round || round.id !== value.roundId || room.start_request_id !== value.requestId
    || round.image_load_id !== value.imageLoadId || role === "engine" && room.round_number !== value.roundNumber) {
    throw new ArenaError("image_load_changed", "현재 사진 준비 상태를 다시 확인해 주세요.", 409);
  }
  if (!prestartImages(room, round, now)) throw new ArenaError("not_loading", "사진 준비 단계가 끝났습니다.", 409);
  const remote = await getRemote(room.id);
  now = Date.now();
  if (!remote || remote.engine_protocol !== 3) throw new ArenaError("protocol_upgrade_required", "최신 PC 실행기가 필요합니다.", 409);
  if (value.failed === true) {
    await cancelImageLoad(room, round, remote, "image_load_failed", now);
    return json({ state: await stateFor(room.id, role) });
  }
  if (value.ready === false && role !== "engine") {
    const nextEpoch = crypto.randomUUID();
    const result = await db().batch([
      db().prepare(IMAGE_RESET_ROUND).bind(nextEpoch, UNSTARTED_AT, UNSTARTED_AT, round.id, round.image_load_id,
        room.id, room.start_request_id, now, now),
      db().prepare(IMAGE_RESET_ROOM).bind(room.id, round.id, room.start_request_id, now, nextEpoch, UNSTARTED_AT),
    ]);
    if (result[0].meta.changes !== 1) throw new ArenaError("image_load_changed", "사진 준비 번호가 바뀌었습니다.", 409);
  } else {
    if (value.ready !== true) throw new ArenaError("invalid_body", "사진 준비 상태를 확인해 주세요.");
    const release = imageReleaseBindings(room.id, round.id, room.start_request_id, round.image_load_id, now);
    const result = await db().batch([
      db().prepare(imageAckStatement(role)).bind(round.id, round.image_load_id, now, room.id, room.start_request_id, now, now),
      db().prepare(IMAGE_RELEASE_ROUND).bind(...release.round),
      db().prepare(IMAGE_RELEASE_ROOM).bind(...release.room),
    ]);
    if (result[0].meta.changes !== 1) throw new ArenaError("image_load_changed", "사진 준비 상태가 바뀌었습니다.", 409);
  }
  return json({ state: await stateFor(room.id, role) });
}
export async function imagesReady(request: Request, id: string) {
  const value = await payload(request); const room = await settlePending(await getRoom(id));
  const role = await authorize(request, room);
  if (role === "engine" || !await getRemote(id)) throw new ArenaError("forbidden", "브라우저 사진 준비 요청이 필요합니다.", 403);
  return acknowledgeImages(value, room, role);
}

/** Remote mode: separate engine capability; the bot browser is only a viewer. */
async function beginReservedRound(value: Record<string, unknown>, room: Room, remote: RemoteRoom, engineHash: string) {
  if (remote.engine_protocol !== 3) throw new ArenaError("protocol_upgrade_required", "사진 준비를 지원하는 최신 PC 실행기로 다시 시작해 주세요.", 409);
  if (room.start_request_id !== value.requestId) throw new ArenaError(room.last_start_cancel_reason === "queue_expired" && !room.start_request_id ? "queue_expired" : "start_request_changed", "시작 대기가 취소됐거나 다른 요청으로 바뀌었습니다.", 409);
  if (["loading", "active", "result"].includes(room.phase) && room.round_id && room.round_number === (value.roundNumber as number) + 1) return json({ state: await stateFor(room.id, "engine") });
  if (room.phase !== "queued" || room.round_id !== null || room.round_number !== value.roundNumber) throw new ArenaError("start_request_changed", "현재 GPU 시작 요청을 다시 확인해 주세요.", 409);
  const checkedAt = Date.now();
  if (!room.bot_token_hash || !engineConnected(remote, checkedAt) || remote.engine_ready !== 1 || !["ready", "waiting_gpu", "reserved"].includes(remote.engine_stage)) throw new ArenaError("engine_not_ready", "로컬 엔진의 연결과 준비를 다시 확인해 주세요.", 409);
  const photos = await activePhotos();
  if (bankReadiness(photos).some(item => !item.ready)) throw new ArenaError("bank_not_ready", "사진 문제은행이 준비되지 않았습니다. 운영자에게 문의해 주세요.", 409);
  const themeIds = Object.keys(THEMES), themeId = themeIds[randomInt(themeIds.length)];
  const challenge = makeChallenge(photos, themeId), roundId = crypto.randomUUID(), now = Date.now();
  const startAt = UNSTARTED_AT, deadlineAt = UNSTARTED_AT, imageLoadId = crypto.randomUUID();
  const results = await db().batch([
    db().prepare(IMAGE_BEGIN_INSERT).bind(roundId, room.id, room.round_number + 1, themeId, JSON.stringify(challenge.tiles), JSON.stringify(challenge.answerTileIds), startAt, deadlineAt, imageLoadId, now + IMAGE_LOADING_MS,
      room.id, room.revision, value.requestId, value.roundNumber, now, now, engineHash, now - ENGINE_FRESH_MS, now),
    db().prepare(IMAGE_BEGIN_ROOM).bind(roundId, room.id, room.revision, value.requestId, value.roundNumber, now, now, engineHash, now - ENGINE_FRESH_MS, now, roundId),
    db().prepare(IMAGE_BEGIN_REMOTE).bind(room.id, engineHash, room.id, roundId, value.requestId),
  ]);
  if (results[1].meta.changes !== 1) {
    const latest = await settlePending(await getRoom(room.id));
    if (latest.start_request_id !== value.requestId || !latest.round_id || latest.round_number !== (value.roundNumber as number) + 1) throw new ArenaError("start_request_changed", "시작 요청이나 엔진 상태가 바뀌었습니다.", 409);
  }
  return json({ state: await stateFor(room.id, "engine") });
}
export async function engineAction(request: Request, id: string) {
  const value = await payload(request); let room = await getRoom(id); const role = await authorize(request, room);
  if (role !== "engine") throw new ArenaError("forbidden", "로컬 엔진 연결 정보가 필요합니다.", 403);
  room = await settlePending(room);
  const remote = await getRemote(id);
  if (!remote) throw new ArenaError("invalid_mode", "원격 엔진 대기실이 아닙니다.", 409);
  // Bind subsequent CAS writes to this request's capability even if a future
  // administrative rotation occurs between authorize() and this second read.
  const engineHash = await digest((request.headers.get("authorization") ?? "").slice(7));
  if (!remote.engine_token_hash || !constantEqual(engineHash, remote.engine_token_hash)) throw new ArenaError("unauthorized", "엔진 연결 정보를 다시 확인해 주세요.", 401);
  validateEngineAction(value);
  const now = Date.now();
  if (value.action === "begin") return beginReservedRound(value, room, remote, engineHash);
  if (value.action === "images_ready") return acknowledgeImages({ ...value, ready: true }, room, role);
  if (value.action === "heartbeat") {
    // A stale engine may restore liveness with its original capability, but it
    // cannot select or submit until this acknowledgement has succeeded.
    const protocol = value.protocolVersion ?? 1, requestId = value.requestId ?? null;
    const observedRound = await getRound(room);
    if (observedRound?.image_load_id && protocol !== 3) throw new ArenaError("protocol_upgrade_required", "사진 준비를 지원하는 최신 PC 실행기로 다시 시작해 주세요.", 409);
    if ((protocol === 1 && room.start_request_id !== null) || protocol !== 3 && room.phase === "queued") throw new ArenaError("protocol_upgrade_required", "GPU 예약을 지원하는 PC 실행기가 필요합니다.", 409);
    if (value.roundId !== room.round_id || value.roundNumber !== room.round_number) throw new ArenaError("round_changed", "이미 다른 참가자 문제로 바뀌었습니다.", 409);
    if (requestId !== room.start_request_id) throw new ArenaError("start_request_changed", "시작 요청이 바뀌었습니다. 현재 상태를 다시 확인해 주세요.", 409);
    if (value.stage === "ready" && room.phase !== "lobby") throw new ArenaError("round_in_progress", "시작한 엔진을 준비실 상태로 바꿀 수 없습니다.", 409);
    if (["waiting_gpu", "reserved"].includes(value.stage as string) && room.phase !== "queued") throw new ArenaError("round_in_progress", "GPU 예약 단계는 시작 대기 중에만 갱신할 수 있습니다.", 409);
    if (room.phase === "queued" && !["waiting_gpu", "reserved", "error"].includes(value.stage as string)) throw new ArenaError("round_in_progress", "현재 GPU 시작 대기를 확인해 주세요.", 409);
    if (prestartImages(room, observedRound, now) && !["loading_images", "images_ready", "error"].includes(value.stage as string)) throw new ArenaError("round_in_progress", "사진 준비 중에는 추론을 시작할 수 없습니다.", 409);
    if (room.phase === "result" && !["submitted", "inferencing", "error"].includes(value.stage as string)) throw new ArenaError("round_ended", "종료한 대결의 입력 단계는 갱신할 수 없습니다.", 409);
    const result = await db().prepare(REMOTE_HEARTBEAT).bind(now, value.stage, protocol, value.stage, value.stage, id, engineHash, now, id, now, value.roundId, value.roundNumber, requestId, value.stage, value.stage, protocol, value.stage, value.stage, now, protocol, value.stage).run();
    if (result.meta.changes !== 1) {
      const latest = await getRoom(id);
      if (latest.round_id !== value.roundId || latest.round_number !== value.roundNumber) throw new ArenaError("round_changed", "이미 다른 참가자 문제로 바뀌었습니다.", 409);
      if (latest.start_request_id !== requestId) throw new ArenaError("start_request_changed", "시작 요청이 바뀌었습니다. 현재 상태를 다시 확인해 주세요.", 409);
      if (value.stage === "ready" && latest.phase !== "lobby") throw new ArenaError("round_in_progress", "시작한 엔진을 준비실 상태로 바꿀 수 없습니다.", 409);
      if (latest.phase === "result" && !["submitted", "inferencing", "error"].includes(value.stage as string)) throw new ArenaError("round_ended", "종료한 대결의 입력 단계는 갱신할 수 없습니다.", 409);
      throw new ArenaError("engine_state_changed", "경기나 엔진 상태가 바뀌었습니다. 다시 확인해 주세요.", 409);
    }
    return json({ state: await stateFor(id, role) });
  }
  const round = await getRound(room);
  if (!round || value.roundId !== round.id) throw new ArenaError("round_changed", "현재 문제를 다시 확인해 주세요.", 409);
  if (value.action === "plan" && round.bot_plan_indices_json !== null) {
    if (!samePlan(round, validatePlanIndices(value.selectedIndices))) throw new ArenaError("plan_conflict", "이미 다른 고정 모델 선택이 등록됐습니다.", 409);
    return json({ plan: planFor(round), serverNow: Date.now() });
  }
  if (room.phase !== "active") throw new ArenaError("round_ended", "이미 경기가 끝났습니다.", 409);
  if (now < round.start_at) throw new ArenaError("not_started", "공통 시작 시각을 기다려 주세요.", 409);
  if (now >= round.deadline_at) { await settleRoom(room, round, now); throw new ArenaError("round_ended", "시간이 끝났습니다.", 409); }
  if (!engineConnected(remote, now) || remote.engine_ready !== 1 || remote.engine_stage === "error") throw new ArenaError("engine_not_ready", "로컬 엔진의 연결과 준비 상태를 다시 확인해 주세요.", 409);
  if (value.action === "plan") {
    const indices = validatePlanIndices(value.selectedIndices);
    // The round read above is asynchronous. Base the playback buffer and fresh
    // engine CAS on the clock immediately before acceptance, not before I/O.
    const planNow = Date.now();
    if (!engineConnected(remote, planNow)) throw new ArenaError("engine_not_ready", "로컬 엔진의 연결과 준비 상태를 다시 확인해 주세요.", 409);
    const startAt = planNow + PLAN_BUFFER_MS, submitAt = startAt + Math.max(0, indices.length - 1) * TILE_INTERVAL_MS;
    if (submitAt >= round.deadline_at) throw new ArenaError("plan_too_late", "남은 시간 안에 모델 선택을 완료할 수 없습니다.", 409);
    const tiles: { id: string }[] = JSON.parse(round.tiles_json);
    const correct = exactMatch(indices.map(index => tiles[index].id), JSON.parse(round.answer_json));
    const result = await db().prepare(PLAN_ACCEPT).bind(JSON.stringify(indices), startAt, submitAt, correct ? 1 : 0,
      round.id, planNow, submitAt, id, planNow, engineHash, planNow - ENGINE_FRESH_MS, planNow).run();
    if (result.meta.changes !== 1) {
      const latest = await getRound(await getRoom(id));
      if (latest?.id === round.id && latest.bot_plan_indices_json !== null) {
        if (!samePlan(latest, indices)) throw new ArenaError("plan_conflict", "이미 다른 고정 모델 선택이 등록됐습니다.", 409);
        return json({ plan: planFor(latest), serverNow: Date.now() });
      }
      throw new ArenaError("plan_changed", "경기나 엔진 선택 상태가 바뀌었습니다.", 409);
    }
    return json({ plan: { roundId: round.id, selectedIndices: indices, startAt, intervalMs: TILE_INTERVAL_MS, submitAt }, serverNow: Date.now() });
  }
  if (round.bot_plan_indices_json !== null) throw new ArenaError("plan_active", "이 문제는 이미 고정 모델 선택을 재생하고 있습니다.", 409);
  if (value.action === "select") {
    const sequence = value.sequence as number, tile = value.tileIndex as number;
    if (selectionDecision(remote, sequence, tile, now) === "duplicate") return json({ state: await stateFor(id, role) });
    const result = await db().prepare(REMOTE_SELECT).bind(tile, sequence, now, id, engineHash,
      now - ENGINE_FRESH_MS, now, sequence - 1, now - TILE_INTERVAL_MS, tile, round.id, now, now, now).run();
    if (result.meta.changes !== 1) {
      const latestRoom = await getRoom(id), latest = await getRemote(id);
      if (latestRoom.phase !== "active" || latestRoom.round_id !== round.id) throw new ArenaError("round_ended", "이미 경기가 끝났습니다.", 409);
      if (!latest || latest.engine_token_hash !== engineHash || !engineConnected(latest, Date.now()) || latest.engine_ready !== 1 || latest.engine_stage === "error") throw new ArenaError("engine_not_ready", "로컬 엔진의 연결과 준비 상태를 다시 확인해 주세요.", 409);
      if (latest && selectionDecision(latest, sequence, tile, Date.now()) === "duplicate") return json({ state: await stateFor(id, role) });
      throw new ArenaError("selection_changed", "선택 상태가 바뀌었습니다. 다시 확인해 주세요.", 409);
    }
    return json({ state: await stateFor(id, role) });
  }
  const selected: number[] = JSON.parse(remote.selected_json);
  const tiles: { id: string }[] = JSON.parse(round.tiles_json);
  const selectedIds = selected.map(index => tiles[index].id);
  const correct = exactMatch(selectedIds, JSON.parse(round.answer_json)); const elapsedMs = now - round.start_at;
  const results = await db().batch([
    db().prepare(REMOTE_SUBMIT).bind(correct ? now : null, correct ? 1 : 0, elapsedMs, round.id, now, now,
      id, now, engineHash, now - ENGINE_FRESH_MS, now, remote.sequence, remote.selected_json),
    db().prepare(FINISH_IF_CORRECT).bind(id, round.id, round.id),
  ]);
  if (results[0].meta.changes !== 1) throw new ArenaError("submission_changed", "경기가 끝났거나 선택이 바뀌었습니다. 상태를 다시 확인해 주세요.", 409);
  await db().prepare(REMOTE_SUBMITTED_STAGE).bind(id, engineHash, remote.sequence, remote.selected_json, id, round.id).run();
  return json({ correct, elapsedMs, state: await stateFor(id, role) });
}

async function requireAdmin(request: Request) {
  // Hosted identity injection belongs to Sites dispatch (app/chatgpt-auth.ts).
  // The portable starter mocks it only on loopback; no body/query identity,
  // browser-supplied role, email match or public default grants ownership.
  const owner = bindings().ADMIN_OWNER_ID;
  if (ownerMatches(owner, request.headers.get("oai-authenticated-user-id"))) return;
  const secret = bindings().ADMIN_KEY;
  if (!secret || secret.length < 16) {
    if (owner) throw new ArenaError("unauthorized", "사이트 소유자로 로그인해 주세요.", 401);
    throw new ArenaError("admin_unavailable", "운영자 인증이 서버에 설정되지 않았습니다.", 503);
  }
  const given = request.headers.get("x-admin-key") ?? "";
  if (!given || given.length > 1024 || !constantEqual(await digest(given), await digest(secret))) throw new ArenaError("unauthorized", "운영자 키를 확인해 주세요.", 401);
}
export async function adminStatus(request: Request) {
  await requireAdmin(request); const photos = await activePhotos();
  const topics = bankReadiness(photos).map((item) => ({ ...item, prompt: THEMES[item.id as keyof typeof THEMES].prompt }));
  return json({ ready: topics.every((item) => item.ready), photoCount: photos.length, topics, storage: { d1: true, r2: !!bindings().BUCKET } });
}
export async function adminPhotos(request: Request) {
  await requireAdmin(request);
  const includeInactive = new URL(request.url).searchParams.get("includeInactive") === "1";
  const rows = await db().prepare(`SELECT * FROM arena_photos ${includeInactive ? "" : "WHERE active = 1"} ORDER BY created_at DESC LIMIT 1000`).all<Photo>();
  return json({ photos: rows.results.map((row) => ({ id: row.id, url: `/api/admin/photos/${row.id}`,
    ...JSON.parse(row.metadata_json), active: row.active === 1, sha256: row.sha256 })) });
}
export async function activatePhotoBank(request: Request) {
  await requireAdmin(request);
  const ids = validateActivePhotoIds((await payload(request)).photoIds);
  const selected = await db().prepare(SELECT_PHOTO_BANK).bind(JSON.stringify(ids)).all<Photo>();
  const photos = selected.results.map(row => ({ id: row.id, groupId: row.group_id, sha256: row.sha256,
    metadata: JSON.parse(row.metadata_json) }));
  const topics = validateActivePhotoBank(ids, photos).map(topic => ({ ...topic, prompt: THEMES[topic.id as keyof typeof THEMES].prompt }));
  await db().prepare(ACTIVATE_PHOTO_BANK).bind(JSON.stringify(ids)).run();
  return json({ ready: true, photoCount: ids.length, topics });
}
function imageMime(bytes: Uint8Array) {
  if (bytes.length >= 8 && [137, 80, 78, 71, 13, 10, 26, 10].every((n, i) => bytes[i] === n)) return "image/png";
  if (bytes.length >= 4 && bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) return "image/jpeg";
  if (bytes.length >= 12 && new TextDecoder().decode(bytes.slice(0, 4)) === "RIFF" && new TextDecoder().decode(bytes.slice(8, 12)) === "WEBP") return "image/webp";
  throw new ArenaError("invalid_image", "JPEG·PNG·WebP 사진만 업로드할 수 있습니다.");
}
export async function uploadPhoto(request: Request) {
  await requireAdmin(request); checkOrigin(request);
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.startsWith("multipart/form-data")) throw new ArenaError("invalid_body", "사진과 메타데이터를 보내 주세요.", 415);
  const form = await new Response(await boundedBytes(request, UPLOAD_LIMIT + 65536), { headers: { "Content-Type": contentType } }).formData();
  const file = form.get("file"); const metadataText = form.get("metadata");
  if (!(file instanceof File) || !file.size || file.size > UPLOAD_LIMIT || typeof metadataText !== "string" || metadataText.length > 8192) throw new ArenaError("invalid_image", "8MB 이하 사진과 메타데이터가 필요합니다.");
  let rawMetadata; try { rawMetadata = JSON.parse(metadataText); } catch { throw new ArenaError("invalid_metadata", "메타데이터 JSON을 확인해 주세요."); }
  const metadata = validatePhotoMetadata(rawMetadata); const bytes = new Uint8Array(await file.arrayBuffer()); const mime = imageMime(bytes); const hash = await digest(bytes);
  if (await db().prepare("SELECT id FROM arena_photos WHERE sha256 = ?").bind(hash).first()) throw new ArenaError("duplicate_photo", "이미 등록된 원본 사진입니다.", 409);
  const id = crypto.randomUUID(), key = `photos/${id}`;
  await bucket().put(key, bytes, { httpMetadata: { contentType: mime } });
  try {
    await db().prepare("INSERT INTO arena_photos (id, object_key, mime_type, byte_size, sha256, group_id, metadata_json, created_at, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)").bind(id, key, mime, bytes.byteLength, hash, metadata.groupId, JSON.stringify(metadata), Date.now()).run();
  } catch (error) { await bucket().delete(key); throw error; }
  return json({ photo: { id, url: `/api/admin/photos/${id}`, ...metadata } }, 201);
}
async function serveObject(photo: Photo) {
  const object = await bucket().get(photo.object_key);
  if (!object) throw new ArenaError("not_found", "사진을 찾을 수 없습니다.", 404);
  return new Response(object.body, { headers: { ...RESPONSE_HEADERS, "Content-Type": photo.mime_type, "Content-Disposition": "inline", "Content-Security-Policy": "default-src 'none'; sandbox" } });
}
export async function readAdminPhoto(request: Request, id: string) {
  await requireAdmin(request); if (!validId(id)) throw new ArenaError("not_found", "사진을 찾을 수 없습니다.", 404);
  const photo = await db().prepare("SELECT * FROM arena_photos WHERE id = ?").bind(id).first<Photo>();
  if (!photo) throw new ArenaError("not_found", "사진을 찾을 수 없습니다.", 404);
  return serveObject(photo);
}
export async function readPhoto(id: string) {
  if (!validId(id)) throw new ArenaError("not_found", "사진을 찾을 수 없습니다.", 404);
  // Public opaque IDs belong to one current round. Prepared remote rounds
  // permit fetching before the clock; browser pixels stay hidden until start.
  const now = Date.now();
  const found = await db().prepare(SESSION_PHOTO_FOR_CURRENT_ROUND).bind(id, now, now).first<Photo & { visible_at: number; session_created_at: number }>();
  if (!found || Date.now() < found.visible_at) throw new ArenaError("not_found", "사진을 찾을 수 없습니다.", 404);
  requireCurrentSession({ created_at: found.session_created_at }, bindings().ARENA_SESSION_RESET_BEFORE_MS);
  return serveObject(found);
}
