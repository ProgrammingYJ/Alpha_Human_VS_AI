import test from "node:test";
import assert from "node:assert/strict";
import { THEMES, validatePhotoMetadata, themeTruth, bankReadiness, makeChallenge, exactMatch, validateSelection, publicState, roundPhase, winnerFor } from "./logic.mjs";

const meta = (overrides = {}) => validatePhotoMetadata({ personCount: null, treeCount: null, treeAtLeast3: null, building: null, pond: null, groupId: "g", source: "school", usageNote: "Evaluation only", ...overrides });
function pool(positive = 4, negative = 7) {
  return Array.from({ length: positive + negative }, (_, i) => ({ id: `private-photo-${i}`, groupId: `g${i}`, sha256: `sha${i}`, metadata: meta({ personCount: i < positive ? 3 : 0, treeAtLeast3: i < positive, building: i < positive, pond: i < positive }) }));
}
const room = { id: "room", code: "CODEABCD", human_token_hash: "SECRET_HUMAN", bot_token_hash: "SECRET_BOT", human_ready: 1, bot_ready: 1, phase: "active", round_number: 1 };
function round(overrides = {}) {
  return { id: "round", theme_id: "person_ge3", tiles_json: JSON.stringify([{ id: "tile-public", photoId: "SECRET_PHOTO" }]), answer_json: '["SECRET_ANSWER"]', start_at: 2000, deadline_at: 92000, human_submitted_at: null, bot_submitted_at: null, human_correct: null, bot_correct: null, human_elapsed_ms: null, bot_elapsed_ms: null, ...overrides };
}
test("unknown labels are never guessed negatives; tree lower bounds cannot prove absence", () => {
  assert.equal(themeTruth(meta(), "person_ge3"), null);
  assert.equal(themeTruth(meta({ treeCountMinimum: 2 }), "tree_ge3"), null);
  assert.equal(themeTruth(meta({ treeCountMinimum: 3 }), "tree_ge3"), true);
  assert.equal(themeTruth(meta({ treeAtLeast3: false }), "tree_ge3"), false);
  assert.equal(themeTruth(meta({ treeCount: 2 }), "tree_ge3"), false);
});
test("metadata rejects contradictory counts, bool counts and unsupported label values", () => {
  for (const value of [-1, true, 1.5, "3"]) assert.throws(() => meta({ personCount: value }));
  assert.throws(() => meta({ treeCount: 2, treeAtLeast3: true }));
  assert.throws(() => meta({ treeCountMinimum: 3, treeAtLeast3: false }));
  assert.throws(() => meta({ building: 0 }));
  assert.throws(() => meta({ groupId: "" }));
  assert.match(meta().usagePolicy, /never_training/);
});
test("readiness requires every allowed answer-count range, not an answer-shaped shortcut", () => {
  assert.ok(bankReadiness(pool()).every((topic) => topic.ready));
  const short = bankReadiness(pool(4, 6));
  assert.equal(short.find((topic) => topic.id === "tree_ge3").ready, true);
  assert.equal(short.find((topic) => topic.id === "person_ge3").ready, false);
});
test("challenge uses exactly nine distinct original groups and opaque per-round IDs", () => {
  for (const theme of Object.values(THEMES)) {
    let next = 0;
    const result = makeChallenge(pool(), theme.id, () => 0, () => `tile-${next++}`);
    assert.equal(result.tiles.length, 9);
    assert.equal(new Set(result.tiles.map((tile) => tile.photoId)).size, 9);
    assert.equal(result.answerTileIds.length, theme.min);
    for (const tile of result.tiles) assert.match(tile.id, /^tile-/);
  }
});
test("identical-byte copies and capture-group aliases cannot occupy two tiles", () => {
  const photos = pool(4, 7); photos[10].sha256 = photos[9].sha256;
  assert.equal(bankReadiness(photos).find((topic) => topic.id === "person_ge3").ready, false);
  photos[10].sha256 = "other"; photos[10].groupId = photos[9].groupId;
  assert.equal(bankReadiness(photos).find((topic) => topic.id === "person_ge3").ready, false);
});
test("mixed positive/negative capture groups do not dead-end a feasible selection", () => {
  const photos = pool(4, 7); photos[0].groupId = photos[4].groupId;
  let counter = 0;
  const result = makeChallenge(photos, "person_ge3", () => 0, () => `${counter++}`);
  const group = (id) => photos.find((p) => p.id === id).groupId;
  assert.equal(new Set(result.tiles.map((tile) => group(tile.photoId))).size, 9);
});
test("exact-set grading rejects omissions, extra choices, foreign and duplicate IDs", () => {
  assert.equal(exactMatch(["b", "a"], ["a", "b"]), true);
  assert.equal(exactMatch(["a"], ["a", "b"]), false);
  assert.equal(exactMatch(["a", "b", "c"], ["a", "b"]), false);
  assert.throws(() => validateSelection(["x"], ["a", "b"]));
  assert.throws(() => validateSelection(["a", "a"], ["a", "b"]));
  assert.deepEqual(validateSelection([], ["a"]), []);
});
test("phase uses future common start and deadline boundaries", () => {
  assert.equal(roundPhase(round(), 1999, "active"), "countdown");
  assert.equal(roundPhase(round(), 2000, "active"), "playing");
  assert.equal(roundPhase(round(), 92000, "active"), "result");
  assert.equal(roundPhase(null, 1000, "lobby"), "lobby");
});
test("lobby/countdown do not expose challenge pixels, evaluator answers or private fields", () => {
  const state = publicState(room, round(), "human", 1999);
  assert.deepEqual(state.tiles, []); assert.equal(state.topic, null);
  const serialized = JSON.stringify(state);
  for (const forbidden of ["SECRET", "answer", "sha256", "groupId", "personCount", "object_key"]) assert.equal(serialized.includes(forbidden), false);
  const live = publicState(room, round(), "human", 2000);
  assert.deepEqual(live.tiles, [{ id: "tile-public", url: "/api/photos/tile-public" }]);
  assert.deepEqual(live.topic.condition, { task_type: "person_count", operator: "gte", n: 3 });
  assert.equal(JSON.stringify(live).includes("SECRET"), false);
});
test("wrong attempts remain editable; first correct answer immediately freezes both timers", () => {
  const wrong = round({ human_correct: 0, human_elapsed_ms: 300 });
  const own = publicState(room, wrong, "human", 2400);
  assert.equal(own.phase, "playing"); assert.equal(own.human.submitted, false); assert.equal(own.human.correct, false);
  assert.equal(publicState(room, wrong, "bot", 2400).human.correct, null);
  const correct = { ...wrong, human_submitted_at: 2600, human_correct: 1, human_elapsed_ms: 600 };
  for (const role of ["human", "bot"]) {
    const state = publicState(room, correct, role, 4000);
    assert.equal(state.phase, "result"); assert.equal(state.result.winner, "human");
    assert.equal(state.result.finishedAt, 2600); assert.equal(state.result.elapsedMs, 600); assert.equal(state.result.reason, "correct");
  }
  assert.equal(winnerFor(round({ bot_correct: 1, bot_submitted_at: 2500, bot_elapsed_ms: 500 })), "bot");
  const timeout = publicState(room, wrong, "human", 100000);
  assert.equal(timeout.phase, "result"); assert.equal(timeout.result.winner, null);
  assert.equal(timeout.result.reason, "timeout"); assert.equal(timeout.result.finishedAt, 92000);
});
