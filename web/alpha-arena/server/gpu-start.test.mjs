import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { ENGINE_FRESH_MS, REMOTE_HEARTBEAT, validateEngineAction } from "./remote.mjs";
import { QUEUE_TTL_MS, GPU_QUEUE, GPU_CANCEL_REMOTE, GPU_CANCEL_ROOM,
  queueCancellationReason, validateStartRequest, validateStartRevision } from "./gpu-start.mjs";
import { IMAGE_BEGIN_INSERT as GPU_BEGIN_INSERT, IMAGE_BEGIN_ROOM as GPU_BEGIN_ROOM, IMAGE_BEGIN_REMOTE as GPU_BEGIN_REMOTE, UNSTARTED_AT, IMAGE_LOADING_MS } from "./image-barrier.mjs";
import { projectStateAfterRemoteRead } from "./state-projection.mjs";

const at = 10_000, hash = "e".repeat(64), ticket = "10000000-0000-4000-8000-000000000001", nextTicket = "10000000-0000-4000-8000-000000000002";
function fixture(t) {
  const db = new DatabaseSync(":memory:"); db.exec("PRAGMA foreign_keys=ON");
  for (const name of ["0000_living_ma_gnuci.sql", "0001_past_rocket_racer.sql", "0002_mysterious_ravenous.sql", "0003_colorful_cassandra_nova.sql", "0004_amazing_namora.sql"]) db.exec(readFileSync(new URL(`../drizzle/${name}`, import.meta.url), "utf8"));
  db.prepare("INSERT INTO arena_rooms(id,code,human_token_hash,bot_token_hash,created_at,expires_at) VALUES ('room','CODEABCD','human','viewer',0,999999)").run();
  db.prepare("INSERT INTO arena_remote_rooms(room_id,lane,engine_token_hash,engine_seen_at,engine_stage,engine_ready,engine_protocol) VALUES ('room','A',?,?,'ready',1,3)").run(hash, at);
  t.after(() => db.close()); return db;
}
const room = db => db.prepare("SELECT * FROM arena_rooms WHERE id='room'").get();
const remote = db => db.prepare("SELECT * FROM arena_remote_rooms WHERE room_id='room'").get();
function transaction(db, work) {
  db.exec("BEGIN IMMEDIATE");
  try { const result = work(); db.exec("COMMIT"); return result; } catch (error) { db.exec("ROLLBACK"); throw error; }
}
function queue(db, id = ticket, revision = room(db).revision, now = at) {
  return Number(db.prepare(GPU_QUEUE).run(id, now, now + QUEUE_TTL_MS, "room", revision, now, now - ENGINE_FRESH_MS, now).changes);
}
function begin(db, id = ticket, expected = room(db), now = at, roundId = "round", token = hash) {
  return transaction(db, () => {
    const a = db.prepare(GPU_BEGIN_INSERT).run(roundId, "room", expected.round_number + 1, "person_ge3", "[]", "[]", UNSTARTED_AT, UNSTARTED_AT, ticket, now + IMAGE_LOADING_MS,
      "room", expected.revision, id, expected.round_number, now, now, token, now - ENGINE_FRESH_MS, now);
    const b = db.prepare(GPU_BEGIN_ROOM).run(roundId, "room", expected.revision, id, expected.round_number, now, now, token, now - ENGINE_FRESH_MS, now, roundId);
    const c = db.prepare(GPU_BEGIN_REMOTE).run("room", token, "room", roundId, id);
    return [Number(a.changes), Number(b.changes), Number(c.changes)];
  });
}
function cancel(db, reason, expected = room(db), observed = remote(db), now = at) {
  const stage = reason === "engine_error" ? "error" : "connected";
  return transaction(db, () => {
    const a = db.prepare(GPU_CANCEL_REMOTE).run(stage, "room", reason, observed.engine_seen_at, observed.engine_stage, "room", expected.start_request_id, expected.revision, now);
    const b = db.prepare(GPU_CANCEL_ROOM).run(reason, "room", expected.start_request_id, expected.revision, now, stage);
    return [Number(a.changes), Number(b.changes)];
  });
}
function beat(db, stage, expected = room(db), requestId = expected.start_request_id, protocol = 3, now = at) {
  return Number(db.prepare(REMOTE_HEARTBEAT).run(now, stage, protocol, stage, stage, "room", hash, now, "room", now,
    expected.round_id, expected.round_number, requestId, stage, stage, protocol, stage, stage, now, protocol, stage).changes);
}

