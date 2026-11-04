import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { START_ROUND_INSERT, START_ROOM_UPDATE, FINISH_IF_CORRECT, PHOTO_FOR_CURRENT_ROUND, submitStatement } from "./statements.mjs";

function fixture(t) {
  const dir = mkdtempSync(join(tmpdir(), "alpha-arena-sql-")); const path = join(dir, "arena.sqlite");
  const db = new DatabaseSync(path);
  db.exec("PRAGMA foreign_keys=ON");
  db.exec(readFileSync(new URL("../drizzle/0000_living_ma_gnuci.sql", import.meta.url), "utf8"));
  db.exec(readFileSync(new URL("../drizzle/0004_amazing_namora.sql", import.meta.url), "utf8"));
  db.prepare("INSERT INTO arena_rooms (id,code,human_token_hash,bot_token_hash,bot_ready,created_at,expires_at) VALUES ('room','CODEABCD',?, ?,1,0,999999)").run("a".repeat(64), "b".repeat(64));
  t.after(() => { try { db.close(); } catch {} rmSync(dir, { recursive: true, force: true }); });
  return { db, path };
}
function start(db, id, revision, number = 1) {
  db.exec("BEGIN IMMEDIATE");
  try {
    const a = db.prepare(START_ROUND_INSERT).run(id, "room", number, "person_ge3", "[]", "[]", 2000, 92000, "room", revision);
    const b = db.prepare(START_ROOM_UPDATE).run(id, "room", revision, id);
    db.exec("COMMIT"); return [Number(a.changes), Number(b.changes)];
  } catch (error) { db.exec("ROLLBACK"); throw error; }
}
function submit(db, role, roundId, correct, time = 3000) {
  db.exec("BEGIN IMMEDIATE");
  try {
    const a = db.prepare(submitStatement(role)).run(correct ? time : null, correct ? 1 : 0, time - 2000, roundId, time, time, "room", roundId);
    db.prepare(FINISH_IF_CORRECT).run("room", roundId, roundId);
    db.exec("COMMIT"); return Number(a.changes);
  } catch (error) { db.exec("ROLLBACK"); throw error; }
}
test("two starts that read the same revision cannot create two active rounds", (t) => {
  const { db } = fixture(t);
  assert.deepEqual(start(db, "round-first", 0), [1, 1]);
  assert.deepEqual(start(db, "round-stale", 0), [0, 0]);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 1);
  assert.equal(db.prepare("SELECT round_id FROM arena_rooms").get().round_id, "round-first");
});
test("a ready-change racing start invalidates the start without orphan records", (t) => {
  const { db } = fixture(t);
  db.prepare("UPDATE arena_rooms SET bot_ready=0, revision=revision+1 WHERE id='room'").run();
  assert.deepEqual(start(db, "stale", 0), [0, 0]);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 0);
});
test("wrong answers allow retry without resetting the start; first correct locks the room", (t) => {
  const { db } = fixture(t); start(db, "round", 0);
  assert.equal(submit(db, "human", "round", false, 2500), 1);
  assert.equal(submit(db, "human", "round", false, 3000), 1);
  const wrong = db.prepare("SELECT * FROM arena_rounds WHERE id='round'").get();
  assert.equal(wrong.human_correct, 0); assert.equal(wrong.human_submitted_at, null); assert.equal(wrong.start_at, 2000);
  assert.equal(db.prepare("SELECT phase FROM arena_rooms").get().phase, "active");
  assert.equal(submit(db, "human", "round", true, 3500), 1);
  assert.equal(db.prepare("SELECT phase FROM arena_rooms").get().phase, "result");
  assert.equal(submit(db, "bot", "round", true, 3600), 0);
  assert.equal(submit(db, "human", "round", false, 4000), 0);
  const final = db.prepare("SELECT * FROM arena_rounds WHERE id='round'").get();
  assert.equal(final.human_correct, 1); assert.equal(final.human_submitted_at, 3500);
  assert.equal(final.bot_correct, null); assert.equal(final.human_elapsed_ms, 1500);
});
test("pre-start, timed-out and stale-round submissions fail and a participant cannot restart", (t) => {
  const { db } = fixture(t); start(db, "round", 0);
  assert.equal(submit(db, "human", "round", true, 1999), 0);
  assert.equal(submit(db, "human", "round", true, 92000), 0);
  db.prepare("UPDATE arena_rooms SET phase='result',revision=revision+1 WHERE id='room'").run();
  assert.deepEqual(start(db, "new-round", 2, 2), [0, 0]);
  assert.equal(submit(db, "human", "round", true, 3000), 0);
  assert.equal(db.prepare("SELECT human_submitted_at FROM arena_rounds WHERE id='round'").get().human_submitted_at, null);
});
test("racing correct answers have exactly one winner in either commit order", (t) => {
  for (const roles of [["human", "bot"], ["bot", "human"]]) {
    const { db } = fixture(t); start(db, "round", 0);
    assert.equal(submit(db, roles[0], "round", true, 3000), 1);
    assert.equal(submit(db, roles[1], "round", true, 3000), 0);
    const saved = db.prepare("SELECT * FROM arena_rounds WHERE id='round'").get();
    assert.equal(saved[`${roles[0]}_correct`], 1); assert.equal(saved[`${roles[1]}_correct`], null);
    assert.equal(db.prepare("SELECT phase FROM arena_rooms").get().phase, "result");
  }
});
test("rooms, hashed capabilities and active round survive closing the database", (t) => {
  const { db, path } = fixture(t); start(db, "round", 0); db.close();
  const reopened = new DatabaseSync(path);
  try {
    const saved = reopened.prepare("SELECT * FROM arena_rooms WHERE id='room'").get();
    assert.equal(saved.human_token_hash, "a".repeat(64));
    assert.equal(saved.round_id, "round");
    assert.equal(reopened.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 1);
  } finally { reopened.close(); }
});

