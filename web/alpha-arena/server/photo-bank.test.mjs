import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { ACTIVATE_PHOTO_BANK, SELECT_PHOTO_BANK, validateActivePhotoBank, validateActivePhotoIds } from "./photo-bank.mjs";
import { THEMES, makeChallenge } from "./logic.mjs";

const id = i => `00000000-0000-4000-8000-${i.toString(16).padStart(12, "0")}`;
const photos = count => Array.from({ length: count }, (_, i) => ({ id: id(i), groupId: `group-${i}`, sha256: `hash-${i}`,
  metadata: { personCount: i < 4 ? 3 : 0, treeAtLeast3: i < 4, building: i < 4, pond: i < 4 } }));
function fixture(t) {
  const db = new DatabaseSync(":memory:");
  db.exec(readFileSync(new URL("../drizzle/0000_living_ma_gnuci.sql", import.meta.url), "utf8"));
  for (const photo of photos(14)) db.prepare("INSERT INTO arena_photos(id,object_key,mime_type,byte_size,sha256,group_id,metadata_json,created_at,active) VALUES (?,?,'image/jpeg',1,?,?,?,0,?)")
    .run(photo.id, `object-${photo.id}`, photo.sha256, photo.groupId, JSON.stringify(photo.metadata), photo.id === id(0) ? 0 : 1);
  t.after(() => db.close());
  return db;
}
const snapshot = db => db.prepare("SELECT * FROM arena_photos ORDER BY id").all();
function activate(db, value) {
  const ids = validateActivePhotoIds(value);
  const rows = db.prepare(SELECT_PHOTO_BANK).all(JSON.stringify(ids));
  const selected = rows.map(row => ({ id: row.id, groupId: row.group_id, sha256: row.sha256, metadata: JSON.parse(row.metadata_json) }));
  const topics = validateActivePhotoBank(ids, selected);
  db.prepare(ACTIVATE_PHOTO_BANK).run(JSON.stringify(ids));
  return topics;
}

test("active bank validates bounded unique UUIDs, including case-insensitive duplicates", () => {
  for (const value of [undefined, null, {}, [], [1], ["bad"], Array.from({ length: 129 }, (_, i) => id(i))]) {
    assert.throws(() => validateActivePhotoIds(value), { code: "invalid_photo_bank" });
  }
  assert.throws(() => validateActivePhotoIds([id(10), id(10).toUpperCase()]), { code: "duplicate_photo_id" });
  assert.deepEqual(validateActivePhotoIds([id(10).toUpperCase()]), [id(10)]);
  assert.equal(validateActivePhotoIds(Array.from({ length: 128 }, (_, i) => id(i))).length, 128);
});

test("missing rows and incomplete theme/group banks leave the active set unchanged", t => {
  const db = fixture(t), before = snapshot(db);
  assert.throws(() => activate(db, [...photos(11).map(p => p.id), id(999)]), { code: "photo_not_found", status: 404 });
  assert.throws(() => activate(db, photos(10).map(p => p.id)), { code: "bank_not_ready", status: 409 });
  assert.deepEqual(snapshot(db), before);
  const aliased = photos(11); aliased[10].groupId = aliased[9].groupId;
  assert.throws(() => validateActivePhotoBank(aliased.map(p => p.id), aliased), { code: "bank_not_ready" });
  const copied = photos(11); copied[10].sha256 = copied[9].sha256;
  assert.throws(() => validateActivePhotoBank(copied.map(p => p.id), copied), { code: "bank_not_ready" });
});

test("one atomic activation reactivates selected photos, retires others and is idempotent without editing bytes/metadata", t => {
  const db = fixture(t), before = snapshot(db), selected = photos(11).map(p => p.id);
  const topics = activate(db, selected);
  assert.equal(topics.length, 4); assert.ok(topics.every(topic => topic.ready));
  const after = snapshot(db);
  assert.deepEqual(after.map(row => row.active), [...Array(11).fill(1), 0, 0, 0]);
  const withoutActive = row => { const copy = { ...row }; delete copy.active; return copy; };
  assert.deepEqual(after.map(withoutActive), before.map(withoutActive));
  activate(db, selected); assert.deepEqual(snapshot(db), after);
  // Every permitted theme/count must be constructible with independent groups.
  for (const theme of Object.values(THEMES)) for (let count = theme.min; count <= theme.max; count++) {
    let first = true;
    const challenge = makeChallenge(photos(11), theme.id, limit => {
      if (first) { first = false; return count - theme.min; }
      return limit - 1;
    });
    assert.equal(challenge.answerTileIds.length, count);
    assert.equal(new Set(challenge.tiles.map(tile => tile.photoId)).size, 9);
  }
});

test("a storage failure during the single UPDATE rolls back every active flag", t => {
  const db = fixture(t), before = snapshot(db);
  db.exec(`CREATE TRIGGER fail_switch BEFORE UPDATE OF active ON arena_photos WHEN NEW.id = '${id(13)}' BEGIN SELECT RAISE(ABORT, 'fixture failure'); END`);
  assert.throws(() => activate(db, photos(11).map(p => p.id)), /fixture failure/);
  assert.deepEqual(snapshot(db), before);
});
