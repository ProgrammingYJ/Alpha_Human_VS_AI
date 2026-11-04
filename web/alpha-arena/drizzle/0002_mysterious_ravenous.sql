ALTER TABLE `arena_remote_rooms` ADD `engine_protocol` integer DEFAULT 1 NOT NULL;--> statement-breakpoint
ALTER TABLE `arena_rooms` ADD `start_request_id` text;--> statement-breakpoint
ALTER TABLE `arena_rooms` ADD `start_requested_at` integer;--> statement-breakpoint
ALTER TABLE `arena_rooms` ADD `start_expires_at` integer;--> statement-breakpoint
ALTER TABLE `arena_rooms` ADD `last_start_cancel_reason` text;