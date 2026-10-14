CREATE TABLE `write_guards` (
	`id` text PRIMARY KEY NOT NULL,
	`valid` integer NOT NULL,
	CONSTRAINT "write_revision_guard" CHECK("write_guards"."valid" = 1)
);
