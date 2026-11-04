import test from "node:test";
import assert from "node:assert/strict";
import { projectStateAfterRemoteRead } from "./state-projection.mjs";
import { engineConnected } from "./remote.mjs";

const room = { id: "synthetic-room", code: "CODEABCD", phase: "lobby", round_id: null,
  round_number: 0, revision: 1, bot_token_hash: "synthetic-viewer", human_ready: 1, bot_ready: 0 };
const remoteRow = overrides => ({ room_id: room.id, lane: "A", engine_token_hash: "synthetic-engine",
  engine_seen_at: 10_000, engine_stage: "ready", engine_ready: 1,
  selected_json: "[]", sequence: 0, last_selection_at: null, ...overrides });

test("a heartbeat committed during the asynchronous D1 read stays connected in that response", async () => {
  let now = 10_000;
  const capturedBeforeRead = now;
  const readRemote = async id => {
    assert.equal(id, room.id);
    await Promise.resolve(); // A different request commits a newer heartbeat.
    now = 10_050;
    const committed = remoteRow({ engine_seen_at: now });
    assert.equal(engineConnected(committed, capturedBeforeRead), false, "This reproduces the previous timestamp-ordering bug");
    await Promise.resolve();
    now = 10_100;
    return committed;
  };
  const state = await projectStateAfterRemoteRead(room, null, "bot", readRemote, () => now);
  assert.equal(state.serverNow, 10_100);
  assert.equal(state.remote.engineHeartbeatReceived, true);
  assert.equal(state.remote.engineConnected, true);
  assert.equal(state.bot.ready, true);
});

test("a slow read cannot conceal real expiry by reusing the earlier clock", async () => {
  let now = 10_000;
  const state = await projectStateAfterRemoteRead(room, null, "bot", async () => {
    await Promise.resolve(); now = 25_001; return remoteRow();
  }, () => now);
  assert.equal(state.serverNow, 25_001);
  assert.equal(state.remote.engineHeartbeatReceived, true);
  assert.equal(state.remote.engineConnected, false);
  assert.equal(state.bot.ready, false);
});

test("the first-heartbeat flag distinguishes a new claim without granting readiness", async () => {
  const state = await projectStateAfterRemoteRead(room, null, "bot", async () => remoteRow({
    engine_seen_at: null, engine_stage: "connected", engine_ready: 0,
  }), () => 10_000);
  assert.equal(state.remote.engineStage, "connected");
  assert.equal(state.remote.engineHeartbeatReceived, false);
  assert.equal(state.remote.engineConnected, false);
  assert.equal(state.bot.ready, false);
});

test("15-second boundary and genuinely future timestamps retain the existing strict checks", async () => {
  for (const [at, expected] of [[25_000, true], [25_001, false], [9_999, false]]) {
    const state = await projectStateAfterRemoteRead(room, null, "engine", async () => remoteRow(), () => at);
    assert.equal(state.remote.engineHeartbeatReceived, true);
    assert.equal(state.remote.engineConnected, expected);
    assert.equal(state.bot.ready, expected);
  }
});

test("human projection retains heartbeat distinction and hides model selections and capabilities", async () => {
  const state = await projectStateAfterRemoteRead(room, null, "human", async () => remoteRow({ selected_json: "[2,5]", sequence: 2 }), () => 10_001);
  assert.equal(state.remote.engineHeartbeatReceived, true);
  assert.equal("selectedIndices" in state.remote, false);
  assert.equal("engine_token_hash" in state.remote, false);
  assert.equal("engine_seen_at" in state.remote, false);
});

test("legacy projection remains free of remote engine fields", async () => {
  const state = await projectStateAfterRemoteRead({ ...room, bot_ready: 1 }, null, "bot", async () => null, () => 10_123);
  assert.equal(state.serverNow, 10_123); assert.equal(state.bot.ready, true);
  assert.equal("remote" in state, false);
});
