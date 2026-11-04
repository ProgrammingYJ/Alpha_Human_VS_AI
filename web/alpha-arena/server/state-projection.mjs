import { publicState } from "./logic.mjs";
import { remotePublic, remoteReady } from "./remote.mjs";
import { startRequestPublic } from "./gpu-start.mjs";
import { projectSelectionPlan } from "./selection-plan.mjs";
import { imageBarrierPublic } from "./image-barrier.mjs";

/**
 * A heartbeat can commit during the asynchronous remote-row read. Capture the
 * projection clock afterwards so that this newer row is never judged against
 * an older request timestamp. Use this same clock for serverNow and liveness.
 */
export async function projectStateAfterRemoteRead(room, round, role, readRemote, clock = Date.now) {
  const remote = await readRemote(room.id);
  const now = clock();
  const state = publicState(room, round, role === "engine" ? "bot" : role, now);
  if (!remote) return state;
  state.bot.ready = remoteReady(room, remote, now);
  return imageBarrierPublic(projectSelectionPlan({ ...state, startRequest: startRequestPublic(room), lastStartCancellationReason: room.last_start_cancel_reason ?? null,
    remote: remotePublic(room, remote, role, now) }, round, role, now), room, round, now);
}
