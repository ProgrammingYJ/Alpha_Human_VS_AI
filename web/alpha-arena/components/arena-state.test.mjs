import test from "node:test";
import assert from "node:assert/strict";
import { acceptsRoomState, publicRoundView, remoteDisplayIndices, roomPollIntervalMs, sameActionContext, validSelectionPlan } from "./arena-state.mjs";

const cursor = (patch = {}) => ({ roomId: "room-A", revision: 10, serverNow: 1000,
  roundNumber: 1, roundId: "round-1", phase: "playing", remote: { sequence: 2 }, ...patch });

test("only an actively playing remote AI viewer uses faster polling", () => {
  assert.equal(roomPollIntervalMs("bot", cursor()), 125);
  assert.equal(roomPollIntervalMs("human", cursor()), 500);
  assert.equal(roomPollIntervalMs("bot", cursor({ remote: undefined })), 500);
  for (const phase of ["lobby", "queued", "countdown", "result"]) assert.equal(roomPollIntervalMs("bot", cursor({ phase })), 500);
  assert.equal(roomPollIntervalMs("bot", null), 500);
});

test("next participant lobby blocks the old result even within one millisecond", () => {
  const result = cursor({ phase: "result" });
  const lobby = cursor({ revision: 11, phase: "lobby", roundId: null, remote: { sequence: 0 } });
  assert.equal(acceptsRoomState(result, lobby), true);
  assert.equal(acceptsRoomState(lobby, result), false);
  assert.equal(acceptsRoomState(lobby, { ...result, revision: 11, serverNow: 1001 }), false);
});

test("a new room revision wins over clock skew, and a stale revision cannot win with a later clock", () => {
  const result = cursor({ phase: "result", serverNow: 1010 });
  const lobby = cursor({ revision: 11, serverNow: 1005, phase: "lobby", roundId: null, remote: { sequence: 0 } });
  assert.equal(acceptsRoomState(result, lobby), true);
  assert.equal(acceptsRoomState(lobby, { ...result, serverNow: 2000 }), false);
});

test("a viewer may miss the result poll before the operator prepares the next participant", () => {
  const active = cursor();
  const lobby = cursor({ revision: 12, serverNow: 1001, phase: "lobby", roundId: null, remote: { sequence: 0 } });
  assert.equal(acceptsRoomState(active, lobby), true);
  assert.equal(acceptsRoomState(active, { ...lobby, revision: 10 }), false);
  assert.equal(acceptsRoomState(lobby, { ...active, revision: 11, serverNow: 2000 }), false);
});

test("polling may skip intermediate next-game phases while the participant number advances", () => {
  const lobby = cursor({ revision: 11, phase: "lobby", roundId: null, remote: { sequence: 0 } });
  const second = cursor({ revision: 12, roundNumber: 2, roundId: "round-2", serverNow: 1010, remote: { sequence: 0 } });
  for (const phase of ["countdown", "playing", "result"]) assert.equal(acceptsRoomState(lobby, { ...second, phase }), true);
  assert.equal(acceptsRoomState(second, { ...lobby, serverNow: 2000 }), false);
  assert.equal(acceptsRoomState(second, cursor({ serverNow: 2000, phase: "result" })), false);
});

test("late same-game responses cannot rewind countdown, selected tiles or server time", () => {
  const active = cursor();
  assert.equal(acceptsRoomState(active, cursor({ phase: "countdown", serverNow: 1001 })), false);
  assert.equal(acceptsRoomState(active, cursor({ serverNow: 1001, remote: { sequence: 1 } })), false);
  assert.equal(acceptsRoomState(active, cursor({ serverNow: 999, remote: { sequence: 3 } })), false);
  assert.equal(acceptsRoomState(active, cursor({ serverNow: 1001, remote: { sequence: 3 } })), true);
});

test("lobby heartbeat updates remain visible and another lane room cannot replace it", () => {
  const lobby = cursor({ phase: "lobby", roundId: null, remote: { sequence: 0 } });
  assert.equal(acceptsRoomState(lobby, { ...lobby, serverNow: 1001 }), true);
  assert.equal(acceptsRoomState(lobby, { ...lobby, roomId: "room-B", serverNow: 1001 }), false);
  assert.equal(acceptsRoomState(lobby, cursor({ roundId: "different-id", serverNow: 1001 })), false);
});

