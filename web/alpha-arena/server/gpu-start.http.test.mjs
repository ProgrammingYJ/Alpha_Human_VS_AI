/** Local-only queue capability/race audit. No administrator answers or models. */
import test from "node:test";
import assert from "node:assert/strict";

const base = process.env.ALPHA_BASE_URL;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
test("local GPU queue: old protocol gate, cancel/requeue isolation, stale/error recovery and begin replay", { skip: !base, timeout: 45000 }, async () => {
  const origin = new URL(base); assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(origin.hostname));
  const request = async (path, token, body) => {
    const response = await fetch(origin.origin + path, { method: body === undefined ? "GET" : "POST", headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    }, body: body === undefined ? undefined : JSON.stringify(body) });
    return { status: response.status, body: await response.json() };
  };
  const create = await request("/api/rooms", null, { mode: "remote", lane: "A" }); assert.equal(create.status, 201);
  const { roomId: id, token: h, code } = create.body;
  const viewer = await request("/api/rooms/join", null, { code, role: "bot", lane: "A" }); assert.equal(viewer.status, 200);
  const engine = await request("/api/rooms/join", null, { code, role: "engine", lane: "A" }); assert.equal(engine.status, 200);
  const e = engine.body.token, v = viewer.body.token;
  const action = body => request(`/api/rooms/${id}/engine`, e, body);
  const view = async () => (await request(`/api/rooms/${id}`, h)).body;
  const start = state => request(`/api/rooms/${id}/start`, h, { expectedRevision: state.revision });
  const cancel = (requestId, actor = h) => request(`/api/rooms/${id}/cancel-start`, actor, { requestId });
  const beat = (stage, state) => action({ action: "heartbeat", stage, protocolVersion: 3,
    requestId: state.startRequest?.id ?? null, roundId: state.roundId, roundNumber: state.roundNumber });

  // Existing engines may finish their no-ticket game, but cannot start v9 work.
  const old = await action({ action: "heartbeat", stage: "ready", roundId: null, roundNumber: 0 }); assert.equal(old.status, 200);
  assert.equal(old.body.state.remote.gpuReservationSupported, false);
  assert.equal((await start(old.body.state)).body.code, "protocol_upgrade_required");
  let ready = await beat("ready", old.body.state); assert.equal(ready.status, 200); assert.equal(ready.body.state.remote.gpuReservationSupported, true);
  assert.equal((await request(`/api/rooms/${id}/start`, h, {})).body.code, "invalid_revision");
  const first = await start(ready.body.state); assert.equal(first.status, 200);
  const pending = first.body.state;
  assert.equal(pending.phase, "queued"); assert.equal(pending.roundNumber, 0); assert.equal(pending.roundId, null);
  assert.equal(pending.startAt, null); assert.equal(pending.deadlineAt, null); assert.equal(pending.topic, null); assert.deepEqual(pending.tiles, []);
  assert.ok(pending.startRequest.expiresAt - pending.startRequest.requestedAt === 120000);
  for (const actor of [e, v]) assert.equal((await cancel(pending.startRequest.id, actor)).status, 403);
  assert.equal((await cancel(crypto.randomUUID())).body.code, "start_request_changed");
  const stopped = await cancel(pending.startRequest.id); assert.equal(stopped.status, 200);
  assert.equal(stopped.body.state.phase, "lobby"); assert.equal(stopped.body.state.startRequest, null); assert.equal(stopped.body.state.lastStartCancellationReason, "human_cancelled"); assert.equal(stopped.body.state.bot.ready, false);
  assert.equal((await action({ action: "begin", requestId: pending.startRequest.id, roundNumber: 0 })).body.code, "start_request_changed");
  assert.equal((await start(ready.body.state)).body.code, "room_changed");

  ready = await beat("ready", stopped.body.state); assert.equal(ready.status, 200);
  const second = await start(ready.body.state); assert.equal(second.status, 200);
  assert.notEqual(second.body.state.startRequest.id, pending.startRequest.id);
  assert.equal((await beat("error", pending)).body.code, "start_request_changed");
  assert.equal((await cancel(pending.startRequest.id)).body.code, "start_request_changed");
  assert.equal((await action({ action: "begin", requestId: pending.startRequest.id, roundNumber: 0 })).body.code, "start_request_changed");
  assert.equal((await view()).phase, "queued");
  const failed = await beat("error", second.body.state); assert.equal(failed.status, 200);
  assert.equal(failed.body.state.phase, "lobby"); assert.equal(failed.body.state.lastStartCancellationReason, "engine_error"); assert.equal(failed.body.state.roundNumber, 0);

  ready = await beat("ready", failed.body.state); assert.equal(ready.status, 200);
  const stalePending = await start(ready.body.state); assert.equal(stalePending.status, 200);
  await delay(15100);
  const disconnected = await view(); assert.equal(disconnected.phase, "lobby"); assert.equal(disconnected.lastStartCancellationReason, "engine_disconnected"); assert.equal(disconnected.roundNumber, 0);
  assert.equal((await beat("waiting_gpu", stalePending.body.state)).body.code, "start_request_changed");
  assert.equal((await action({ action: "begin", requestId: stalePending.body.state.startRequest.id, roundNumber: 0 })).body.code, "start_request_changed");

  ready = await beat("ready", disconnected); assert.equal(ready.status, 200);
  const finalQueue = await start(ready.body.state); assert.equal(finalQueue.status, 200);
  const ticket = finalQueue.body.state.startRequest.id;
  assert.equal((await beat("reserved", finalQueue.body.state)).status, 200);
  const begins = await Promise.all([0, 1].map(() => action({ action: "begin", requestId: ticket, roundNumber: 0 })));
  assert.ok(begins.every(value => value.status === 200));
  assert.equal(begins[0].body.state.roundId, begins[1].body.state.roundId); assert.equal(begins[0].body.state.startAt, begins[1].body.state.startAt);
  assert.equal(begins[0].body.state.phase, "loading"); assert.equal(begins[0].body.state.roundNumber, 1); assert.equal(begins[0].body.state.startRequest.id, ticket);
  const cancelledLoad = await cancel(ticket); assert.equal(cancelledLoad.status, 200); assert.equal(cancelledLoad.body.state.phase, "lobby");
  assert.equal(cancelledLoad.body.state.roundNumber, 1);
  assert.equal((await beat("ready", finalQueue.body.state)).body.code, "round_changed");
});
