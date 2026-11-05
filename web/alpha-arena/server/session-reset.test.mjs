import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { sessionResetCutoff, requireCurrentSession, SESSION_PHOTO_FOR_CURRENT_ROUND } from "./session-reset.mjs";
import { PHOTO_FOR_CURRENT_ROUND } from "./statements.mjs";

const now = 200_000, cutoff = "100000";

test("absent fence preserves existing rooms; a positive safe cutoff includes the exact boundary", () => {
  assert.equal(sessionResetCutoff(undefined, now), 0);
  assert.doesNotThrow(() => requireCurrentSession({ created_at: 0 }, undefined, now));
  assert.equal(sessionResetCutoff(cutoff, now), 100000);
  assert.equal(sessionResetCutoff(String(now), now), now);
  for (const created_at of [0, 99999, 100000]) {
    assert.throws(() => requireCurrentSession({ created_at }, cutoff, now), { code: "room_reset", status: 410 });
  }
  assert.doesNotThrow(() => requireCurrentSession({ created_at: 100001 }, cutoff, now));
});

test("present invalid, zero, imprecise and future configuration fails closed without echoing the binding", () => {
  const inputs = [null, false, true, 100000, "", "0", "00", "0100000", " 100000", "100000 ", "+100000", "-1", "1e5", "100000.0", "NaN", "Infinity", "9007199254740992", "200001", "1\n"];
  for (const raw of inputs) {
    assert.throws(() => sessionResetCutoff(raw, now), error => {
      assert.equal(error.code, "session_reset_unavailable");
      assert.equal(error.status, 503);
      assert.equal(error.message, "운영 세션 초기화 설정을 확인해 주세요.");
      return true;
    });
  }
  for (const invalidClock of [NaN, Infinity, -1, 1.5]) {
    assert.throws(() => sessionResetCutoff(cutoff, invalidClock), { status: 503 });
  }
});

test("revocation applies equally to every preexisting role and does not mutate stored credentials or history", () => {
  for (const role of ["human", "bot", "engine"]) {
    const room = Object.freeze({ created_at: 100000, phase: "active", role,
      human_token_hash: "fixture-human", bot_token_hash: "fixture-viewer", round_id: "fixture-history" });
    assert.throws(() => requireCurrentSession(room, cutoff, now), { code: "room_reset", status: 410 });
    assert.equal(room.round_id, "fixture-history");
    assert.equal(room.bot_token_hash, "fixture-viewer");
  }
  for (const created_at of [undefined, null, NaN, -1, 1.5]) {
    assert.throws(() => requireCurrentSession({ created_at }, cutoff, now), { status: 503 });
  }
});

function fixture(t) {
  const db = new DatabaseSync(":memory:"); db.exec("PRAGMA foreign_keys=ON");
  for (const name of ["0000_living_ma_gnuci.sql", "0001_past_rocket_racer.sql", "0002_mysterious_ravenous.sql", "0003_colorful_cassandra_nova.sql", "0004_amazing_namora.sql"]) {
    db.exec(readFileSync(new URL(`../drizzle/${name}`, import.meta.url), "utf8"));
  }
  const room = db.prepare("INSERT INTO arena_rooms(id,code,human_token_hash,bot_token_hash,phase,round_id,created_at,expires_at) VALUES (?,?, 'fixture-human','fixture-viewer','active',?,?,999999)");
  room.run("old-room", "OLDCODE2", "old-round", 100000);
  room.run("new-room", "NEWCODE2", "new-round", 100001);
  const photo = db.prepare("INSERT INTO arena_photos(id,object_key,mime_type,byte_size,sha256,group_id,metadata_json,created_at) VALUES (?,?,'image/jpeg',1,?,?,'{}',1)");
  photo.run("old-photo", "old-object", "old-sha", "old-group");
  photo.run("new-photo", "new-object", "new-sha", "new-group");
  const round = db.prepare("INSERT INTO arena_rounds(id,room_id,number,theme_id,tiles_json,answer_json,start_at,deadline_at,image_load_id) VALUES (?,?,1,'building_present',?,'[]',150000,290000,'fixture-epoch')");
  round.run("old-round", "old-room", '[{"id":"old-tile","photoId":"old-photo"}]');
  round.run("new-round", "new-room", '[{"id":"new-tile","photoId":"new-photo"}]');
  t.after(() => db.close()); return db;
}

test("joining by an existing code rejects the old connection while a newly created room remains joinable", t => {
  const db = fixture(t);
  const byCode = db.prepare("SELECT * FROM arena_rooms WHERE code = ?");
  assert.throws(() => requireCurrentSession(byCode.get("OLDCODE2"), cutoff, now), { status: 410, code: "room_reset" });
  const fresh = byCode.get("NEWCODE2");
  assert.doesNotThrow(() => requireCurrentSession(fresh, cutoff, now));
  // Stored old hashes and rows remain intact; the generation fence revokes access.
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rooms").get().n, 2);
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rounds").get().n, 2);
  assert.equal(db.prepare("SELECT bot_token_hash FROM arena_rooms WHERE id='old-room'").get().bot_token_hash, "fixture-viewer");
  // Even a naturally expired old room carries the reset reason, rather than
  // accidentally taking the ordinary missing-code path before generation checks.
  db.exec("UPDATE arena_rooms SET expires_at=1 WHERE id='old-room'");
  assert.throws(() => requireCurrentSession(byCode.get("OLDCODE2"), cutoff, now), { status: 410, code: "room_reset" });
});

test("opaque photo route cannot bypass the same fence and its normal visibility rules remain intact", t => {
  const db = fixture(t);
  for (const tile of ["old-tile", "new-tile"]) {
    const existing = db.prepare(PHOTO_FOR_CURRENT_ROUND).get(tile, now, now);
    const guarded = db.prepare(SESSION_PHOTO_FOR_CURRENT_ROUND).get(tile, now, now);
    const { session_created_at, ...normal } = guarded;
    assert.deepEqual(normal, { ...existing });
    assert.doesNotThrow(() => requireCurrentSession({ created_at: session_created_at }, undefined, now));
    if (tile === "old-tile") {
      assert.throws(() => requireCurrentSession({ created_at: session_created_at }, cutoff, now), { status: 410 });
    } else assert.doesNotThrow(() => requireCurrentSession({ created_at: session_created_at }, cutoff, now));
  }
  db.exec("UPDATE arena_rooms SET expires_at=199999 WHERE id='new-room'");
  assert.equal(db.prepare(SESSION_PHOTO_FOR_CURRENT_ROUND).get("new-tile", now, now), undefined);
});
