import test from "node:test";
import assert from "node:assert/strict";
import { clearRemoteSessions, currentSessionRequest, remoteSessionKeys, resetSessionFailure, sessionKey } from "./arena-session.mjs";

const context = (patch = {}) => ({ generation: 4, roomId: "old-room", storageKey: sessionKey("human", "remote", "A"), ...patch });

test("explicit reset removes exactly four remote keys without reading saved credentials", () => {
  const removed = [];
  clearRemoteSessions({ getItem() { throw new Error("must not read a saved token"); }, removeItem(key) { removed.push(key); } });
  assert.deepEqual(removed, ["alpha-arena-human-remote-A", "alpha-arena-human-remote-B", "alpha-arena-bot-remote-A", "alpha-arena-bot-remote-B"]);
  assert.deepEqual(removed, remoteSessionKeys);
  assert.ok(!removed.includes(sessionKey("human", "legacy", "A")));
});

test("only reset and expired room failures clear the current role/lane session", () => {
  for (const code of ["room_reset", "room_expired"]) {
    assert.equal(resetSessionFailure({ status: 410, code }, context(), context()), true);
    assert.equal(resetSessionFailure({ status: 409, code }, context(), context()), false);
  }
  for (const code of ["round_changed", "engine_disconnected", "bank_not_ready", undefined]) {
    assert.equal(resetSessionFailure({ status: 410, code }, context(), context()), false);
  }
});

test("old poll and action failures cannot clear a new room, reconnected token generation, or different lane", () => {
  const failure = { status: 410, code: "room_reset" };
  for (const current of [context({ generation: 5 }), context({ roomId: "new-room" }),
    context({ storageKey: sessionKey("human", "remote", "B") }),
    context({ storageKey: sessionKey("bot", "remote", "A") }), context({ roomId: null })]) {
    assert.equal(currentSessionRequest(context(), current), false);
    assert.equal(resetSessionFailure(failure, context(), current), false);
  }
});

test("legacy expiration uses its own selected session key", () => {
  const legacy = context({ storageKey: sessionKey("bot", "legacy", "B") });
  assert.equal(resetSessionFailure({ status: 410, code: "room_expired" }, legacy, legacy), true);
  assert.equal(resetSessionFailure({ status: 410, code: "room_reset" }, legacy, context()), false);
});
