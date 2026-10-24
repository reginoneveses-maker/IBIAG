CREATE TABLE IF NOT EXISTS workspace_members (user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL CHECK(role IN ('owner','editor','viewer')), created_at TEXT NOT NULL);
