CREATE TABLE IF NOT EXISTS code_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES exam_sessions(id),
    FOREIGN KEY (question_id) REFERENCES questions(question_id),

    UNIQUE(session_id, question_id, version)
);

CREATE INDEX IF NOT EXISTS idx_code_snapshots_session_id
ON code_snapshots(session_id);
