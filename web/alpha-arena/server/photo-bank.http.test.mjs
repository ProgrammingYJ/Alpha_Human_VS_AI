/** Privileged LOCAL fixture-bank mutation audit. Run separately from the other
 * HTTP suites, restore the original active set in finally, and never feed this
 * catalog or its hashes to the ML runner. Secrets come only from the environment. */
import test from "node:test";
import assert from "node:assert/strict";
import { bankReadiness } from "./logic.mjs";

const base = process.env.ALPHA_BASE_URL, adminKey = process.env.ALPHA_ADMIN_KEY;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const hash = async bytes => [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(n => n.toString(16).padStart(2, "0")).join("");
const asBank = photos => photos.map(photo => ({ id: photo.id, groupId: photo.groupId, sha256: photo.sha256, metadata: photo }));
const ready = photos => bankReadiness(asBank(photos)).every(topic => topic.ready);

test("local admin bank replacement is authorized, atomic/idempotent and preserves active/loading round pixels", { skip: !base || !adminKey, timeout: 45000 }, async () => {
  const origin = new URL(base);
  assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname), "Bank mutation audit is localhost only");
  const request = async (path, { method = "GET", token, admin = false, body, headers: extra = {} } = {}) => {
    const headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(admin ? { "x-admin-key": adminKey } : {}),
      ...(body === undefined ? {} : { "Content-Type": "application/json" }), ...extra };
    const response = await fetch(origin.origin + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    const text = await response.text(); let parsed;
    try { parsed = JSON.parse(text); } catch { parsed = { code: "non_json_response" }; }
    return { status: response.status, body: parsed };
  };
  const list = async (all = false) => {
    const result = await request(`/api/admin/photos${all ? "?includeInactive=1" : ""}`, { admin: true });
    assert.equal(result.status, 200); return result.body.photos;
  };
  const activate = ids => request("/api/admin/photos", { method: "PUT", admin: true, body: { photoIds: ids } });
  const original = await list(), originalIds = original.map(photo => photo.id);
  assert.ok(original.length <= 128 && ready(original), "Load a bounded reviewed local bank first");
  assert.ok(original.every(photo => photo.active === true && /^[0-9a-f]{64}$/.test(photo.sha256)));
  const assertUnchanged = async () => assert.deepEqual((await list()).map(p => p.id).sort(), [...originalIds].sort());
  assert.equal((await request("/api/admin/photos?includeInactive=1")).status, 401);
  assert.equal((await request("/api/admin/photos", { method: "PUT", body: { photoIds: originalIds } })).status, 401);
  assert.equal((await request("/api/admin/photos", { method: "PUT", admin: true, body: { photoIds: originalIds }, headers: { Origin: "https://foreign.invalid" } })).status, 403);
  assert.equal((await request("/api/admin/photos", { method: "PUT", admin: true, body: { photoIds: originalIds }, headers: { "Content-Type": "text/plain" } })).status, 415);
  assert.equal((await request("/api/admin/photos", { method: "PUT", admin: true, body: { photoIds: originalIds, padding: "x".repeat(8192) } })).status, 413);
  for (const photoIds of [[], ["bad"], [originalIds[0], originalIds[0].toUpperCase()], Array.from({ length: 129 }, () => crypto.randomUUID())]) {
    assert.equal((await activate(photoIds)).status, 400);
  }
  const missing = await activate([originalIds[0], crypto.randomUUID()]);
  assert.equal(missing.status, 404); assert.equal(missing.body.code, "photo_not_found");
  const incomplete = await activate(originalIds.slice(0, 1));
  assert.equal(incomplete.status, 409); assert.equal(incomplete.body.code, "bank_not_ready");
  await assertUnchanged();

  const legacyRound = async () => {
    const created = await request("/api/rooms", { method: "POST", body: {} }); assert.equal(created.status, 201);
    const joined = await request("/api/rooms/join", { method: "POST", body: { role: "bot", code: created.body.code } }); assert.equal(joined.status, 200);
    const path = `/api/rooms/${created.body.roomId}`;
    assert.equal((await request(path + "/ready", { method: "POST", token: joined.body.token, body: { ready: true } })).status, 200);
    const started = await request(path + "/start", { method: "POST", token: created.body.token, body: {} }); assert.equal(started.status, 200);
    await delay(Math.max(0, started.body.state.startAt - Date.now() + 25));
    const state = await request(path, { token: created.body.token }); assert.equal(state.status, 200); assert.equal(state.body.phase, "playing");
    return { path, token: created.body.token, state: state.body, tiles: state.body.tiles };
  };
  const loadingRound = async () => {
    const created = await request("/api/rooms", { method: "POST", body: { mode: "remote", lane: "B" } }); assert.equal(created.status, 201);
    const viewer = await request("/api/rooms/join", { method: "POST", body: { role: "bot", lane: "B", code: created.body.code } }); assert.equal(viewer.status, 200);
    const joined = await request("/api/rooms/join", { method: "POST", body: { role: "engine", lane: "B", code: created.body.code } }); assert.equal(joined.status, 200);
    const path = `/api/rooms/${created.body.roomId}`, token = joined.body.token, state = joined.body.state;
    const beat = await request(path + "/engine", { method: "POST", token, body: { action: "heartbeat", stage: "ready", protocolVersion: 3, roundId: state.roundId, roundNumber: state.roundNumber, requestId: null } }); assert.equal(beat.status, 200);
    const queued = await request(path + "/start", { method: "POST", token: created.body.token, body: { expectedRevision: beat.body.state.revision } }); assert.equal(queued.status, 200);
    const begun = await request(path + "/engine", { method: "POST", token, body: { action: "begin", requestId: queued.body.state.startRequest.id, roundNumber: queued.body.state.roundNumber } }); assert.equal(begun.status, 200);
    assert.equal(begun.body.state.phase, "loading");
    return { path, token: created.body.token, state: begun.body.state, tiles: begun.body.state.preloadTiles };
  };
  const pixel = async tile => {
    const response = await fetch(origin.origin + tile.url); assert.equal(response.status, 200);
    return { tile, sha256: await hash(await response.arrayBuffer()) };
  };
  const [playing, loading] = await Promise.all([legacyRound(), loadingRound()]);
  const snapshots = [];
  for (const round of [playing, loading]) snapshots.push({ round, pixels: await Promise.all(round.tiles.map(pixel)) });
  const byHash = new Map(original.map(photo => [photo.sha256, photo]));
  let selected = [...original]; const retired = [];
  for (const { pixels } of snapshots) {
    // Retire a current tile in EACH state while retaining a complete bank.
    const photo = pixels.map(p => byHash.get(p.sha256)).find(photo => photo && selected.some(p => p.id === photo.id) && ready(selected.filter(p => p.id !== photo.id)));
    assert.ok(photo, "Local bank needs spare independent groups for both current-round retirement checks");
    selected = selected.filter(p => p.id !== photo.id); retired.push(photo);
  }
  try {
    const ids = selected.map(photo => photo.id);
    for (let attempt = 0; attempt < 2; attempt++) {
      const result = await activate(ids); assert.equal(result.status, 200); assert.equal(result.body.photoCount, ids.length);
      assert.equal(result.body.ready, true); assert.ok(result.body.topics.every(topic => topic.ready));
      assert.deepEqual((await list()).map(p => p.id).sort(), [...ids].sort());
    }
    const all = await list(true);
    for (const photo of retired) {
      assert.equal(all.find(p => p.id === photo.id).active, false);
      const response = await fetch(origin.origin + photo.url, { headers: { "x-admin-key": adminKey } });
      assert.equal(response.status, 200); assert.equal(await hash(await response.arrayBuffer()), photo.sha256);
    }
    for (const { round, pixels } of snapshots) {
      const state = await request(round.path, { token: round.token }); assert.equal(state.status, 200);
      assert.equal(state.body.roundId, round.state.roundId); assert.equal(state.body.startAt, round.state.startAt);
      assert.deepEqual(state.body.phase === "loading" ? state.body.preloadTiles : state.body.tiles, round.tiles);
      for (const before of pixels) assert.equal((await pixel(before.tile)).sha256, before.sha256);
    }
    const future = await legacyRound();
    const futureHashes = await Promise.all(future.tiles.map(pixel));
    assert.ok(futureHashes.every(p => !retired.some(photo => photo.sha256 === p.sha256)), "Retired photos must be excluded from future challenges");
  } finally {
    const restored = await activate(originalIds); assert.equal(restored.status, 200, "Restore local fixture bank");
    await assertUnchanged();
  }
});
