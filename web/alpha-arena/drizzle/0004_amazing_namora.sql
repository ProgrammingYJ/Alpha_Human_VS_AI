ALTER TABLE `arena_rounds` ADD `image_load_id` text;--> statement-breakpoint
ALTER TABLE `arena_rounds` ADD `loading_expires_at` integer;--> statement-breakpoint
ALTER TABLE `arena_rounds` ADD `human_images_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `arena_rounds` ADD `bot_images_ready` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `arena_rounds` ADD `engine_images_ready` integer DEFAULT 0 NOT NULL;