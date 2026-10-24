CREATE TABLE `audit_events` (
	`id` text PRIMARY KEY NOT NULL,
	`at` text NOT NULL,
	`user_id` text NOT NULL,
	`actor` text NOT NULL,
	`action` text NOT NULL,
	`resource_type` text NOT NULL,
	`resource_id` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_audit_events_at` ON `audit_events` (`at`);