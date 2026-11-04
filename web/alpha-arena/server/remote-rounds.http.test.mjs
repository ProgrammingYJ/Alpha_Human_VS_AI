/** Privileged localhost SERVER audit, never an ML engine or answer source. */
import test from "node:test";
import { releaseImageBarrier } from "./image-barrier.http-helpers.mjs";
import assert from "node:assert/strict";
import { themeTruth } from "./logic.mjs";

const base = process.env.ALPHA_BASE_URL, adminKey = process.env.ALPHA_ADMIN_KEY;
const enabled = !!base && !!adminKey;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const privateKeys = new Set(["answer_json", "answer", "answers", "answerTileIds", "answerCount", "metadata", "photoId", "personCount", "treeCount", "treeAtLeast3", "groupId", "source", "sha256", "objectKey", "engine_token_hash", "human_token_hash", "bot_token_hash"]);
function noTruth(value) {
  if (Array.isArray(value)) return value.forEach(noTruth);
  if (value && typeof value === "object") for (const [key, child] of Object.entries(value)) { assert.equal(privateKeys.has(key), false, `private field: ${key}`); noTruth(child); }
}
async function sha(bytes) { return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(n => n.toString(16).padStart(2, "0")).join(""); }

test("local remote persistent room: two rounds, one pairing, atomic next, empty reset and old request rejection", { skip: !enabled, timeout: 45000 }, async () => {
  const url = new URL(base); assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(url.hostname));
  const request = async (path, { token, body, admin = false } = {}) => {
    const response = await fetch(url.origin + path, { method: body === undefined ? "GET" : "POST",
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body === undefined ? {} : { "Content-Type": "application/json" }), ...(admin ? { "x-admin-key": adminKey } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  };
  const catalog = await request("/api/admin/photos", { admin: true }); assert.equal(catalog.status, 200); assert.ok(catalog.body.photos.length <= 128);
  const truth = new Map();
  // Only this administrator QA evaluator derives expected SERVER grading.
  for (let i = 0; i < catalog.body.photos.length; i += 4) await Promise.all(catalog.body.photos.slice(i, i + 4).map(async photo => {
    const image = await fetch(url.origin + photo.url, { headers: { "x-admin-key": adminKey } }); assert.equal(image.status, 200);
    truth.set(await sha(await image.arrayBuffer()), photo);
  }));
  const created = await request("/api/rooms", { body: { mode: "remote", lane: "A" } }); assert.equal(created.status, 201);
  const { roomId: id, code, token: human } = created.body;
  const joined = await Promise.all(["bot", "engine"].map(role => request("/api/rooms/join", { body: { role, code, lane: "A" } })));
  assert.ok(joined.every(value => value.status === 200));
  const viewer = joined[0].body.token, engine = joined[1].body.token;
  let requestId = null;
  const action = body => request(`/api/rooms/${id}/engine`, { token: engine, body });
  const beat = (stage, roundId, roundNumber) => action({ action: "heartbeat", stage, roundId, roundNumber, protocolVersion: 3, requestId });
  const next = roundId => request(`/api/rooms/${id}/next`, { token: human, body: { roundId } });
  for (const token of [viewer, engine]) assert.equal((await request(`/api/rooms/${id}/next`, { token, body: { roundId: crypto.randomUUID() } })).status, 403);
  assert.equal((await action({ action: "heartbeat", stage: "ready" })).body.code, "invalid_round");
  const initialReady = await beat("ready", null, 0); assert.equal(initialReady.status, 200);
  const first = await request(`/api/rooms/${id}/start`, { token: human, body: { expectedRevision: initialReady.body.state.revision } }); assert.equal(first.status, 200);
  assert.equal(first.body.state.phase, "queued"); assert.equal(first.body.state.roundNumber, 0); assert.equal(first.body.state.roundId, null); assert.equal(first.body.state.startAt, null); assert.deepEqual(first.body.state.tiles, []);
  requestId = first.body.state.startRequest.id;
  const firstBegin = await action({ action: "begin", requestId, roundNumber: 0 }); assert.equal(firstBegin.status, 200);
  const firstCountdown = await releaseImageBarrier({origin: url.origin, roomId: id, human, viewer, engine, state: firstBegin.body.state});
  assert.equal(firstCountdown.roundNumber, 1); assert.ok(Number.isInteger(firstCountdown.revision));
  assert.equal((await next(firstCountdown.roundId)).body.code, "round_in_progress");
  await delay(Math.max(0, firstCountdown.startAt - Date.now() + 30));
  const answersFor = async state => {
    const answers = [];
    for (const tile of state.tiles) {
      const image = await fetch(url.origin + tile.url); assert.equal(image.status, 200);
      const photo = truth.get(await sha(await image.arrayBuffer())); assert.ok(photo);
      if (themeTruth(photo, state.topic.id) === true) answers.push(tile.id);
    }
    return answers;
  };
  const firstState = (await request(`/api/rooms/${id}`, { token: human })).body; noTruth(firstState);
  assert.equal((await beat("inferencing", firstState.roundId, 1)).status, 200);
  assert.equal((await action({ action: "select", roundId: firstState.roundId, sequence: 1, tileIndex: 0 })).status, 200);
  const win1 = await request(`/api/rooms/${id}/submit`, { token: human, body: { roundId: firstState.roundId, tileIds: await answersFor(firstState) } });
  assert.equal(win1.status, 200); assert.equal(win1.body.correct, true); assert.equal(win1.body.state.phase, "result");
  assert.equal((await beat("submitted", firstState.roundId, 1)).status, 200);
  const endedSelectionBeat = await beat("selecting", firstState.roundId, 1);
  assert.equal(endedSelectionBeat.status, 409); assert.equal(endedSelectionBeat.body.code, "round_ended");
  const resets = await Promise.all([next(firstState.roundId), next(firstState.roundId), beat("submitted", firstState.roundId, 1)]);
  assert.equal(resets[0].status, 200); assert.equal(resets[1].status, 200); assert.ok([200, 409].includes(resets[2].status));
  const lobby = (await request(`/api/rooms/${id}`, { token: viewer })).body;
  assert.equal(lobby.roomId, id); assert.ok(lobby.code === code, "Pairing code must remain unchanged"); assert.equal(lobby.phase, "lobby"); assert.equal(lobby.roundId, null); assert.equal(lobby.roundNumber, 1);
  assert.deepEqual(lobby.tiles, []); assert.equal(lobby.topic, null); assert.deepEqual(lobby.remote.selectedIndices, []); assert.equal(lobby.remote.sequence, 0); assert.equal(lobby.remote.lastSelectionAt, null); assert.equal(lobby.bot.ready, false); noTruth(lobby);
  assert.equal((await fetch(url.origin + firstState.tiles[0].url)).status, 404);
  for (const stage of ["submitted", "error", "inferencing"]) assert.equal((await beat(stage, firstState.roundId, 1)).body.code, "round_changed");
  assert.equal((await beat("ready", null, 0)).body.code, "round_changed");
  assert.equal((await action({ action: "select", roundId: firstState.roundId, sequence: 2, tileIndex: 1 })).body.code, "round_changed");
  assert.equal((await action({ action: "submit", roundId: firstState.roundId })).body.code, "round_changed");
  requestId = null;
  const rearmed = await beat("ready", null, 1); assert.equal(rearmed.status, 200); assert.equal(rearmed.body.state.bot.ready, true);
  const duplicate = await next(firstState.roundId); assert.equal(duplicate.status, 200); assert.equal(duplicate.body.state.bot.ready, true); assert.equal(duplicate.body.state.revision, rearmed.body.state.revision);
  // A late old next may ACK the lobby or observe the new countdown. It must
  // never reset the concurrently started second participant.
  const race = await Promise.all([request(`/api/rooms/${id}/start`, { token: human, body: { expectedRevision: rearmed.body.state.revision } }), next(firstState.roundId)]);
  assert.equal(race[0].status, 200); assert.ok([200, 409].includes(race[1].status));
  assert.equal(race[0].body.state.phase, "queued"); assert.equal(race[0].body.state.roundNumber, 1);
  requestId = race[0].body.state.startRequest.id;
  const secondBegin = await action({ action: "begin", requestId, roundNumber: 1 }); assert.equal(secondBegin.status, 200);
  const second = await releaseImageBarrier({origin: url.origin, roomId: id, human, viewer, engine, state: secondBegin.body.state});
  assert.equal(second.roundNumber, 2); assert.notEqual(second.roundId, firstState.roundId); assert.ok(second.code === code, "Pairing code must remain unchanged"); assert.equal(second.phase, "countdown");
  assert.equal((await next(firstState.roundId)).body.code, "round_changed");
  assert.equal((await beat("ready", null, 1)).body.code, "round_changed");
  assert.equal((await beat("error", firstState.roundId, 1)).body.code, "round_changed");
  await delay(Math.max(0, second.startAt - Date.now() + 30));
  assert.equal((await beat("inferencing", second.roundId, 2)).status, 200);
  const selected2 = await action({ action: "select", roundId: second.roundId, sequence: 1, tileIndex: 3 }); assert.equal(selected2.status, 200); assert.deepEqual(selected2.body.state.remote.selectedIndices, [3]);
  const human2 = (await request(`/api/rooms/${id}`, { token: human })).body;
  assert.equal("selectedIndices" in human2.remote, false); noTruth(human2);
  const win2 = await request(`/api/rooms/${id}/submit`, { token: human, body: { roundId: second.roundId, tileIds: await answersFor(human2) } });
  assert.equal(win2.status, 200); assert.equal(win2.body.state.result.winner, "human"); assert.equal(win2.body.state.roundNumber, 2);
  assert.equal((await next(firstState.roundId)).body.code, "round_changed");
  for (const token of [human, viewer, engine]) {
    const final = await request(`/api/rooms/${id}`, { token }); assert.equal(final.status, 200); assert.equal(final.body.phase, "result"); assert.ok(final.body.code === code, "Pairing code must remain unchanged"); noTruth(final.body);
  }
  const legacy = await request("/api/rooms", { body: {} }); assert.equal(legacy.status, 201);
  assert.equal((await request(`/api/rooms/${legacy.body.roomId}/next`, { token: legacy.body.token, body: { roundId: firstState.roundId } })).body.code, "invalid_mode");
});