test("additive migration defaults old engines to protocol 1 and preserves existing records", t => {
  const db = new DatabaseSync(":memory:"); t.after(() => db.close());
  for (const name of ["0000_living_ma_gnuci.sql", "0001_past_rocket_racer.sql"]) db.exec(readFileSync(new URL(`../drizzle/${name}`, import.meta.url), "utf8"));
  db.prepare("INSERT INTO arena_rooms(id,code,human_token_hash,created_at,expires_at) VALUES ('old','OLDABCDE','secret',0,999999)").run();
  db.prepare("INSERT INTO arena_remote_rooms(room_id,lane,engine_token_hash,selected_json,sequence) VALUES ('old','B',?,'[2]',1)").run(hash);
  db.exec(readFileSync(new URL("../drizzle/0002_mysterious_ravenous.sql", import.meta.url), "utf8"));
  const old = db.prepare("SELECT * FROM arena_remote_rooms WHERE room_id='old'").get();
  assert.equal(old.engine_protocol, 1); assert.equal(db.prepare("SELECT start_request_id FROM arena_rooms WHERE id='old'").get().start_request_id, null);
  assert.equal(old.engine_token_hash, hash); assert.equal(old.selected_json, "[2]"); assert.equal(old.sequence, 1);
  assert.equal(db.prepare("SELECT human_token_hash FROM arena_rooms WHERE id='old'").get().human_token_hash, "secret");
});

test("queue makes no round, increments revision and discloses no challenge or running timer", async t => {
  const db = fixture(t); assert.equal(queue(db), 1);
  assert.equal(room(db).round_number, 0); assert.equal(room(db).revision, 1); assert.equal(room(db).round_id, null);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 0);
  const state = await projectStateAfterRemoteRead(room(db), null, "human", async () => remote(db), () => at);
  assert.equal(state.phase, "queued"); assert.equal(state.startAt, null); assert.equal(state.deadlineAt, null); assert.equal(state.topic, null); assert.deepEqual(state.tiles, []);
  assert.deepEqual(state.startRequest, { id: ticket, requestedAt: at, expiresAt: at + 120000 });
  assert.equal(state.remote.gpuReservationSupported, true); assert.equal("selectedIndices" in state.remote, false);
});

test("queue rejects protocols 1/2, stale readiness, missing viewer and obsolete revisions", t => {
  for (const mutation of ["UPDATE arena_remote_rooms SET engine_protocol=1", "UPDATE arena_remote_rooms SET engine_protocol=2", "UPDATE arena_remote_rooms SET engine_seen_at=-6000", "UPDATE arena_remote_rooms SET engine_ready=0", "UPDATE arena_rooms SET bot_token_hash=NULL"]) {
    const db = fixture(t); db.exec(mutation); assert.equal(queue(db), 0); assert.equal(room(db).phase, "lobby");
  }
  const db = fixture(t); assert.equal(queue(db, ticket, 99), 0); assert.equal(queue(db), 1); assert.equal(queue(db, nextTicket, 0), 0);
});

test("begin CAS permits one round and preserves the ticket for lost-response retries", t => {
  const db = fixture(t); queue(db); const pending = room(db);
  assert.deepEqual(begin(db, ticket, pending), [1, 1, 1]);
  assert.deepEqual(begin(db, ticket, pending, at, "orphan"), [0, 0, 0]);
  assert.equal(room(db).start_request_id, ticket); assert.equal(room(db).round_number, 1); assert.equal(remote(db).engine_stage, "loading_images");
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 1);
  assert.equal(db.prepare("SELECT start_at FROM arena_rounds").get().start_at, UNSTARTED_AT);
});