test("pixel URLs expire with the room or next round; retiring a photo preserves the current round", (t) => {
  const { db } = fixture(t); start(db, "first", 0);
  db.prepare("INSERT INTO arena_photos(id,object_key,mime_type,byte_size,sha256,group_id,metadata_json,created_at,active) VALUES ('photo','key','image/jpeg',1,?,'group','{}',0,1)").run("c".repeat(64));
  db.prepare("UPDATE arena_rounds SET tiles_json = ? WHERE id='first'").run('[{"id":"tile-first","photoId":"photo"}]');
  const read = (id, time) => db.prepare(PHOTO_FOR_CURRENT_ROUND).get(id, time, time);
  assert.equal(read("tile-first", 1999), undefined);
  assert.equal(read("tile-first", 2000).id, "photo");
  db.prepare("UPDATE arena_photos SET active=0 WHERE id='photo'").run();
  assert.equal(read("tile-first", 2000).id, "photo");
  db.prepare("UPDATE arena_rooms SET phase='result',revision=revision+1 WHERE id='room'").run();
  assert.equal(read("tile-first", 3000).id, "photo");
  // Defensive URL lifetime check for legacy/migrated rows. The public start
  // endpoint no longer permits a second round for the same participant.
  db.prepare("INSERT INTO arena_rounds(id,room_id,number,theme_id,tiles_json,answer_json,start_at,deadline_at) VALUES ('second','room',2,'person_ge3','[]','[]',2000,92000)").run();
  db.prepare("UPDATE arena_rooms SET round_id='second' WHERE id='room'").run();
  db.prepare("UPDATE arena_rounds SET tiles_json = ? WHERE id='second'").run('[{"id":"tile-second","photoId":"photo"}]');
  assert.equal(read("tile-first", 3000), undefined);
  assert.equal(read("tile-second", 3000).id, "photo");
  db.prepare("UPDATE arena_rooms SET expires_at=3000 WHERE id='room'").run();
  assert.equal(read("tile-second", 3000), undefined);
});
