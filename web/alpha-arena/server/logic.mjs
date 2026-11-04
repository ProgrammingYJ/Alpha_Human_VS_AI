/** Pixel challenge rules and evaluator logic. This module never enters a client bundle. */
export const THEMES = Object.freeze({
  person_ge3: { id: "person_ge3", prompt: "사람이 3명 이상인 사진을 모두 선택하세요", condition: { task_type: "person_count", operator: "gte", n: 3 }, min: 2, max: 4 },
  tree_ge3: { id: "tree_ge3", prompt: "나무가 3그루 이상인 사진을 모두 선택하세요", condition: { task_type: "tree_count", operator: "gte", n: 3 }, min: 3, max: 4 },
  building_present: { id: "building_present", prompt: "건물이 있는 사진을 모두 선택하세요", condition: { task_type: "building_present" }, min: 2, max: 4 },
  pond_present: { id: "pond_present", prompt: "연못이 있는 사진을 모두 선택하세요", condition: { task_type: "pond_present" }, min: 2, max: 4 },
});
export class ArenaError extends Error {
  constructor(code, message, status = 400) { super(message); this.code = code; this.status = status; }
}
export function randomInt(max) {
  if (!Number.isInteger(max) || max < 1 || max > 0x100000000) throw new Error("Invalid random range");
  const limit = Math.floor(0x100000000 / max) * max;
  const bytes = new Uint32Array(1);
  do { crypto.getRandomValues(bytes); } while (bytes[0] >= limit);
  return bytes[0] % max;
}
export function shuffled(values, rng = randomInt) {
  const result = [...values];
  for (let i = result.length - 1; i > 0; i--) { const j = rng(i + 1); [result[i], result[j]] = [result[j], result[i]]; }
  return result;
}
function nullableCount(value, name) {
  if (value === undefined || value === null) return null;
  if (!Number.isSafeInteger(value) || value < 0 || value > 10000) throw new ArenaError("invalid_metadata", `${name}은 0 이상의 정수 또는 모름이어야 합니다.`);
  return value;
}
function nullableBoolean(value, name) {
  if (value === undefined || value === null) return null;
  if (typeof value !== "boolean") throw new ArenaError("invalid_metadata", `${name}은 참/거짓/모름이어야 합니다.`);
  return value;
}
function requiredText(value, name, max) {
  if (typeof value !== "string" || !value.trim() || value.trim().length > max) throw new ArenaError("invalid_metadata", `${name}을 확인해 주세요.`);
  return value.trim();
}
export function validatePhotoMetadata(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new ArenaError("invalid_metadata", "사진 메타데이터가 필요합니다.");
  if (!["school", "kaggle", "other", "owned"].includes(value.source)) throw new ArenaError("invalid_metadata", "사진 출처를 확인해 주세요.");
  const metadata = {
    personCount: nullableCount(value.personCount, "personCount"),
    treeCount: nullableCount(value.treeCount, "treeCount"),
    treeAtLeast3: nullableBoolean(value.treeAtLeast3, "treeAtLeast3"),
    treeCountMinimum: nullableCount(value.treeCountMinimum, "treeCountMinimum"),
    building: nullableBoolean(value.building, "building"),
    pond: nullableBoolean(value.pond, "pond"),
    groupId: requiredText(value.groupId, "같은 원본/연속 촬영 그룹", 200),
    source: value.source,
    usageNote: requiredText(value.usageNote, "사용 메모", 2000),
    usagePolicy: value.source === "school" ? "question_and_fixed_model_final_evaluation_only_never_training" : "question_bank_only_not_automatic_training_data",
  };
  if (metadata.treeCount !== null && metadata.treeCountMinimum !== null && metadata.treeCount < metadata.treeCountMinimum) throw new ArenaError("invalid_metadata", "나무 정확 수보다 하한이 클 수 없습니다.");
  if (metadata.treeAtLeast3 !== null && metadata.treeCount !== null && metadata.treeAtLeast3 !== (metadata.treeCount >= 3)) throw new ArenaError("invalid_metadata", "나무 수와 3그루 이상 판정이 서로 다릅니다.");
  if (metadata.treeAtLeast3 === false && metadata.treeCountMinimum !== null && metadata.treeCountMinimum >= 3) throw new ArenaError("invalid_metadata", "나무 하한과 판정이 서로 다릅니다.");
  if (value.provenance !== undefined) {
    if (!value.provenance || typeof value.provenance !== "object" || Array.isArray(value.provenance)) throw new ArenaError("invalid_metadata", "출처 기록을 확인해 주세요.");
    const serialized = JSON.stringify(value.provenance);
    if (serialized.length > 4000) throw new ArenaError("invalid_metadata", "출처 기록이 너무 깁니다.");
    metadata.provenance = value.provenance;
  }
  return metadata;
}
export function themeTruth(metadata, themeId) {
  if (themeId === "person_ge3") return metadata.personCount == null ? null : metadata.personCount >= 3;
  if (themeId === "tree_ge3") {
    if (typeof metadata.treeAtLeast3 === "boolean") return metadata.treeAtLeast3;
    if (metadata.treeCount != null) return metadata.treeCount >= 3;
    return metadata.treeCountMinimum != null && metadata.treeCountMinimum >= 3 ? true : null;
  }
  if (themeId === "building_present") return typeof metadata.building === "boolean" ? metadata.building : null;
  if (themeId === "pond_present") return typeof metadata.pond === "boolean" ? metadata.pond : null;
  throw new ArenaError("invalid_theme", "지원하지 않는 문제입니다.");
}
// Union exact-copy hashes and declared capture groups before choosing any tile.
function photoGroups(photos) {
  const parents = photos.map((_, i) => i); const seen = new Map();
  const find = (i) => { while (parents[i] !== i) { parents[i] = parents[parents[i]]; i = parents[i]; } return i; };
  photos.forEach((p, i) => { for (const key of [`group:${p.groupId}`, `sha:${p.sha256}`]) { if (seen.has(key)) parents[find(i)] = find(seen.get(key)); else seen.set(key, i); } });
  const groups = new Map(); photos.forEach((p, i) => { const key = find(i); if (!groups.has(key)) groups.set(key, []); groups.get(key).push(p); });
  return [...groups.values()];
}
function buckets(photos, themeId) {
  const onlyPositive = [], onlyNegative = [], mixed = [];
  for (const group of photoGroups(photos)) {
    const positive = group.filter((photo) => themeTruth(photo.metadata, themeId) === true);
    const negative = group.filter((photo) => themeTruth(photo.metadata, themeId) === false);
    const item = { positive, negative };
    if (positive.length && negative.length) mixed.push(item);
    else if (positive.length) onlyPositive.push(item);
    else if (negative.length) onlyNegative.push(item);
  }
  return { onlyPositive, onlyNegative, mixed };
}
export function bankReadiness(photos) {
  return Object.values(THEMES).map((theme) => {
    const b = buckets(photos, theme.id); const positiveGroups = b.onlyPositive.length + b.mixed.length; const negativeGroups = b.onlyNegative.length + b.mixed.length;
    const knownGroups = b.onlyPositive.length + b.onlyNegative.length + b.mixed.length;
    return { id: theme.id, positiveGroups, negativeGroups, knownGroups, requiredPositiveGroups: theme.max, requiredNegativeGroups: 9 - theme.min,
      ready: positiveGroups >= theme.max && negativeGroups >= 9 - theme.min && knownGroups >= 9 };
  });
}
export function makeChallenge(photos, themeId, rng = randomInt, id = () => crypto.randomUUID()) {
  const theme = THEMES[themeId]; if (!theme) throw new ArenaError("invalid_theme", "지원하지 않는 문제입니다.");
  const count = theme.min + rng(theme.max - theme.min + 1); const b = buckets(photos, themeId);
  const posOnly = shuffled(b.onlyPositive, rng); const negOnly = shuffled(b.onlyNegative, rng); const mixed = shuffled(b.mixed, rng);
  const positive = posOnly.slice(0, count); const mixedNeeded = count - positive.length;
  positive.push(...mixed.slice(0, mixedNeeded));
  const negative = shuffled([...negOnly, ...mixed.slice(mixedNeeded)], rng).slice(0, 9 - count);
  if (positive.length !== count || negative.length !== 9 - count) throw new ArenaError("bank_not_ready", "문제 사진이 부족합니다. 운영자에게 문의해 주세요.", 409);
  const picked = [...positive.map((group) => ({ photo: group.positive[rng(group.positive.length)], correct: true })),
    ...negative.map((group) => ({ photo: group.negative[rng(group.negative.length)], correct: false }))];
  const ordered = shuffled(picked, rng).map((item) => ({ ...item, tileId: id() }));
  return { themeId, tiles: ordered.map((item) => ({ id: item.tileId, photoId: item.photo.id })), answerTileIds: ordered.filter((item) => item.correct).map((item) => item.tileId) };
}
export function validateSelection(tileIds, allowedIds) {
  if (!Array.isArray(tileIds) || tileIds.length > 9 || tileIds.some((id) => typeof id !== "string" || !allowedIds.includes(id))) throw new ArenaError("invalid_selection", "이 문제의 타일만 선택할 수 있습니다.");
  if (new Set(tileIds).size !== tileIds.length) throw new ArenaError("invalid_selection", "같은 타일을 중복 제출할 수 없습니다.");
  return tileIds;
}
export function exactMatch(selected, answer) { return selected.length === answer.length && selected.every((id) => answer.includes(id)); }
export function roundPhase(round, now, storedPhase) {
  if (!round) return storedPhase === "queued" ? "queued" : "lobby";
  if (storedPhase === "loading") return "loading";
  if (storedPhase === "result" || now >= round.deadline_at || round.human_correct === 1 || round.bot_correct === 1) return "result";
  return now < round.start_at ? "countdown" : "playing";
}
export function winnerFor(round) {
  const h = round.human_correct === 1, b = round.bot_correct === 1;
  if (!h && !b) return null;
  if (h && !b) return "human"; if (b && !h) return "bot";
  // New SQL permits only one correct finisher. This ordering handles legacy
  // records defensively; an ended round can never be reopened by a later reply.
  return round.human_submitted_at <= round.bot_submitted_at ? "human" : "bot";
}
export function publicState(room, round, role, now) {
  const phase = roundPhase(round, now, room.phase); const visible = phase === "playing" || phase === "result";
  const participant = (who) => ({ ready: room[`${who}_ready`] === 1, submitted: round ? round[`${who}_submitted_at`] !== null : false,
    correct: round && (phase === "result" || role === who) && round[`${who}_correct`] !== null ? round[`${who}_correct`] === 1 : null,
    elapsedMs: round && (phase === "result" || role === who) ? round[`${who}_elapsed_ms`] : null });
  const theme = visible && round ? THEMES[round.theme_id] : null;
  const winner = phase === "result" && round ? winnerFor(round) : null;
  const finishedAt = phase === "result" && round ? (winner ? round[`${winner}_submitted_at`] : round.deadline_at) : null;
  return { serverNow: now, roomId: room.id, code: room.code, phase, roundId: round?.id ?? null, roundNumber: room.round_number, revision: room.revision,
    startAt: round?.start_at ?? null, deadlineAt: round?.deadline_at ?? null,
    topic: theme ? { id: theme.id, prompt: theme.prompt, condition: theme.condition } : null,
    tiles: visible && round ? JSON.parse(round.tiles_json).map((tile) => ({ id: tile.id, url: `/api/photos/${tile.id}` })) : [],
    human: participant("human"), bot: participant("bot"), result: { winner, finishedAt,
      elapsedMs: finishedAt !== null && round ? finishedAt - round.start_at : null,
      reason: phase === "result" ? (winner ? "correct" : "timeout") : null } };
}
