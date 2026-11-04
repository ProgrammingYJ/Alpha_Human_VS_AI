import { ArenaError, bankReadiness } from "./logic.mjs";

const PHOTO_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function validateActivePhotoIds(value) {
  if (!Array.isArray(value) || value.length < 1 || value.length > 128 ||
      value.some(id => typeof id !== "string" || !PHOTO_ID.test(id))) {
    throw new ArenaError("invalid_photo_bank", "활성 사진 ID를 1~128개 지정해 주세요.");
  }
  const ids = value.map(id => id.toLowerCase());
  if (new Set(ids).size !== ids.length) {
    throw new ArenaError("duplicate_photo_id", "활성 사진 ID가 중복되었습니다.");
  }
  return ids;
}

export function validateActivePhotoBank(ids, photos) {
  if (photos.length !== ids.length || new Set(photos.map(photo => photo.id)).size !== ids.length ||
      photos.some(photo => !ids.includes(photo.id))) {
    throw new ArenaError("photo_not_found", "지정한 사진을 모두 찾지 못했습니다.", 404);
  }
  const topics = bankReadiness(photos);
  if (!topics.every(topic => topic.ready)) {
    throw new ArenaError("bank_not_ready", "네 유형의 모든 정답 수를 출제할 독립 사진이 부족합니다.", 409);
  }
  return topics;
}

// A JSON array uses one D1 bind parameter even for a 128-photo bank. One UPDATE
// changes the complete set atomically; existing rounds keep their photo IDs.
export const SELECT_PHOTO_BANK = "SELECT * FROM arena_photos WHERE id IN (SELECT value FROM json_each(?))";
export const ACTIVATE_PHOTO_BANK = "UPDATE arena_photos SET active = CASE WHEN id IN (SELECT value FROM json_each(?)) THEN 1 ELSE 0 END";
