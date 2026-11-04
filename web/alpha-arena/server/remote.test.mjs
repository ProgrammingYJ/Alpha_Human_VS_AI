import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { ENGINE_FRESH_MS, TILE_INTERVAL_MS, REMOTE_HEARTBEAT, REMOTE_SELECT, REMOTE_SUBMIT, REMOTE_NEXT_RESET, REMOTE_NEXT_ROOM, REMOTE_SUBMITTED_STAGE,
  engineConnected, remotePublic, remoteReady, selectionDecision, validateEngineAction, validateLane, validateRoomMode } from "./remote.mjs";
import { GPU_BEGIN_INSERT, GPU_BEGIN_ROOM } from "./gpu-start.mjs";
import { FINISH_IF_CORRECT, submitStatement } from "./statements.mjs";

const hash = "e".repeat(64), now = 10_000;
function fixture(t) {
  const db = new DatabaseSync(":memory:"); db.exec("PRAGMA foreign_keys=ON");
  for (const name of ["0000_living_ma_gnuci.sql", "0001_past_rocket_racer.sql", "0002_mysterious_ravenous.sql", "0003_colorful_cassandra_nova.sql", "0004_amazing_namora.sql"]) db.exec(readFileSync(new URL(`../drizzle/${name}`, import.meta.url), "utf8"));
  db.prepare("INSERT INTO arena_rooms(id,code,human_token_hash,bot_token_hash,created_at,expires_at) VALUES ('room','CODEABCD',?,?,0,999999)").run("h".repeat(64), "v".repeat(64));
  db.prepare("INSERT INTO arena_remote_rooms(room_id,lane,engine_token_hash,engine_seen_at,engine_stage,engine_ready,engine_protocol) VALUES ('room','A',?,?,'ready',1,2)").run(hash, now);
  t.after(() => db.close()); return db;
}
const row = db => db.prepare("SELECT * FROM arena_remote_rooms WHERE room_id='room'").get();
function start(db, at = now, revision = 0, id = "round", number = 1) {
  db.exec("BEGIN IMMEDIATE");
  try {
    const ticket = "10000000-0000-4000-8000-000000000001";
    // Seed a pending request; GPU_QUEUE itself has a separate transaction audit.
    db.prepare("UPDATE arena_rooms SET phase='queued', start_request_id=?,start_requested_at=?,start_expires_at=? WHERE id='room' AND phase='lobby' AND revision=?").run(ticket, at, at + 120000, revision);
    const a = db.prepare(GPU_BEGIN_INSERT).run(id, "room", number, "person_ge3", JSON.stringify(Array.from({ length: 9 }, (_, i) => ({ id: `tile${i}` }))), '["tile0","tile1"]', at, at + 90000, "room", revision, ticket, number - 1, at, at, hash, at - ENGINE_FRESH_MS, at);
    const b = db.prepare(GPU_BEGIN_ROOM).run(id, "room", revision, ticket, number - 1, at, at, hash, at - ENGINE_FRESH_MS, at, id);
    db.exec("COMMIT"); return [Number(a.changes), Number(b.changes)];
  } catch (error) { db.exec("ROLLBACK"); throw error; }
}
function beat(db, stage, at = now, roundId, roundNumber) {
  const room = db.prepare("SELECT * FROM arena_rooms WHERE id='room'").get();
  const observedId = roundId === undefined ? room.round_id : roundId;
  const observedNumber = roundNumber === undefined ? room.round_number : roundNumber;
  return Number(db.prepare(REMOTE_HEARTBEAT).run(at, stage, 2, stage, stage, "room", hash, at, "room", at, observedId, observedNumber, room.start_request_id, stage, stage, 2, stage, stage, at, 2, stage).changes);
}
function next(db, expected = "round", revision = 2, at = now + 1000) {
  db.exec("BEGIN IMMEDIATE");
  try {
    const reset = db.prepare(REMOTE_NEXT_RESET).run("room", "room", expected, revision, at);
    const room = db.prepare(REMOTE_NEXT_ROOM).run("room", expected, revision, at);
    db.exec("COMMIT"); return [Number(reset.changes), Number(room.changes)];
  } catch (error) { db.exec("ROLLBACK"); throw error; }
}
function select(db, sequence, tile, at, roundId = "round", tokenHash = hash) {
  return Number(db.prepare(REMOTE_SELECT).run(tile, sequence, at, "room", tokenHash, at - ENGINE_FRESH_MS, at, sequence - 1, at - TILE_INTERVAL_MS, tile, roundId, at, at, at).changes);
}
function submit(db, snapshot, correct, at) {
  db.exec("BEGIN IMMEDIATE");
  try {
    const result = db.prepare(REMOTE_SUBMIT).run(correct ? at : null, correct ? 1 : 0, at - now, "round", at, at,
      "room", at, hash, at - ENGINE_FRESH_MS, at, snapshot.sequence, snapshot.selected_json);
    db.prepare(FINISH_IF_CORRECT).run("room", "round", "round");
    db.exec("COMMIT"); return Number(result.changes);
  } catch (error) { db.exec("ROLLBACK"); throw error; }
}

