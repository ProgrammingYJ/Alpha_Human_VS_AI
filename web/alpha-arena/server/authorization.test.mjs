import test from "node:test";
import assert from "node:assert/strict";
import { ownerMatches } from "./authorization.mjs";

test("only the exact configured Sites owner receives keyless administrator access", () => {
  assert.equal(ownerMatches("owner-uid", "owner-uid"), true);
  assert.equal(ownerMatches("owner-uid", "different-uid"), false);
  assert.equal(ownerMatches("owner-uid", null), false);
  assert.equal(ownerMatches(undefined, "owner-uid"), false);
  assert.equal(ownerMatches("", ""), false);
  assert.equal(ownerMatches(undefined, "local_seedy"), false);
  assert.equal(ownerMatches("local_seedy", "local_seedy"), true);
});
