import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { PLAN_BUFFER_MS, PLAN_ACCEPT, PLAN_SETTLE_ROUND, PLAN_HUMAN_SUBMIT, planFor, planPrefix, samePlan, validatePlanIndices } from "./selection-plan.mjs";
import { ENGINE_FRESH_MS, REMOTE_SELECT, REMOTE_SUBMIT, REMOTE_NEXT_RESET, REMOTE_NEXT_ROOM, validateEngineAction } from "./remote.mjs";
import { FINISH_IF_CORRECT } from "./statements.mjs";
import { projectStateAfterRemoteRead } from "./state-projection.mjs";

const at = 10_000, hash = "e".repeat(64), end = at + 90_000;
function fixture(t) {
  const db = new DatabaseSync(":memory:"); db.exec("PRAGMA foreign_keys=ON");
  for (const name of ["0000_living_ma_gnuci.sql", "0001_past_rocket_racer.sql", "0002_mysterious_ravenous.sql", "0003_colorful_cassandra_nova.sql"]) db.exec(readFileSync(new URL(`../drizzle/${name}`, import.meta.url), "utf8"));
  db.prepare("INSERT INTO arena_rooms(id,code,human_token_hash,bot_token_hash,phase,round_id,round_number,revision,created_at,expires_at) VALUES ('room','CODEABCD','human','viewer','active','round',1,1,0,999999)").run();
  db.prepare("INSERT INTO arena_rounds(id,room_id,number,theme_id,tiles_json,answer_json,start_at,deadline_at) VALUES ('round','room',1,'person_ge3',?,'[\"tile0\",\"tile1\"]',?,?)").run(JSON.stringify(Array.from({ length: 9 }, (_, index) => ({ id: `tile${index}` }))), at, end);
  db.prepare("INSERT INTO arena_remote_rooms(room_id,lane,engine_token_hash,engine_seen_at,engine_stage,engine_ready,engine_protocol) VALUES ('room','A',?,?,'inferencing',1,2)").run(hash, at);
  t.after(() => db.close()); return db;
}
const room = db => db.prepare("SELECT * FROM arena_rooms WHERE id='room'").get();
const round = db => db.prepare("SELECT * FROM arena_rounds WHERE id='round'").get();
const remote = db => db.prepare("SELECT * FROM arena_remote_rooms WHERE room_id='room'").get();
function transaction(db, operation) { db.exec("BEGIN IMMEDIATE"); try { const result = operation(); db.exec("COMMIT"); return result; } catch (error) { db.exec("ROLLBACK"); throw error; } }
function accept(db, indices = [0, 1], now = at, capability = hash) {
  const correct = JSON.stringify([...indices].sort()) === "[0,1]", first = now + PLAN_BUFFER_MS, submit = first + Math.max(0, indices.length - 1) * 250;
  return Number(db.prepare(PLAN_ACCEPT).run(JSON.stringify(indices), first, submit, correct ? 1 : 0, "round", now, submit, "room", now, capability, now - ENGINE_FRESH_MS, now).changes);
}
function settle(db, now) {
  return transaction(db, () => {
    const result = db.prepare(PLAN_SETTLE_ROUND).run("round", now, "room", now);
    db.prepare(FINISH_IF_CORRECT).run("room", "round", "round"); return Number(result.changes);
  });
}
function human(db, now, withSettlement = true) {
  return transaction(db, () => {
    if (withSettlement) db.prepare(PLAN_SETTLE_ROUND).run("round", now, "room", now);
    const result = db.prepare(PLAN_HUMAN_SUBMIT).run(now, 1, now - at, "round", now, now, "room", "round", now);
    db.prepare(FINISH_IF_CORRECT).run("room", "round", "round"); return Number(result.changes);
  });
}

