/** Privileged local integration audit, explicitly separate from the pixel-only ML runner.
 * ALPHA_ADMIN_KEY is supplied only through the process environment and never printed.
 */
import test from "node:test";
import assert from "node:assert/strict";
import { themeTruth } from "./logic.mjs";

const base = process.env.ALPHA_BASE_URL;
const adminKey = process.env.ALPHA_ADMIN_KEY;
const enabled = !!base && !!adminKey;
const privateKeys = new Set(["answer", "answers", "answerTileIds", "answerCount", "labels", "metadata", "photoId", "personCount", "treeCount", "treeAtLeast3", "treeCountMinimum", "groupId", "source", "usageNote", "sha256", "objectKey", "human_token_hash", "bot_token_hash"]);
function noTruthLeak(value) {
  if (Array.isArray(value)) { value.forEach(noTruthLeak); return; }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      assert.equal(privateKeys.has(key), false, `Private evaluator field leaked: ${key}`);
      noTruthLeak(child);
    }
  }
}
function localOnly(address) {
  const url = new URL(address);
  assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(url.hostname), "Integration audit is restricted to localhost");
  return url.origin;
}
async function bytesHash(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((n) => n.toString(16).padStart(2, "0")).join("");
}
test("local D1/R2 API: authorization, common start, atomic starts/submits, truth-free public state", { skip: !enabled, timeout: 45000 }, async () => {
  const origin = localOnly(base);
  const request = async (path, { method = "GET", token, admin = false, body } = {}) => {
    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (admin) headers["x-admin-key"] = adminKey;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetch(origin + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    const payload = await response.json();
    return { status: response.status, body: payload };
  };
  assert.equal((await request("/api/admin/photos")).status, 401);
  const readiness = await request("/api/admin/status", { admin: true });
  assert.equal(readiness.status, 200); assert.equal(readiness.body.ready, true, "Load the reviewed demo bank before this audit");
  const catalog = await request("/api/admin/photos", { admin: true });
  assert.equal(catalog.status, 200); assert.ok(catalog.body.photos.length <= 128, "Use a bounded local fixture bank");
  const truthByHash = new Map();
  // Privileged expected answers are derived here only to verify SERVER grading.
  // The booth bot must never use this endpoint or this map.
  for (let start = 0; start < catalog.body.photos.length; start += 4) {
    await Promise.all(catalog.body.photos.slice(start, start + 4).map(async (photo) => {
      const preview = await fetch(origin + photo.url, { headers: { "x-admin-key": adminKey } });
      assert.equal(preview.status, 200);
      truthByHash.set(await bytesHash(await preview.arrayBuffer()), photo);
    }));
  }
  const created = await request("/api/rooms", { method: "POST", body: {} });
  assert.equal(created.status, 201); const human = created.body.token, id = created.body.roomId;
  assert.match(created.body.code, /^[A-Z2-9]{8}$/); noTruthLeak(created.body.state);
  assert.equal(created.body.state.phase, "lobby"); assert.deepEqual(created.body.state.tiles, []);
  assert.equal((await request(`/api/rooms/${id}`)).status, 401);
  assert.equal((await request(`/api/rooms/${id}`, { token: "A".repeat(43) })).status, 401);
  const joined = await request("/api/rooms/join", { method: "POST", body: { code: created.body.code, role: "bot" } });
  assert.equal(joined.status, 200); const bot = joined.body.token;
  assert.equal((await request("/api/rooms/join", { method: "POST", body: { code: created.body.code, role: "bot" } })).status, 409);
  assert.equal((await request(`/api/rooms/${id}/start`, { method: "POST", token: human, body: {} })).status, 409);
  assert.equal((await request(`/api/rooms/${id}/ready`, { method: "POST", token: bot, body: { ready: true } })).status, 200);
  assert.equal((await request(`/api/rooms/${id}/start`, { method: "POST", token: bot, body: {} })).status, 403);
  const starts = await Promise.all([0, 1].map(() => request(`/api/rooms/${id}/start`, { method: "POST", token: human, body: {} })));
  assert.deepEqual(starts.map((r) => r.status).sort(), [200, 409]);
  const countdown = starts.find((r) => r.status === 200).body.state;
  assert.equal(countdown.phase, "countdown"); assert.equal(countdown.topic, null); assert.deepEqual(countdown.tiles, []);
  assert.equal(countdown.deadlineAt - countdown.startAt, 90000); noTruthLeak(countdown);
  if (Date.now() < countdown.startAt - 50) {
    const early = await request(`/api/rooms/${id}/submit`, { method: "POST", token: human, body: { roundId: countdown.roundId, tileIds: [] } });
    assert.equal(early.status, 409); assert.equal(early.body.code, "not_started");
  }
  await new Promise((resolve) => setTimeout(resolve, Math.max(0, countdown.startAt - Date.now() + 50)));
  const [humanState, botState] = await Promise.all([human, bot].map((token) => request(`/api/rooms/${id}`, { token })));
  assert.equal(humanState.status, 200); assert.equal(botState.status, 200);
  const state = humanState.body;
  assert.equal(state.phase, "playing"); assert.equal(state.tiles.length, 9); noTruthLeak(state); noTruthLeak(botState.body);
  assert.deepEqual(state.tiles, botState.body.tiles); assert.equal(state.startAt, botState.body.startAt);
  const answers = [];
  for (const tile of state.tiles) {
    assert.match(tile.url, /^\/api\/photos\/[0-9a-f-]{36}$/i);
    const image = await fetch(origin + tile.url); assert.equal(image.status, 200);
    assert.match(image.headers.get("content-type"), /^image\/(jpeg|png|webp)$/);
    const truth = truthByHash.get(await bytesHash(await image.arrayBuffer()));
    assert.ok(truth, "Every round pixel must resolve to a reviewed bank record");
    if (themeTruth(truth, state.topic.id) === true) answers.push(tile.id);
  }
  assert.ok(answers.length >= (state.topic.id === "tree_ge3" ? 3 : 2) && answers.length <= 4);
  const foreign = await request(`/api/rooms/${id}/submit`, { method: "POST", token: human, body: { roundId: state.roundId, tileIds: [crypto.randomUUID()] } });
  assert.equal(foreign.status, 400);
  for (let attempt = 0; attempt < 2; attempt++) {
    const wrong = await request(`/api/rooms/${id}/submit`, { method: "POST", token: human, body: { roundId: state.roundId, tileIds: [] } });
    assert.equal(wrong.status, 200); assert.equal(wrong.body.correct, false);
    assert.equal(wrong.body.state.phase, "playing"); assert.equal(wrong.body.state.human.submitted, false);
    assert.equal(wrong.body.state.human.correct, false); assert.equal(wrong.body.state.startAt, state.startAt);
  }
  // Both roles submit the perfect answer simultaneously. Only one transaction
  // can finish; the later one must not overwrite or turn it into a draw.
  const submits = await Promise.all([human, bot].map((token) => request(`/api/rooms/${id}/submit`, { method: "POST", token, body: { roundId: state.roundId, tileIds: answers } })));
  assert.deepEqual(submits.map((r) => r.status).sort(), [200, 409]);
  const accepted = submits.find((r) => r.status === 200); const winner = submits[0].status === 200 ? "human" : "bot";
  assert.equal(accepted.body.correct, true); noTruthLeak(accepted.body.state);
  assert.equal(accepted.body.state.phase, "result"); assert.equal(accepted.body.state.result.winner, winner);
  const finishedAt = accepted.body.state.result.finishedAt; assert.ok(Number.isFinite(finishedAt));
  for (const token of [human, bot]) {
    const ended = await request(`/api/rooms/${id}`, { token });
    assert.equal(ended.body.phase, "result"); assert.equal(ended.body.result.winner, winner);
    assert.equal(ended.body.result.finishedAt, finishedAt);
    assert.equal((await request(`/api/rooms/${id}/submit`, { method: "POST", token, body: { roundId: state.roundId, tileIds: answers } })).status, 409);
  }
  const next = await request(`/api/rooms/${id}/start`, { method: "POST", token: human, body: {} });
  assert.equal(next.status, 409); assert.equal(next.body.code, "already_played");
  assert.equal((await fetch(origin + state.tiles[0].url)).status, 200, "The completed participant may still view the current result");
  const nextParticipant = await request("/api/rooms", { method: "POST", body: {} });
  assert.equal(nextParticipant.status, 201); assert.notEqual(nextParticipant.body.roomId, id);
  assert.equal((await request(`/api/photos/${crypto.randomUUID()}`)).status, 404);
  // Optional second Worker process, configured with the SAME persistent D1/R2,
  // checks that the room is not tied to one isolate's in-memory state.
  if (process.env.ALPHA_SECOND_BASE_URL) {
    const second = localOnly(process.env.ALPHA_SECOND_BASE_URL);
    const response = await fetch(`${second}/api/rooms/${id}`, { headers: { Authorization: `Bearer ${human}` } });
    assert.equal(response.status, 200); assert.equal((await response.json()).roomId, id);
  }
});
