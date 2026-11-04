CREATE TABLE `arena_photos` (
	`id` text PRIMARY KEY NOT NULL,
	`object_key` text NOT NULL,
	`mime_type` text NOT NULL,
	`byte_size` integer NOT NULL,
	`sha256` text NOT NULL,
	`group_id` text NOT NULL,
	`metadata_json` text NOT NULL,
	`created_at` integer NOT NULL,
	`active` integer DEFAULT 1 NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `arena_photo_sha` ON `arena_photos` (`sha256`);--> statement-breakpoint
CREATE INDEX `arena_photo_group` ON `arena_photos` (`group_id`);--> statement-breakpoint
CREATE TABLE `arena_rooms` (
	`id` text PRIMARY KEY NOT NULL,
	`code` text NOT NULL,
	`human_token_hash` text NOT NULL,
	`bot_token_hash` text,
	`human_ready` integer DEFAULT 1 NOT NULL,
	`bot_ready` integer DEFAULT 0 NOT NULL,
	`phase` text DEFAULT 'lobby' NOT NULL,
	`round_id` text,
	`round_number` integer DEFAULT 0 NOT NULL,
	`revision` integer DEFAULT 0 NOT NULL,
	`created_at` integer NOT NULL,
	`expires_at` integer NOT NULL
);
--> statement-breakpoint
CREATE UNIQUE INDEX `arena_room_code` ON `arena_rooms` (`code`);--> statement-breakpoint
CREATE TABLE `arena_rounds` (
	`id` text PRIMARY KEY NOT NULL,
	`room_id` text NOT NULL,
	`number` integer NOT NULL,
	`theme_id` text NOT NULL,
	`tiles_json` text NOT NULL,
	`answer_json` text NOT NULL,
	`start_at` integer NOT NULL,
	`deadline_at` integer NOT NULL,
	`human_submitted_at` integer,
	`human_correct` integer,
	`human_elapsed_ms` integer,
	`bot_submitted_at` integer,
	`bot_correct` integer,
	`bot_elapsed_ms` integer,
	FOREIGN KEY (`room_id`) REFERENCES `arena_rooms`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `arena_round_number` ON `arena_rounds` (`room_id`,`number`);--> statement-breakpoint
CREATE INDEX `arena_round_room` ON `arena_rounds` (`room_id`);