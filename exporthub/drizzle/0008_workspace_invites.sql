CREATE TABLE IF NOT EXISTS workspace_invites (email TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role IN ('editor','viewer')), invited_by TEXT NOT NULL, created_at TEXT NOT NULL);