test("cancel/begin races never reset a started round or start a cancelled ticket", t => {
  for (const first of ["cancel", "begin"]) {
    const db = fixture(t); queue(db); const pending = room(db), observed = remote(db);
    if (first === "cancel") {
      assert.deepEqual(cancel(db, "human_cancelled", pending, observed), [1, 1]);
      assert.deepEqual(begin(db, ticket, pending), [0, 0, 0]);
      assert.equal(room(db).phase, "lobby"); assert.equal(room(db).last_start_cancel_reason, "human_cancelled"); assert.equal(remote(db).engine_ready, 0);
    } else {
      assert.deepEqual(begin(db, ticket, pending), [1, 1, 1]); assert.deepEqual(cancel(db, "human_cancelled", pending, observed), [0, 0]);
      assert.equal(room(db).phase, "loading"); assert.equal(remote(db).engine_stage, "loading_images");
    }
  }
});

test("cancel/requeue isolates late begin, cancel, start and heartbeat from the old ticket", t => {
  const db = fixture(t); queue(db); const old = room(db), observed = remote(db); cancel(db, "human_cancelled", old, observed);
  assert.equal(beat(db, "ready"), 1); assert.equal(queue(db, nextTicket), 1);
  assert.equal(queue(db, ticket, 0), 0); assert.deepEqual(cancel(db, "human_cancelled", old, observed), [0, 0]);
  assert.deepEqual(begin(db, ticket, old), [0, 0, 0]); assert.equal(beat(db, "waiting_gpu", old, ticket), 0);
  assert.equal(room(db).start_request_id, nextTicket); assert.equal(room(db).round_number, 0);
});

test("automatic cancellation checks stale heartbeat snapshots instead of cancelling newly live work", t => {
  const db = fixture(t); queue(db); const pending = room(db), observed = remote(db);
  assert.equal(queueCancellationReason(pending, observed, at + 15001), "engine_disconnected");
  assert.equal(beat(db, "waiting_gpu", pending, ticket, 3, at + 15001), 1);
  assert.deepEqual(cancel(db, "engine_disconnected", pending, observed, at + 15001), [0, 0]);
  assert.equal(room(db).phase, "queued");
  const expiredRemote = remote(db); assert.deepEqual(cancel(db, "engine_disconnected", pending, expiredRemote, at + 30002), [1, 1]);
  assert.equal(beat(db, "waiting_gpu", pending, ticket, 3, at + 30002), 0); assert.equal(room(db).last_start_cancel_reason, "engine_disconnected");
});

test("queue expiry and error are cancellation reasons and never mint a round", t => {
  for (const reason of ["queue_expired", "engine_error"]) {
    const db = fixture(t); queue(db);
    if (reason === "engine_error") beat(db, "error");
    const pending = room(db), observed = remote(db), end = reason === "queue_expired" ? at + QUEUE_TTL_MS : at;
    assert.equal(queueCancellationReason(pending, observed, end), reason);
    assert.deepEqual(cancel(db, reason, pending, observed, end), [1, 1]); assert.deepEqual(begin(db, ticket, pending, end), [0, 0, 0]);
    assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 0);
  }
});

test("heartbeat ticket and stage CAS separates queued, countdown and lobby", t => {
  const db = fixture(t); queue(db); const pending = room(db);
  assert.equal(beat(db, "ready"), 0); assert.equal(beat(db, "loading_images"), 0); assert.equal(beat(db, "waiting_gpu", pending, null), 0);
  assert.equal(beat(db, "waiting_gpu"), 1); assert.equal(beat(db, "reserved"), 1); begin(db);
  assert.equal(beat(db, "reserved"), 0); assert.equal(beat(db, "loading_images"), 1); assert.equal(beat(db, "error", pending), 0);
});

test("request/protocol validators fail closed while old no-ticket heartbeat remains compatible", t => {
  for (const value of [null, "bad", 1]) assert.throws(() => validateStartRequest(value));
  for (const value of [-1, true, undefined]) assert.throws(() => validateStartRevision(value));
  assert.doesNotThrow(() => validateEngineAction({ action: "heartbeat", stage: "ready", roundId: null, roundNumber: 0 }));
  assert.throws(() => validateEngineAction({ action: "heartbeat", stage: "ready", roundId: null, roundNumber: 0, protocolVersion: 2 }), { code: "invalid_start_request" });
  assert.doesNotThrow(() => validateEngineAction({ action: "begin", requestId: ticket, roundNumber: 0 }));
  const db = fixture(t); assert.equal(beat(db, "ready", room(db), null, 1), 1); assert.equal(remote(db).engine_protocol, 1); assert.equal(queue(db), 0);
});
