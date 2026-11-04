CREATE TABLE `arena_remote_rooms` (
	`room_id` text PRIMARY KEY NOT NULL,
	`lane` text NOT NULL,
	`engine_token_hash` text,
	`engine_seen_at` integer,
	`engine_stage` text DEFAULT 'disconnected' NOT NULL,
	`engine_ready` integer DEFAULT 0 NOT NULL,
	`selected_json` text DEFAULT '[]' NOT NULL,
	`sequence` integer DEFAULT 0 NOT NULL,
	`last_selection_at` integer,
	FOREIGN KEY (`room_id`) REFERENCES `arena_rooms`(`id`) ON UPDATE no action ON DELETE no action
);