test("legacy one-game results cannot reset to the same lobby", () => {
  const result = cursor({ phase: "result", remote: undefined, revision: undefined });
  assert.equal(acceptsRoomState(result, cursor({ phase: "lobby", roundId: null, remote: undefined, revision: undefined, serverNow: 1001 })), false);
  assert.equal(acceptsRoomState(result, { ...result, serverNow: 1001 }), true);
});

const queued = (patch = {}) => cursor({ phase: "queued", roundId: null, startRequest: { id: "request-1" }, remote: { sequence: 0 }, ...patch });

test("queue cancellation and requeue reject old polls even with a later server clock", () => {
  const first = queued();
  const cancelled = cursor({ phase: "lobby", roundId: null, revision: 11, startRequest: null });
  const second = queued({ revision: 12, startRequest: { id: "request-2" } });
  assert.equal(acceptsRoomState(first, cancelled), true);
  assert.equal(acceptsRoomState(cancelled, second), true);
  assert.equal(acceptsRoomState(second, { ...first, serverNow: 2000 }), false);
  assert.equal(acceptsRoomState(second, { ...cancelled, serverNow: 2000 }), false);
  assert.equal(acceptsRoomState(first, second), true);
});

test("reservation identity cannot change or cancel at the same revision", () => {
  const current = queued();
  assert.equal(acceptsRoomState(current, { ...current, serverNow: 1001 }), true);
  assert.equal(acceptsRoomState(current, queued({ startRequest: { id: "other" }, serverNow: 1001 })), false);
  assert.equal(acceptsRoomState(current, cursor({ phase: "lobby", roundId: null, serverNow: 1001 })), false);
  assert.equal(acceptsRoomState(null, queued({ startRequest: null })), false);
  assert.equal(acceptsRoomState(null, queued({ remote: undefined })), false);
});

test("reserved start advances the participant once and ignores delayed queue replies", () => {
  const waiting = queued();
  const started = cursor({ phase: "countdown", revision: 11, roundNumber: 2, roundId: "round-2", startRequest: null });
  for (const phase of ["countdown", "playing", "result"]) assert.equal(acceptsRoomState(waiting, { ...started, phase }), true);
  assert.equal(acceptsRoomState(started, { ...waiting, serverNow: 2000 }), false);
  assert.equal(acceptsRoomState(waiting, queued({ roundNumber: 2, revision: 11 })), false);
});

test("a viewer can skip next-participant lobby directly to the next reservation", () => {
  assert.equal(acceptsRoomState(cursor({ phase: "result" }), queued({ revision: 12, startRequest: { id: "next-request" } })), true);
  assert.equal(acceptsRoomState(cursor({ phase: "result" }), queued()), false);
});

test("old start or cancellation errors cannot overwrite a new queue", () => {
  const lobby = cursor({ phase: "lobby", roundId: null, startRequest: null });
  const first = queued({ revision: 11 });
  const second = queued({ revision: 13, startRequest: { id: "request-2" } });
  assert.equal(sameActionContext(lobby, first), false);
  assert.equal(sameActionContext(first, second), false);
  assert.equal(sameActionContext(first, { ...first, serverNow: 1001 }), true);
  assert.equal(sameActionContext(first, { ...first, startRequest: { id: "other" } }), false);
});

test("queued presentation hides early question pixels and timer fields", () => {
  const hidden = publicRoundView({ phase: "queued", topic: { prompt: "hidden question" }, tiles: [{ id: "hidden-photo" }], startAt: 123, deadlineAt: 456 });
  assert.deepEqual(hidden, { queued: true, loading: false, topic: null, tiles: [], startAt: null, deadlineAt: null });
  const visible = publicRoundView({ phase: "playing", topic: { prompt: "question" }, tiles: [{ id: "photo" }], startAt: 123, deadlineAt: 456 }, 123);
  assert.equal(visible.topic.prompt, "question");
  assert.equal(visible.tiles[0].id, "photo");
  assert.equal(visible.startAt, 123);
});

