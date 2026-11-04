/** Local-only HTTP capability audit. It never reads administrator answers. */
import test from "node:test";
import { releaseImageBarrier } from "./image-barrier.http-helpers.mjs";
import assert from "node:assert/strict";

const base = process.env.ALPHA_BASE_URL;
const forbidden = new Set(["answer_json", "answer", "answers", "answerTileIds", "answerCount", "metadata", "photoId", "personCount", "treeCount", "treeAtLeast3", "groupId", "source", "sha256", "objectKey", "engine_token_hash", "human_token_hash", "bot_token_hash"]);
function noTruth(value) {
  if (Array.isArray(value)) return value.forEach(noTruth);
  if (value && typeof value === "object") for (const [key, child] of Object.entries(value)) { assert.equal(forbidden.has(key), false, `private field: ${key}`); noTruth(child); }
}
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

test("local remote API: independent engine/viewer capabilities, private state, ACKs, timing and stale heartbeat", { skip: !base, timeout: 45000 }, async () => {
  const origin = new URL(base); assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname));
  const request = async (path, token, body) => {
    const response = await fetch(origin.origin + path, { method: body === undefined ? "GET" : "POST",
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body === undefined ? {} : { "Content-Type": "application/json" }) }, body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  };
  const create = async lane => {
    const result = await request("/api/rooms", null, { mode: "remote", lane }); assert.equal(result.status, 201); noTruth(result.body.state); return result.body;
  };
  const join = (room, role, lane = room.state.remote.lane) => request("/api/rooms/join", null, { code: room.code, role, lane });
  const room = await create("A"), id = room.roomId;
  assert.equal(room.state.remote.viewerConnected, false); assert.equal(room.state.bot.ready, false);
  assert.equal((await join(room, "engine", "B")).body.code, "lane_mismatch");
  const viewer = await join(room, "bot"); assert.equal(viewer.status, 200);
  assert.equal((await join(room, "bot")).body.code, "bot_already_connected");
  const engine = await join(room, "engine"); assert.equal(engine.status, 200); assert.ok(engine.body.token !== viewer.body.token, "Engine and viewer capabilities must differ");
  assert.equal(engine.body.state.remote.engineStage, "connected");
  assert.equal(engine.body.state.remote.engineHeartbeatReceived, false);
  assert.equal(engine.body.state.remote.engineConnected, false);
  assert.equal((await join(room, "engine")).body.code, "engine_already_connected");
  const v = viewer.body.token, e = engine.body.token, h = room.token;
  for (const actor of [v, h]) assert.equal((await request(`/api/rooms/${id}/engine`, actor, { action: "heartbeat", stage: "ready" })).status, 403);
  for (const actor of [v, e]) {
    assert.equal((await request(`/api/rooms/${id}/ready`, actor, { ready: true })).status, 403);
    assert.equal((await request(`/api/rooms/${id}/submit`, actor, { roundId: crypto.randomUUID(), tileIds: [] })).status, 403);
  }
  assert.equal((await request(`/api/rooms/${id}/start`, h, { expectedRevision: engine.body.state.revision })).body.code, "protocol_upgrade_required");
  const ready = await request(`/api/rooms/${id}/engine`, e, { action: "heartbeat", stage: "ready", roundId: null, roundNumber: 0, protocolVersion: 3, requestId: null }); assert.equal(ready.status, 200); assert.equal(ready.body.state.bot.ready, true);
  assert.equal(ready.body.state.remote.engineHeartbeatReceived, true);
  const starts = await Promise.all([0, 1].map(() => request(`/api/rooms/${id}/start`, h, { expectedRevision: ready.body.state.revision })));
  assert.deepEqual(starts.map(item => item.status).sort(), [200, 409]);
  const queued = starts.find(item => item.status === 200).body.state;
  assert.equal(queued.phase, "queued"); assert.equal(queued.roundId, null); assert.equal(queued.roundNumber, 0); assert.equal(queued.startAt, null); assert.deepEqual(queued.tiles, []); assert.equal(queued.topic, null); noTruth(queued);
  const requestId = queued.startRequest.id;
  for (const actor of [h, v]) assert.equal((await request(`/api/rooms/${id}/engine`, actor, { action: "begin", requestId, roundNumber: 0 })).status, 403);
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "heartbeat", stage: "reserved", roundId: null, roundNumber: 0, protocolVersion: 3, requestId })).status, 200);
  const begun = await request(`/api/rooms/${id}/engine`, e, { action: "begin", requestId, roundNumber: 0 }); assert.equal(begun.status, 200);
  const loading = begun.body.state;
  const countdown = await releaseImageBarrier({origin: origin.origin, roomId: id, human: h, viewer: v, engine: e, state: loading});
  const replayBegin = await request(`/api/rooms/${id}/engine`, e, { action: "begin", requestId, roundNumber: 0 }); assert.equal(replayBegin.status, 200); assert.equal(replayBegin.body.state.roundId, countdown.roundId); assert.equal(replayBegin.body.state.startAt, countdown.startAt);
  assert.equal(countdown.phase, "countdown"); assert.deepEqual(countdown.tiles, []); assert.equal(countdown.topic, null);
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId: countdown.roundId, sequence: 1, tileIndex: 0 })).body.code, "not_started");
  await delay(Math.max(0, countdown.startAt - Date.now() + 30));
  const state = await request(`/api/rooms/${id}`, e); assert.equal(state.body.tiles.length, 9); noTruth(state.body);
  const roundId = state.body.roundId;
  const empty = await request(`/api/rooms/${id}/engine`, e, { action: "submit", roundId });
  assert.equal(empty.status, 200); assert.equal(empty.body.correct, false); assert.equal(empty.body.state.startAt, countdown.startAt);
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "heartbeat", stage: "selecting", roundId, roundNumber: 1, protocolVersion: 3, requestId })).status, 200);
  const first = await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 1, tileIndex: 0 }); assert.equal(first.status, 200);
  const tooFast = await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 2, tileIndex: 1 }); assert.equal(tooFast.status, 429);
  const repeated = await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 1, tileIndex: 0 }); assert.equal(repeated.status, 200);
  assert.equal(repeated.body.state.remote.lastSelectionAt, first.body.state.remote.lastSelectionAt);
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 1, tileIndex: 1 })).body.code, "sequence_conflict");
  await delay(Math.max(0, first.body.state.remote.lastSelectionAt + 280 - Date.now()));
  const second = await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 2, tileIndex: 1 }); assert.equal(second.status, 200);
  assert.ok(second.body.state.remote.lastSelectionAt - first.body.state.remote.lastSelectionAt >= 250);
  const [humanView, botView] = await Promise.all([h, v].map(token => request(`/api/rooms/${id}`, token)));
  assert.equal("selectedIndices" in humanView.body.remote, false); assert.deepEqual(botView.body.remote.selectedIndices, [0, 1]); noTruth(humanView.body); noTruth(botView.body);
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId: crypto.randomUUID(), sequence: 3, tileIndex: 2 })).body.code, "round_changed");
  const other = await create("B"); assert.equal((await request(`/api/rooms/${other.roomId}`, e)).status, 401);
  // Opposite join order also leaves the independent viewer role available.
  const otherEngine = await join(other, "engine"); assert.equal(otherEngine.status, 200);
  await request(`/api/rooms/${other.roomId}/engine`, otherEngine.body.token, { action: "heartbeat", stage: "ready", roundId: null, roundNumber: 0, protocolVersion: 3, requestId: null });
  assert.equal((await request(`/api/rooms/${other.roomId}`, other.token)).body.bot.ready, false);
  assert.equal((await join(other, "bot")).status, 200);
  assert.equal((await request(`/api/rooms/${other.roomId}`, other.token)).body.bot.ready, true);
  await delay(15_100);
  const stale = await request(`/api/rooms/${id}`, h); assert.equal(stale.body.remote.engineConnected, false); assert.equal(stale.body.bot.ready, false);
  assert.equal(stale.body.remote.engineHeartbeatReceived, true);
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 3, tileIndex: 2 })).body.code, "engine_not_ready");
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "heartbeat", stage: "selecting", roundId, roundNumber: 1, protocolVersion: 3, requestId })).status, 200);
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 3, tileIndex: 2 })).status, 200);
  await request(`/api/rooms/${id}/engine`, e, { action: "heartbeat", stage: "error", roundId, roundNumber: 1, protocolVersion: 3, requestId });
  assert.equal((await request(`/api/rooms/${id}/engine`, e, { action: "select", roundId, sequence: 4, tileIndex: 3 })).body.code, "engine_not_ready");
});
