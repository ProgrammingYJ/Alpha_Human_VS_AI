import { ArenaError } from "./logic.mjs";
import { TILE_INTERVAL_MS } from "./remote.mjs";
import { submitStatement } from "./statements.mjs";

export const PLAN_BUFFER_MS = 500;

export function validatePlanIndices(value) {
  if (!Array.isArray(value) || value.length > 9 || value.some(index => !Number.isInteger(index) || index < 0 || index > 8)
      || new Set(value).size !== value.length) throw new ArenaError("invalid_selection", "모델이 고른 서로 다른 타일 번호만 보낼 수 있습니다.");
  return value;
}

export function planFor(round) {
  if (!round || round.bot_plan_indices_json == null) return null;
  return { roundId: round.id, selectedIndices: JSON.parse(round.bot_plan_indices_json),
    startAt: round.bot_plan_start_at, intervalMs: TILE_INTERVAL_MS, submitAt: round.bot_plan_submit_at };
}

export function samePlan(round, indices) {
  return round.bot_plan_indices_json === JSON.stringify(indices);
}

/** Scheduled selections stop at the canonical winner/deadline, not at a late poll. */
export function planPrefix(plan, now, finishedAt = null, deadlineAt = null) {
  if (!plan) return [];
  const cutoff = Math.min(now, finishedAt ?? Infinity, deadlineAt ?? Infinity);
  const count = cutoff < plan.startAt ? 0 : Math.min(plan.selectedIndices.length, 1 + Math.floor((cutoff - plan.startAt) / plan.intervalMs));
  return plan.selectedIndices.slice(0, count);
}

export function projectSelectionPlan(state, round, role, now) {
  if (!state.remote) return state;
  state.remote.selectionPlanSupported = true;
  const plan = planFor(round);
  if (!plan) return state;
  const prefix = planPrefix(plan, now, state.result?.finishedAt, state.deadlineAt);
  state.remote.sequence = prefix.length;
  state.remote.lastSelectionAt = prefix.length ? plan.startAt + (prefix.length - 1) * plan.intervalMs : null;
  if (role !== "human") state.remote.selectedIndices = prefix;
  // Only the read-only bot viewer receives the future model predictions.
  // The human never receives this plan or its private correctness field.
  if (role === "bot") state.remote.selectionPlan = plan;
  if (state.phase !== "result") state.remote.engineStage = round.bot_submitted_at !== null ? "submitted" : "selecting";
  return state;
}

// The live engine and untouched per-round input state are checked in the write.
export const PLAN_ACCEPT = `UPDATE arena_rounds SET bot_plan_indices_json = ?, bot_plan_start_at = ?, bot_plan_submit_at = ?, bot_plan_correct = ? WHERE id = ? AND bot_plan_indices_json IS NULL AND bot_submitted_at IS NULL AND bot_correct IS NULL AND COALESCE(human_correct,0) <> 1 AND start_at <= ? AND deadline_at > ? AND EXISTS (SELECT 1 FROM arena_rooms AS room JOIN arena_remote_rooms AS remote ON remote.room_id = room.id WHERE room.id = ? AND room.round_id = arena_rounds.id AND room.phase = 'active' AND room.expires_at > ? AND remote.engine_token_hash = ? AND remote.engine_seen_at >= ? AND remote.engine_seen_at <= ? AND remote.engine_ready = 1 AND remote.engine_stage <> 'error' AND remote.sequence = 0 AND remote.selected_json = '[]')`;

// No heartbeat predicate: after acceptance the complete fixed ML result is on
// the server. A PC/network disconnect cannot change this immutable schedule.
export const PLAN_SETTLE_ROUND = `UPDATE arena_rounds SET bot_submitted_at = bot_plan_submit_at, bot_correct = bot_plan_correct, bot_elapsed_ms = bot_plan_submit_at - start_at WHERE id = ? AND bot_plan_indices_json IS NOT NULL AND bot_submitted_at IS NULL AND bot_correct IS NULL AND COALESCE(human_correct,0) <> 1 AND bot_plan_submit_at <= ? AND bot_plan_submit_at >= start_at AND bot_plan_submit_at < deadline_at AND EXISTS (SELECT 1 FROM arena_rooms WHERE id = ? AND round_id = arena_rounds.id AND phase = 'active' AND expires_at > ?)`;

// This guard is essential even if a state poll has not yet materialized the
// scheduled bot submission. At the exact due timestamp the bot is first.
export const PLAN_HUMAN_SUBMIT = submitStatement("human") + ` AND NOT (COALESCE(bot_plan_correct,0) = 1 AND bot_plan_submit_at <= ? AND bot_plan_submit_at < deadline_at)`;
