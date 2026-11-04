/** Local SERVER API tests simulate readiness after fetching pixels. This does
 * not certify browser decoding/visibility; browser QA is separate. No labels. */
import assert from "node:assert/strict";

export async function releaseImageBarrier({ origin, roomId, human, viewer, engine, state }) {
  const path = `/api/rooms/${roomId}`;
  const post = async (suffix, token, body) => {
    const response = await fetch(origin + path + suffix, { method: "POST", headers: {
      Authorization: `Bearer ${token}`, "Content-Type": "application/json",
    }, body: JSON.stringify(body) });
    const result = await response.json();
    assert.equal(response.status, 200, `Readiness action failed: ${result.code ?? response.status}`);
    return result.state;
  };
  assert.equal(state.phase, "loading");
  assert.equal(state.preloadTiles.length, 9);
  for (const tile of state.preloadTiles) {
    const response = await fetch(origin + tile.url);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.ok((await response.arrayBuffer()).byteLength > 0);
  }
  const identity = { roundId: state.roundId, requestId: state.startRequest.id, imageLoadId: state.imageLoad.id };
  await post("/images-ready", human, { ...identity, ready: true });
  await post("/images-ready", viewer, { ...identity, ready: true });
  const countdown = await post("/engine", engine, { ...identity, action: "images_ready", roundNumber: state.roundNumber });
  assert.equal(countdown.phase, "countdown");
  assert.equal(countdown.imageLoad.humanReady, true);
  assert.equal(countdown.imageLoad.botReady, true);
  assert.equal(countdown.imageLoad.engineReady, true);
  assert.ok(countdown.startAt > countdown.serverNow);
  return countdown;
}
