import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { publicState } from "./logic.mjs";
import { validateRoomMode } from "./remote.mjs";
import { operationMode, operationRequest, requireOperationLane, OPERATION_ROOM_BY_ID,
  OPERATION_ROOM_BY_CODE, OPERATION_PHOTO_FOR_CURRENT_ROUND } from "./operation-mode.mjs";
import { SESSION_PHOTO_FOR_CURRENT_ROUND } from "./session-reset.mjs";

test("single is the server default and remote creation without a lane chooses only internal A", () => {
  assert.equal(operationMode(undefined), "single");
  assert.equal(operationMode("single"), "single");
  assert.equal(operationMode("dual"), "dual");
  const value = Object.freeze({ mode: "remote" });
  assert.equal(validateRoomMode(operationRequest(value, undefined)), "A");
  assert.deepEqual(value, { mode: "remote" });
  assert.equal(validateRoomMode(operationRequest({}, "single")), null, "legacy remains explicit and separate");
  assert.throws(() => validateRoomMode(operationRequest({ mode: "remote" }, "dual")), { code: "invalid_mode" });
});

test("single rejects B creation/join and existing B reads without changing an A or legacy capability", () => {
  for (const role of [undefined, "bot", "engine"]) {
    assert.throws(() => operationRequest({ mode: "remote", lane: "B", role }, "single"), { code: "lane_disabled", status: 409 });
  }
  for (const lane of ["A", null, undefined]) assert.doesNotThrow(() => requireOperationLane(lane, "single"));
  assert.throws(() => requireOperationLane("B", "single"), { code: "lane_disabled", status: 410 });
  assert.equal(operationRequest({ mode: "remote", lane: "B" }, "dual").lane, "B");
  assert.doesNotThrow(() => requireOperationLane("B", "dual"));
});

test("invalid operation bindings fail closed with a bounded message", () => {
  for (const raw of [null, true, false, 1, "", "A", "single ", "DUAL", "unexpected-private-value"]) {
    assert.throws(() => operationMode(raw), error => {
      assert.equal(error.code, "operation_mode_unavailable");
      assert.equal(error.status, 503);
      assert.equal(error.message, "운영 모드 설정을 확인해 주세요.");
      return true;
    });
  }
});

function fixture(t) {
  const db = new DatabaseSync(":memory:");
  for (const name of ["0000_living_ma_gnuci.sql", "0001_past_rocket_racer.sql", "0002_mysterious_ravenous.sql", "0003_colorful_cassandra_nova.sql", "0004_amazing_namora.sql"]) {
    db.exec(readFileSync(new URL(`../drizzle/${name}`, import.meta.url), "utf8"));
  }
  for (const [room, lane, code] of [["a-room", "A", "AAAACODE"], ["b-room", "B", "BBBBCODE"], ["legacy-room", null, "OLDCODE2"]]) {
    db.prepare("INSERT INTO arena_rooms(id,code,human_token_hash,phase,round_id,created_at,expires_at) VALUES (?,?,'fixture-human','active',?,1,999999)").run(room, code, room + "-round");
    if (lane) db.prepare("INSERT INTO arena_remote_rooms(room_id,lane) VALUES (?,?)").run(room, lane);
    db.prepare("INSERT INTO arena_photos(id,object_key,mime_type,byte_size,sha256,group_id,metadata_json,created_at) VALUES (?,?,'image/jpeg',1,?,?,'{}',1)").run(room + "-photo", room + "-key", room + "-hash", room + "-group");
    db.prepare("INSERT INTO arena_rounds(id,room_id,number,theme_id,tiles_json,answer_json,start_at,deadline_at,image_load_id) VALUES (?,?,1,'building_present',?,'[]',100,999999,'epoch')").run(room + "-round", room, JSON.stringify([{ id: room + "-tile", photoId: room + "-photo" }]));
  }
  t.after(() => db.close()); return db;
}

test("same-query room metadata protects every B role while preserving original A/legacy records", t => {
  const db = fixture(t);
  for (const [id, code, lane] of [["a-room", "AAAACODE", "A"], ["b-room", "BBBBCODE", "B"], ["legacy-room", "OLDCODE2", null]]) {
    const byId = db.prepare(OPERATION_ROOM_BY_ID).get(id);
    assert.deepEqual({ ...db.prepare(OPERATION_ROOM_BY_CODE).get(code) }, { ...byId });
    const { operation_lane, ...normal } = byId;
    assert.equal(operation_lane, lane);
    assert.deepEqual(normal, { ...db.prepare("SELECT * FROM arena_rooms WHERE id=?").get(id) });
    for (const role of ["human", "bot", "engine"]) {
      if (lane === "B") assert.throws(() => requireOperationLane(operation_lane, "single"), { code: "lane_disabled" });
      else assert.doesNotThrow(() => requireOperationLane(operation_lane, "single"));
      assert.equal("operation_lane" in publicState(byId, null, role === "engine" ? "bot" : role, 500), false);
    }
  }
  assert.equal(db.prepare("SELECT COUNT(*) AS n FROM arena_rooms").get().n, 3);
});

test("current-photo reads cannot bypass the B policy and retain original visibility metadata", t => {
  const db = fixture(t);
  for (const [id, lane] of [["a-room", "A"], ["b-room", "B"], ["legacy-room", null]]) {
    const original = db.prepare(SESSION_PHOTO_FOR_CURRENT_ROUND).get(id + "-tile", 500, 500);
    const found = db.prepare(OPERATION_PHOTO_FOR_CURRENT_ROUND).get(id + "-tile", 500, 500);
    const { operation_lane, ...normal } = found;
    assert.deepEqual(normal, { ...original });
    assert.equal(operation_lane, lane);
    if (lane === "B") assert.throws(() => requireOperationLane(operation_lane, "single"), { status: 410 });
    else assert.doesNotThrow(() => requireOperationLane(operation_lane, "single"));
    assert.doesNotThrow(() => requireOperationLane(operation_lane, "dual"));
  }
  db.exec("UPDATE arena_rooms SET expires_at=1 WHERE id='a-room'");
  assert.equal(db.prepare(OPERATION_PHOTO_FOR_CURRENT_ROUND).get("a-room-tile", 500, 500), undefined);
});