test("plan validation accepts empty fixed predictions and rejects fabricated indices/order duplicates", () => {
  for (const indices of [[], [0, 1], [8, 0, 4]]) { assert.deepEqual(validatePlanIndices(indices), indices); assert.doesNotThrow(() => validateEngineAction({ action: "plan", selectedIndices: indices })); }
  for (const indices of [null, {}, [true], [-1], [9], [0, 0], Array.from({ length: 10 }, (_, index) => index)]) {
    assert.throws(() => validatePlanIndices(indices), { code: "invalid_selection" });
    assert.throws(() => validateEngineAction({ action: "plan", selectedIndices: indices }), { code: "invalid_selection" });
  }
});
test("one round stores one immutable ordered plan and the server's private correctness", t => {
  const db = fixture(t); assert.equal(accept(db), 1); const saved = round(db);
  assert.deepEqual(planFor(saved), { roundId: "round", selectedIndices: [0, 1], startAt: 10500, intervalMs: 250, submitAt: 10750 });
  assert.equal(saved.bot_plan_correct, 1); assert.equal(samePlan(saved, [0, 1]), true); assert.equal(samePlan(saved, [1, 0]), false);
  assert.equal(accept(db), 0); assert.equal(accept(db, [1, 0]), 0); assert.equal(round(db).bot_plan_indices_json, "[0,1]");
});
test("accept CAS rejects stale capability, previously touched selections, old attempt and late plans", t => {
  for (const kind of ["capability", "selected", "prior_wrong", "late", "future_heartbeat", "stale", "winner", "not_started"]) {
    const db = fixture(t);
    if (kind === "selected") db.exec("UPDATE arena_remote_rooms SET sequence=1,selected_json='[0]'");
    if (kind === "prior_wrong") db.exec("UPDATE arena_rounds SET bot_correct=0,bot_elapsed_ms=1");
    if (kind === "future_heartbeat") db.prepare("UPDATE arena_remote_rooms SET engine_seen_at=?").run(at + 1);
    if (kind === "stale") db.prepare("UPDATE arena_remote_rooms SET engine_seen_at=?").run(at - ENGINE_FRESH_MS - 1);
    if (kind === "winner") db.exec("UPDATE arena_rounds SET human_correct=1");
    if (kind === "late") db.prepare("UPDATE arena_remote_rooms SET engine_seen_at=?").run(end - 500);
    assert.equal(accept(db, [0, 1], kind === "late" ? end - 500 : kind === "not_started" ? at - 1 : at, kind === "capability" ? "wrong" : hash), 0, kind);
  }
});
test("plan prefixes use exact250ms boundaries and clip remaining selections after a human win", () => {
  const plan = { roundId: "round", selectedIndices: [7, 2, 5], startAt: 1000, intervalMs: 250, submitAt: 1500 };
  for (const [time, expected] of [[999, []], [1000, [7]], [1249, [7]], [1250, [7, 2]], [1500, [7, 2, 5]], [9999, [7, 2, 5]]]) assert.deepEqual(planPrefix(plan, time), expected);
  assert.deepEqual(planPrefix(plan, 9999, 1249), [7]);
  assert.deepEqual(planPrefix(plan, 9999, 900), []);
  assert.deepEqual(planPrefix({ ...plan, selectedIndices: [] }, 9999), []);
});
test("future model plans/correctness never enter human JSON; bot receives only model schedule", async t => {
  const db = fixture(t); accept(db);
  const h = await projectStateAfterRemoteRead(room(db), round(db), "human", async () => remote(db), () => 10500);
  assert.equal(h.remote.selectionPlanSupported, true); assert.equal("selectedIndices" in h.remote, false); assert.equal("selectionPlan" in h.remote, false);
  for (const privateKey of ["bot_plan_correct", "bot_plan_indices_json", "answer_json"]) assert.equal(JSON.stringify(h).includes(privateKey), false);
  const b = await projectStateAfterRemoteRead(room(db), round(db), "bot", async () => remote(db), () => 10500);
  assert.deepEqual(b.remote.selectedIndices, [0]); assert.deepEqual(b.remote.selectionPlan.selectedIndices, [0, 1]); assert.equal("correct" in b.remote.selectionPlan, false);
  const engine = await projectStateAfterRemoteRead(room(db), round(db), "engine", async () => remote(db), () => 10500);
  assert.equal("selectionPlan" in engine.remote, false);
});
test("correct plans settle only at due time using scheduled timestamp, not a later poll", t => {
  const db = fixture(t); accept(db);
  assert.equal(settle(db, 10749), 0); assert.equal(round(db).bot_correct, null);
  assert.equal(settle(db, 10750), 1); assert.equal(round(db).bot_submitted_at, 10750); assert.equal(round(db).bot_elapsed_ms, 750); assert.equal(room(db).phase, "result");
  assert.equal(settle(db, 20000), 0); assert.equal(round(db).bot_submitted_at, 10750);
});
test("a human correct submission just before plan completion wins and cancels remaining scheduled input", t => {
  const db = fixture(t); accept(db); assert.equal(human(db, 10749), 1); assert.equal(settle(db, 10750), 0);
  assert.equal(round(db).human_correct, 1); assert.equal(round(db).bot_correct, null); assert.equal(room(db).phase, "result");
});
test("a human request at/after scheduled correct completion cannot beat the plan in either settlement order", t => {
  for (const time of [10750, 10751, 20000]) for (const prePoll of [false, true]) {
    const db = fixture(t); accept(db); if (prePoll) settle(db, time);
    assert.equal(human(db, time), 0); assert.equal(round(db).bot_correct, 1); assert.equal(round(db).human_correct, null); assert.equal(round(db).bot_submitted_at, 10750);
  }
});
test("the human SQL itself rejects an already-due correct plan even without a prior settlement poll", t => {
  const db = fixture(t); accept(db); assert.equal(human(db, 10750, false), 0); assert.equal(round(db).human_correct, null);
  assert.equal(settle(db, 10751), 1); assert.equal(round(db).bot_correct, 1);
});
test("an accepted plan continues after engine disconnection; a wrong zero-selection plan stays one attempt", t => {
  const db = fixture(t); accept(db, []); db.exec("UPDATE arena_remote_rooms SET engine_ready=0,engine_seen_at=NULL,engine_stage='error'");
  assert.equal(settle(db, 10500), 1); assert.equal(round(db).bot_correct, 0); assert.equal(round(db).bot_submitted_at, 10500); assert.equal(room(db).phase, "active");
  assert.equal(settle(db, 11000), 0); assert.equal(accept(db, [0, 1], 11000), 0); assert.equal(human(db, 11000), 1);
});
test("a plan cannot win at or beyond the deadline, including defensive persisted invalid data", t => {
  const db = fixture(t); accept(db); db.prepare("UPDATE arena_rounds SET bot_plan_submit_at=?").run(end);
  assert.equal(settle(db, end + 1), 0); assert.equal(human(db, end + 1), 0); assert.equal(round(db).bot_correct, null);
});
test("old per-tile SELECT and SUBMIT CAS cannot race into an accepted plan", t => {
  const db = fixture(t); accept(db);
  assert.equal(Number(db.prepare(REMOTE_SELECT).run(0, 1, at, "room", hash, at - ENGINE_FRESH_MS, at, 0, at - 250, 0, "round", at, at, at).changes), 0);
  assert.equal(Number(db.prepare(REMOTE_SUBMIT).run(at, 1, 0, "round", at, at, "room", at, hash, at - ENGINE_FRESH_MS, at, 0, "[]").changes), 0);
});
test("next participant preserves the old plan as history and new rounds start with no plan", t => {
  const db = fixture(t); accept(db); settle(db, 10750); const saved = room(db);
  transaction(db, () => { db.prepare(REMOTE_NEXT_RESET).run("room", "room", "round", saved.revision, 11000); db.prepare(REMOTE_NEXT_ROOM).run("room", "round", saved.revision, 11000); });
  assert.equal(room(db).phase, "lobby"); assert.equal(room(db).round_id, null); assert.equal(round(db).bot_plan_indices_json, "[0,1]");
  db.prepare("INSERT INTO arena_rounds(id,room_id,number,theme_id,tiles_json,answer_json,start_at,deadline_at) VALUES ('new','room',2,'person_ge3','[]','[]',11000,101000)").run();
  assert.equal(db.prepare("SELECT bot_plan_indices_json FROM arena_rounds WHERE id='new'").get().bot_plan_indices_json, null);
});
