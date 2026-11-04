import { integer, sqliteTable, text, uniqueIndex, index } from "drizzle-orm/sqlite-core";

// Private evaluator metadata. Never select these rows into participant JSON.
export const arenaPhotos = sqliteTable("arena_photos", {
  id: text("id").primaryKey(),
  objectKey: text("object_key").notNull(),
  mimeType: text("mime_type").notNull(),
  byteSize: integer("byte_size").notNull(),
  sha256: text("sha256").notNull(),
  groupId: text("group_id").notNull(),
  metadataJson: text("metadata_json").notNull(),
  createdAt: integer("created_at").notNull(),
  active: integer("active").notNull().default(1),
}, (table) => [uniqueIndex("arena_photo_sha").on(table.sha256), index("arena_photo_group").on(table.groupId)]);

export const arenaRooms = sqliteTable("arena_rooms", {
  id: text("id").primaryKey(),
  code: text("code").notNull(),
  humanTokenHash: text("human_token_hash").notNull(),
  botTokenHash: text("bot_token_hash"),
  humanReady: integer("human_ready").notNull().default(1),
  botReady: integer("bot_ready").notNull().default(0),
  phase: text("phase").notNull().default("lobby"),
  roundId: text("round_id"),
  roundNumber: integer("round_number").notNull().default(0),
  revision: integer("revision").notNull().default(0),
  startRequestId: text("start_request_id"),
  startRequestedAt: integer("start_requested_at"),
  startExpiresAt: integer("start_expires_at"),
  lastStartCancelReason: text("last_start_cancel_reason"),
  createdAt: integer("created_at").notNull(),
  expiresAt: integer("expires_at").notNull(),
}, (table) => [uniqueIndex("arena_room_code").on(table.code)]);

export const arenaRounds = sqliteTable("arena_rounds", {
  id: text("id").primaryKey(),
  roomId: text("room_id").notNull().references(() => arenaRooms.id),
  number: integer("number").notNull(),
  themeId: text("theme_id").notNull(),
  tilesJson: text("tiles_json").notNull(),
  answerJson: text("answer_json").notNull(),
  startAt: integer("start_at").notNull(),
  deadlineAt: integer("deadline_at").notNull(),
  humanSubmittedAt: integer("human_submitted_at"),
  humanCorrect: integer("human_correct"),
  humanElapsedMs: integer("human_elapsed_ms"),
  botSubmittedAt: integer("bot_submitted_at"),
  botCorrect: integer("bot_correct"),
  botElapsedMs: integer("bot_elapsed_ms"),
  // One immutable, server-timed replay of the PC's already-computed ML result.
  // Correctness remains private and cannot be used by the PC or viewer.
  botPlanIndicesJson: text("bot_plan_indices_json"),
  botPlanStartAt: integer("bot_plan_start_at"),
  botPlanSubmitAt: integer("bot_plan_submit_at"),
  botPlanCorrect: integer("bot_plan_correct"),
  // Prepared pixels are acknowledged by both browsers and the PC before time starts.
  imageLoadId: text("image_load_id"),
  loadingExpiresAt: integer("loading_expires_at"),
  humanImagesReady: integer("human_images_ready").notNull().default(0),
  botImagesReady: integer("bot_images_ready").notNull().default(0),
  engineImagesReady: integer("engine_images_ready").notNull().default(0),
}, (table) => [uniqueIndex("arena_round_number").on(table.roomId, table.number), index("arena_round_room").on(table.roomId)]);

// Remote engines and read-only bot viewers have separate capabilities.
// This table is absent for the preserved physical-screen/legacy room mode.
export const arenaRemoteRooms = sqliteTable("arena_remote_rooms", {
  roomId: text("room_id").primaryKey().references(() => arenaRooms.id),
  lane: text("lane").notNull(),
  engineTokenHash: text("engine_token_hash"),
  engineSeenAt: integer("engine_seen_at"),
  engineStage: text("engine_stage").notNull().default("disconnected"),
  engineReady: integer("engine_ready").notNull().default(0),
  engineProtocol: integer("engine_protocol").notNull().default(1),
  selectedJson: text("selected_json").notNull().default("[]"),
  sequence: integer("sequence").notNull().default(0),
  lastSelectionAt: integer("last_selection_at"),
});
