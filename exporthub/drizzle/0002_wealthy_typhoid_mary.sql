CREATE TABLE `collection_chunks` (
	`batch_id` text NOT NULL,
	`ordinal` integer NOT NULL,
	`content` text NOT NULL,
	PRIMARY KEY(`batch_id`, `ordinal`)
);
