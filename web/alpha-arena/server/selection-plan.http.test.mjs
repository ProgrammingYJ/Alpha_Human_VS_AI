/** Privileged localhost SERVER scheduling/grading audit. Never used by ML.
 * Expected answers exist only in this isolated test process, not the engine.
 */
import test from "node:test";
import { releaseImageBarrier } from "./image-barrier.http-helpers.mjs";
import assert from "node:assert/strict";
import { themeTruth } from "./logic.mjs";

const base = process.env.ALPHA_BASE_URL, adminKey = process.env.ALPHA_ADMIN_KEY;
const delay = ms => new Promise(resolve => setTimeout(resolve, Math.max(0, ms)));
const forbidden = new Set(["answer_json", "answer", "answers", "answerTileIds", "answerCount", "metadata", "photoId", "personCount", "treeCount", "treeAtLeast3", "groupId", "source", "sha256", "objectKey", "engine_token_hash", "human_token_hash", "bot_token_hash", "bot_plan_correct", "bot_plan_indices_json"]);
function noTruth(value) {
  if (Array.isArray(value)) return value.forEach(noTruth);
  if (value && typeof value === "object") for (const [key, child] of Object.entries(value)) { assert.equal(forbidden.has(key), false, `private field: ${key}`); noTruth(child); }
}
const sha = async bytes => [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(n => n.toString(16).padStart(2, "0")).join("");

test("local fixed model plans: immutable ACK, privacy, scheduled winner, human interruption and same-room next", { skip: !base || !adminKey, timeout: 45000 }, async () => {
  const origin = new URL(base); assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname));
  const request = async (path, { token, body, admin = false } = {}) => {
    const response = await fetch(origin.origin + path, { method: body === undefined ? "GET" : "POST",
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body === undefined ? {} : { "Content-Type": "application/json" }), ...(admin ? { "x-admin-key": adminKey } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  };
  const catalog = await request("/api/admin/photos", { admin: true }); assert.equal(catalog.status, 200); assert.ok(catalog.body.photos.length <= 128);
  const truth = new Map();
  for (let i = 0; i < catalog.body.photos.length; i += 4) await Promise.all(catalog.body.photos.slice(i, i + 4).map(async photo => {
    const image = await fetch(origin.origin + photo.url, { headers: { "x-admin-key": adminKey } }); assert.equal(image.status, 200);
    truth.set(await sha(await image.arrayBuffer()), photo);
  }));
  const created = await request("/api/rooms", { body: { mode: "remote", lane: "A" } }); assert.equal(created.status, 201);
  const id = created.body.roomId, human = created.body.token;
  const joined = await Promise.all(["bot", "engine"].map(role => request("/api/rooms/join", { body: { role, lane: "A", code: created.body.code } })));
  assert.ok(joined.every(result => result.status === 200));
  const viewer = joined[0].body.token, engine = joined[1].body.token, path = `/api/rooms/${id}`;
  const action = body => request(path + "/engine", { token: engine, body });
  let requestId = null;
  const start = async number => {
    requestId = null;
    const ready = await action({ action: "heartbeat", stage: "ready", protocolVersion: 3, requestId, roundId: null, roundNumber: number - 1 }); assert.equal(ready.status, 200);
    assert.equal(ready.body.state.remote.selectionPlanSupported, true);
    const queued = await request(path + "/start", { token: human, body: { expectedRevision: ready.body.state.revision } }); assert.equal(queued.status, 200);
    requestId = queued.body.state.startRequest.id;
    const begun = await action({ action: "begin", requestId, roundNumber: number - 1 }); assert.equal(begun.status, 200);
    const countdown = await releaseImageBarrier({origin: origin.origin, roomId: id, human, viewer, engine, state: begun.body.state});
    await delay(countdown.startAt - Date.now() + 25);
    const current = await request(path, { token: viewer }); assert.equal(current.status, 200); assert.equal(current.body.phase, "playing"); return current.body;
  };
  const expectedIndices = async state => {
    const result = [];
    await Promise.all(state.tiles.map(async (tile, index) => {
      const image = await fetch(origin.origin + tile.url); assert.equal(image.status, 200);
      const photo = truth.get(await sha(await image.arrayBuffer())); assert.ok(photo);
      if (themeTruth(photo, state.topic.id) === true) result.push(index);
    }));
    return result.sort((a, b) => a - b);
  };
  const reset = async state => {
    const response = await request(path + "/next", { token: human, body: { roundId: state.roundId } }); assert.equal(response.status, 200);
    assert.equal(response.body.state.phase, "lobby"); assert.deepEqual(response.body.state.remote.selectedIndices, undefined);
    const display = await request(path, { token: viewer }); assert.deepEqual(display.body.remote.selectedIndices, []); assert.equal("selectionPlan" in display.body.remote, false);
  };

  const first = await start(1);
  for (const token of [human, viewer]) assert.equal((await request(path + "/engine", { token, body: { action: "plan", roundId: first.roundId, selectedIndices: [] } })).status, 403);
  assert.equal((await action({ action: "plan", roundId: first.roundId, selectedIndices: [0, 0] })).status, 400);
  const empty = await action({ action: "plan", roundId: first.roundId, selectedIndices: [] }); assert.equal(empty.status, 200);
  assert.deepEqual(Object.keys(empty.body).sort(), ["plan", "serverNow"]); assert.equal(empty.body.plan.intervalMs, 250); assert.equal(empty.body.plan.submitAt, empty.body.plan.startAt); noTruth(empty.body);
  const repeat = await action({ action: "plan", roundId: first.roundId, selectedIndices: [] }); assert.equal(repeat.status, 200); assert.deepEqual(repeat.body.plan, empty.body.plan);
  assert.equal((await action({ action: "plan", roundId: first.roundId, selectedIndices: [0] })).body.code, "plan_conflict");
  assert.equal((await action({ action: "select", roundId: first.roundId, sequence: 1, tileIndex: 0 })).body.code, "plan_active");
  assert.equal((await action({ action: "submit", roundId: first.roundId })).body.code, "plan_active");
  await delay(empty.body.plan.submitAt - Date.now() + 25);
  const emptyAfter = await request(path, { token: viewer }); assert.equal(emptyAfter.body.phase, "playing"); assert.equal(emptyAfter.body.bot.submitted, true); assert.equal(emptyAfter.body.bot.correct, false); noTruth(emptyAfter.body);
  const firstAnswers = await expectedIndices(first);
  const firstWin = await request(path + "/submit", { token: human, body: { roundId: first.roundId, tileIds: firstAnswers.map(index => first.tiles[index].id) } }); assert.equal(firstWin.status, 200); assert.equal(firstWin.body.state.result.winner, "human");
  await reset(first);

  const second = await start(2), answer = await expectedIndices(second);
  const correct = await action({ action: "plan", roundId: second.roundId, selectedIndices: answer }); assert.equal(correct.status, 200);
  const plan = correct.body.plan; assert.equal(plan.submitAt - plan.startAt, (answer.length - 1) * 250);
  const hidden = await request(path, { token: human }); noTruth(hidden.body); assert.equal("selectionPlan" in hidden.body.remote, false); assert.equal("selectedIndices" in hidden.body.remote, false);
  // No state poll is required at the due instant. The human's later submission
  // atomically materializes the earlier scheduled bot result and cannot win.
  await delay(plan.submitAt - Date.now() + 50);
  const lateHuman = await request(path + "/submit", { token: human, body: { roundId: second.roundId, tileIds: answer.map(index => second.tiles[index].id) } }); assert.equal(lateHuman.status, 409);
  const botWin = await request(path, { token: viewer }); assert.equal(botWin.body.result.winner, "bot"); assert.equal(botWin.body.result.finishedAt, plan.submitAt); assert.deepEqual(botWin.body.remote.selectedIndices, answer); noTruth(botWin.body);
  const finalAck = await action({ action: "plan", roundId: second.roundId, selectedIndices: answer }); assert.equal(finalAck.status, 200); assert.deepEqual(finalAck.body.plan, plan);
  await reset(second);

  const third = await start(3), thirdAnswers = await expectedIndices(third);
  const interrupted = await action({ action: "plan", roundId: third.roundId, selectedIndices: thirdAnswers }); assert.equal(interrupted.status, 200);
  const earlyHuman = await request(path + "/submit", { token: human, body: { roundId: third.roundId, tileIds: thirdAnswers.map(index => third.tiles[index].id) } }); assert.equal(earlyHuman.status, 200); assert.equal(earlyHuman.body.state.result.winner, "human");
  await delay(interrupted.body.plan.submitAt - Date.now() + 25);
  const clipped = await request(path, { token: viewer }); assert.equal(clipped.body.result.winner, "human"); assert.ok(clipped.body.remote.selectedIndices.length < thirdAnswers.length); assert.equal(clipped.body.bot.correct, null);
  assert.equal((await action({ action: "plan", roundId: second.roundId, selectedIndices: answer })).body.code, "round_changed");
});