test("prepared photos keep one identity across loading/countdown/play and reveal the question only at common time", () => {
  const photos = Array.from({length:9}, (_,index)=>({id:`tile-${index}`,url:`/api/photos/tile-${index}`}));
  const topic={prompt:"public question"};
  const loading={phase:"loading",preloadTiles:photos,topic,startAt:999,deadlineAt:9999};
  const hidden=publicRoundView(loading,2000);
  assert.equal(hidden.topic,null); assert.equal(hidden.startAt,null); assert.equal(hidden.deadlineAt,null); assert.equal(hidden.tiles,photos);
  const countdown={phase:"countdown",preloadTiles:photos,preloadTopic:topic,topic:null,tiles:[],startAt:3000,deadlineAt:93000};
  assert.equal(publicRoundView(countdown,2999).topic,null);
  assert.equal(publicRoundView(countdown,3000).topic,topic);
  assert.equal(publicRoundView(countdown,3000).tiles,photos);
  assert.equal(publicRoundView({...countdown,phase:"playing",topic},2999).topic,null);
  assert.equal(publicRoundView({...countdown,phase:"playing",topic,preloadTiles:undefined,tiles:photos},3000).tiles,photos);
});
test("a fresh prestart epoch can rewind countdown while stale epoch or same revision cannot", () => {
  const current=cursor({phase:"countdown",roundId:"round",roundNumber:1,revision:4,imageLoad:{id:"old"}});
  const reset=cursor({phase:"loading",roundId:"round",roundNumber:1,revision:5,imageLoad:{id:"new"}});
  assert.equal(acceptsRoomState(current,reset),true);
  assert.equal(acceptsRoomState(current,{...reset,revision:4}),false);
  assert.equal(acceptsRoomState(current,{...reset,imageLoad:{id:"old"}}),false);
  assert.equal(acceptsRoomState(reset,current),false);
  const running={...current,phase:"playing"};
  assert.equal(acceptsRoomState(running,reset),false);
});

const planned = overrides => ({ phase: "playing", roundId: "round-plan", deadlineAt: 90000,
  result: { finishedAt: null, winner: null }, remote: { selectedIndices: [],
    selectionPlan: { roundId: "round-plan", selectedIndices: [4, 0, 8], startAt: 1000, intervalMs: 250, submitAt: 1500 } }, ...overrides });

test("a received valid plan replays between polls and lowers only that viewer's polling load", () => {
  const state = planned();
  assert.equal(roomPollIntervalMs("bot", state), 500);
  assert.equal(roomPollIntervalMs("human", state), 500);
  assert.equal(roomPollIntervalMs("bot", { ...state, remote: {} }), 125);
  for (const [now, expected] of [[999, []], [1000, [4]], [1249, [4]], [1250, [4, 0]], [1500, [4, 0, 8]]]) assert.deepEqual(remoteDisplayIndices(state, now), expected);
  assert.equal(state.result.winner, null, "Playback cannot manufacture a winner before the server result");
});
test("late plan delivery catches up and a canonical early human win clips future playback", () => {
  assert.deepEqual(remoteDisplayIndices(planned(), 9999), [4, 0, 8]);
  assert.deepEqual(remoteDisplayIndices(planned({ phase: "result", result: { finishedAt: 1249, winner: "human" } }), 9999), [4]);
  assert.deepEqual(remoteDisplayIndices(planned({ phase: "result", result: { finishedAt: 900, winner: "human" } }), 9999), []);
});
test("a stale round, malformed plan or empty prediction cannot add fabricated visible selections", () => {
  const state = planned();
  for (const change of [{ roundId: "previous-round" }, { intervalMs: 1 }, { selectedIndices: [4, 4] }, { selectedIndices: [9] }, { submitAt: 1 }]) {
    const bad = { ...state, remote: { selectedIndices: [2], selectionPlan: { ...state.remote.selectionPlan, ...change } } };
    assert.equal(validSelectionPlan(bad), null); assert.deepEqual(remoteDisplayIndices(bad, 9999), [2]);
  }
  const empty = { ...state, remote: { selectedIndices: [], selectionPlan: { ...state.remote.selectionPlan, selectedIndices: [], submitAt: 1000 } } };
  assert.deepEqual(remoteDisplayIndices(empty, 9999), []);
});
