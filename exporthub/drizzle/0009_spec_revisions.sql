CREATE TABLE IF NOT EXISTS spec_revisions (
 spec_id TEXT PRIMARY KEY NOT NULL REFERENCES specs(id),
 root_id TEXT NOT NULL REFERENCES specs(id),
 revision INTEGER NOT NULL CHECK(revision >= 1 AND revision <= 500),
 sha256 TEXT NOT NULL CHECK(sha256 = '' OR (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*')),
 issued_on TEXT NOT NULL DEFAULT '', valid_until TEXT NOT NULL DEFAULT '', change_note TEXT NOT NULL,
 UNIQUE(root_id,revision)
);