test("room mode and optional lane fail closed", () => {
  assert.equal(validateRoomMode({}), null); assert.equal(validateRoomMode({ mode: "remote", lane: "B" }), "B");
  for (const input of [{ mode: "unknown" }, { mode: "remote" }, { lane: "A" }, { mode: "remote", lane: "C" }]) assert.throws(() => validateRoomMode(input));
  assert.doesNotThrow(() => validateLane(undefined, { lane: "A" }));
  assert.throws(() => validateLane("B", { lane: "A" }), { code: "lane_mismatch" });
  assert.throws(() => validateLane("A", null), { code: "lane_mismatch" });
});
test("viewer join, engine readiness and a bounded heartbeat are all required", () => {
  const room = { bot_token_hash: "viewer" }, remote = { engine_token_hash: hash, engine_seen_at: now, engine_ready: 1, engine_stage: "ready" };
  assert.equal(remoteReady(room, remote, now), true);
  assert.equal(remoteReady({ bot_token_hash: null }, remote, now), false);
  assert.equal(remoteReady(room, { ...remote, engine_ready: 0 }, now), false);
  assert.equal(remoteReady(room, { ...remote, engine_stage: "error" }, now), false);
  assert.equal(engineConnected(remote, now + 15000), true); assert.equal(engineConnected(remote, now + 15001), false);
  assert.equal(engineConnected(remote, now - 1), false);
});
test("human projection omits selections and every projection omits engine capability", () => {
  const remote = { lane: "A", engine_token_hash: hash, engine_seen_at: now, engine_stage: "selecting", engine_ready: 1, selected_json: "[2,5]", sequence: 2, last_selection_at: now };
  const human = remotePublic({ bot_token_hash: "viewer" }, remote, "human", now);
  assert.equal("selectedIndices" in human, false); assert.equal("engine_token_hash" in human, false);
  assert.equal(human.engineHeartbeatReceived, true);
  assert.equal(remotePublic({ bot_token_hash: "viewer" }, { ...remote, engine_seen_at: null }, "bot", now).engineHeartbeatReceived, false);
  for (const role of ["bot", "engine"]) assert.deepEqual(remotePublic({ bot_token_hash: "viewer" }, remote, role, now).selectedIndices, [2, 5]);
});
test("selection validates integer bounds, immutable sequence ACKs and minimum time", () => {
  assert.equal(TILE_INTERVAL_MS, 250);
  for (const value of [{ action: "select", sequence: 0, tileIndex: 0 }, { action: "select", sequence: 1, tileIndex: 9 }, { action: "select", sequence: true, tileIndex: 0 }, { action: "heartbeat", stage: "invented" }]) assert.throws(() => validateEngineAction(value));
  const remote = { sequence: 1, selected_json: "[4]", last_selection_at: now };
  assert.equal(selectionDecision(remote, 1, 4, now), "duplicate");
  assert.throws(() => selectionDecision(remote, 1, 3, now), { code: "sequence_conflict" });
  assert.throws(() => selectionDecision(remote, 3, 3, now + 1000), { code: "sequence_conflict" });
  assert.throws(() => selectionDecision(remote, 2, 4, now + 1000), { code: "duplicate_selection" });
  assert.throws(() => selectionDecision(remote, 2, 3, now + 249), { code: "selection_too_fast" });
  assert.equal(selectionDecision(remote, 2, 3, now + 250), "append");
});
test("heartbeats require both round identity and non-negative safe round number", () => {
  for (const value of [{}, { roundId: null }, { roundNumber: 0 }, { roundId: "bad", roundNumber: 0 }, { roundId: null, roundNumber: -1 }, { roundId: null, roundNumber: true }]) {
    assert.throws(() => validateEngineAction({ action: "heartbeat", stage: "ready", ...value }), { code: "invalid_round" });
  }
  assert.doesNotThrow(() => validateEngineAction({ action: "heartbeat", stage: "ready", roundId: null, roundNumber: 0 }));
});
test("SQL remote start has one winner and never creates a stale orphan", t => {
  const db = fixture(t); assert.deepEqual(start(db), [1, 1]);
  assert.deepEqual(start(db, now, 0, "stale"), [0, 0]);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 1);
});
test("SQL fresh-start predicate checks expiry, viewer and error at write time", t => {
  for (const mutation of ["UPDATE arena_remote_rooms SET engine_seen_at=-6000", "UPDATE arena_remote_rooms SET engine_stage='error',engine_ready=0", "UPDATE arena_rooms SET bot_token_hash=NULL"]) {
    const db = fixture(t); db.exec(mutation); assert.deepEqual(start(db), [0, 0]);
    assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 0);
  }
});
test("SQL heartbeat cannot revive error readiness or re-arm a game after its start", t => {
  const db = fixture(t);
  assert.equal(beat(db, "error"), 1); assert.equal(beat(db, "selecting"), 1); assert.equal(row(db).engine_ready, 0);
  assert.equal(beat(db, "ready"), 1); assert.equal(row(db).engine_ready, 1); assert.deepEqual(start(db), [1, 1]);
  assert.equal(beat(db, "ready"), 0); assert.equal(beat(db, "inferencing", now + 1), 1);
  assert.equal(beat(db, "selecting", now), 0); assert.equal(row(db).engine_seen_at, now + 1);
});
test("SQL selection CAS rejects concurrent sequence, duplicate tile and writes below 250ms", t => {
  const db = fixture(t); start(db);
  assert.equal(select(db, 1, 0, now), 1); assert.equal(select(db, 1, 1, now), 0);
  assert.equal(select(db, 2, 1, now + 249), 0); assert.equal(select(db, 2, 0, now + 250), 0);
  assert.equal(select(db, 2, 1, now + 250), 1);
  assert.deepEqual(JSON.parse(row(db).selected_json), [0, 1]); assert.equal(row(db).last_selection_at, now + 250);
});
test("SQL selection rejects stale capabilities, another round and ended games", t => {
  const db = fixture(t); start(db);
  assert.equal(select(db, 1, 0, now, "foreign"), 0); assert.equal(select(db, 1, 0, now, "round", "x".repeat(64)), 0);
  assert.equal(select(db, 1, 0, now + 15001), 0);
  db.exec("UPDATE arena_rooms SET phase='result'"); assert.equal(select(db, 1, 0, now), 0);
  assert.equal(row(db).sequence, 0);
});
test("SQL submit rejects a selection snapshot changed by a concurrent append", t => {
  const db = fixture(t); start(db); select(db, 1, 0, now); const snapshot = row(db);
  select(db, 2, 1, now + 1000); assert.equal(submit(db, snapshot, false, now + 1000), 0);
  assert.equal(db.prepare("SELECT bot_correct FROM arena_rounds WHERE id='round'").get().bot_correct, null);
});
test("SQL remote/human correct submissions resolve to exactly one winner in either order", t => {
  for (const first of ["human", "engine"]) {
    const db = fixture(t); start(db); select(db, 1, 0, now); select(db, 2, 1, now + 1000);
    const human = () => Number(db.prepare(submitStatement("human")).run(now + 1000, 1, 1000, "round", now + 1000, now + 1000, "room", "round").changes);
    if (first === "human") {
      assert.equal(human(), 1); db.prepare(FINISH_IF_CORRECT).run("room", "round", "round"); assert.equal(submit(db, row(db), true, now + 1000), 0);
    } else { assert.equal(submit(db, row(db), true, now + 1000), 1); assert.equal(human(), 0); }
    const saved = db.prepare("SELECT * FROM arena_rounds WHERE id='round'").get();
    assert.equal(saved[first === "human" ? "human_correct" : "bot_correct"], 1);
    assert.equal(saved[first === "human" ? "bot_correct" : "human_correct"], null);
    assert.equal(select(db, 3, 2, now + 2000), 0);
  }
});
test("wrong remote submit preserves the common start and allows future server selections", t => {
  const db = fixture(t); start(db); assert.equal(submit(db, row(db), false, now), 1);
  const round = db.prepare("SELECT * FROM arena_rounds WHERE id='round'").get();
  assert.equal(round.bot_submitted_at, null); assert.equal(round.start_at, now);
  assert.equal(db.prepare("SELECT phase FROM arena_rooms").get().phase, "active");
  assert.equal(select(db, 1, 0, now), 1);
});
test("SQL next atomically clears selections/readiness but preserves room, code and both capabilities", t => {
  const db = fixture(t); start(db); select(db, 1, 0, now); select(db, 2, 1, now + 1000); submit(db, row(db), true, now + 1000);
  const before = db.prepare("SELECT * FROM arena_rooms WHERE id='room'").get();
  assert.deepEqual(next(db), [1, 1]); const reset = db.prepare("SELECT * FROM arena_rooms WHERE id='room'").get();
  for (const key of ["id", "code", "human_token_hash", "bot_token_hash", "round_number"]) assert.equal(reset[key], before[key]);
  assert.equal(reset.phase, "lobby"); assert.equal(reset.round_id, null); assert.equal(reset.revision, before.revision + 1);
  assert.equal(row(db).engine_token_hash, hash); assert.equal(row(db).engine_ready, 0); assert.equal(row(db).engine_stage, "connected");
  assert.equal(row(db).sequence, 0); assert.equal(row(db).last_selection_at, null); assert.deepEqual(JSON.parse(row(db).selected_json), []);
  assert.equal(db.prepare("SELECT bot_correct FROM arena_rounds WHERE id='round'").get().bot_correct, 1);
});
test("SQL duplicate next cannot undo re-ready or a second round in either race order", t => {
  const db = fixture(t); start(db); submit(db, row(db), true, now); assert.deepEqual(next(db), [1, 1]);
  assert.equal(beat(db, "ready", now + 1000, null, 1), 1);
  assert.deepEqual(next(db), [0, 0]); assert.equal(row(db).engine_ready, 1);
  assert.deepEqual(start(db, now + 1000, 3, "second", 2), [1, 1]);
  assert.deepEqual(next(db), [0, 0]); assert.equal(select(db, 1, 4, now + 1000, "second"), 1);
  assert.deepEqual(next(db), [0, 0]); assert.deepEqual(JSON.parse(row(db).selected_json), [4]);
  const room = db.prepare("SELECT * FROM arena_rooms WHERE id='room'").get(); assert.equal(room.round_id, "second"); assert.equal(room.round_number, 2);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 2);
});
test("SQL reset rejects playing, stale round, wrong revision and expired room without partial state", t => {
  const db = fixture(t); start(db); select(db, 1, 0, now);
  assert.deepEqual(next(db, "round", 1), [0, 0]);
  db.exec("UPDATE arena_rooms SET phase='result', revision=2");
  assert.deepEqual(next(db, "foreign"), [0, 0]); assert.deepEqual(next(db, "round", 1), [0, 0]);
  db.exec("UPDATE arena_rooms SET expires_at=10000"); assert.deepEqual(next(db), [0, 0]);
  assert.equal(row(db).sequence, 1); assert.deepEqual(JSON.parse(row(db).selected_json), [0]);
});
test("SQL late result/old lobby heartbeats never re-arm or poison the next participant", t => {
  const db = fixture(t); start(db); submit(db, row(db), true, now);
  assert.equal(beat(db, "submitted", now, "round", 1), 1);
  assert.deepEqual(next(db), [1, 1]);
  for (const stage of ["submitted", "error", "inferencing"]) assert.equal(beat(db, stage, now + 1000, "round", 1), 0);
  assert.equal(beat(db, "ready", now + 1000, null, 0), 0);
  assert.equal(row(db).engine_ready, 0); assert.equal(row(db).engine_stage, "connected");
  assert.equal(beat(db, "ready", now + 1000, null, 1), 1); start(db, now + 1000, 3, "second", 2);
  assert.equal(beat(db, "ready", now + 1000, null, 1), 0); assert.equal(beat(db, "error", now + 1000, "round", 1), 0);
  assert.equal(row(db).engine_ready, 1); assert.equal(beat(db, "inferencing", now + 1000, "second", 2), 1);
});
test("SQL old empty-submit stage and old selection/submit cannot affect a reset or second round", t => {
  const db = fixture(t); start(db); const old = row(db); submit(db, old, true, now); next(db);
  const late = () => Number(db.prepare(REMOTE_SUBMITTED_STAGE).run("room", hash, 0, "[]", "room", "round").changes);
  assert.equal(late(), 0); assert.equal(row(db).engine_stage, "connected");
  beat(db, "ready", now + 1000, null, 1); start(db, now + 1000, 3, "second", 2);
  assert.equal(late(), 0); assert.equal(select(db, 1, 3, now + 1000, "round"), 0); assert.equal(submit(db, old, false, now + 1000), 0);
  assert.equal(row(db).sequence, 0); assert.equal(db.prepare("SELECT bot_correct FROM arena_rounds WHERE id='second'").get().bot_correct, null);
});
