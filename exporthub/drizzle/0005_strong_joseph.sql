CREATE TABLE `sector_files` (
	`id` text PRIMARY KEY NOT NULL,
	`record_id` text NOT NULL,
	`filename` text NOT NULL,
	`size` integer NOT NULL,
	`created_at` text NOT NULL,
	`created_by` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_sector_files_record` ON `sector_files` (`record_id`);