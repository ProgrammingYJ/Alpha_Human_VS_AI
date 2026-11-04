import test from "node:test";
import assert from "node:assert/strict";
import { clockSample } from "./server-clock.mjs";

test("a slow state response cannot move an already synchronized common start", () => {
  const best = clockSample(null, 100_050, 1000, 1100);
  assert.equal(best.offset, 99_000);
  assert.equal(clockSample(best, 106_000, 1200, 6200), best);
  const faster = clockSample(best, 107_010, 8000, 8020);
  assert.equal(faster.offset, 99_000);
  assert.equal(9000 + faster.offset, 108_000);
});
test("a long-lived room refreshes stale samples and invalid timestamps cannot poison the clock", () => {
  const old = clockSample(null, 100_050, 1000, 1100);
  const renewed = clockSample(old, 131_200, 32_000, 32_400);
  assert.equal(renewed.offset, 99_000);
  assert.equal(clockSample(renewed, NaN, 1, 2), renewed);
  assert.equal(clockSample(renewed, 1, 3, 2), renewed);
});
test("an already committed countdown retains its clock anchor even when a refresh becomes due", () => {
  const best = clockSample(null, 100_050, 1000, 1100);
  assert.equal(clockSample(best, 140_000, 32_000, 39_000, true), best);
  assert.notEqual(clockSample(best, 140_000, 32_000, 39_000), best);
});
