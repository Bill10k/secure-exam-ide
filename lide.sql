CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    lti_user_id TEXT UNIQUE,
    name TEXT,
    email TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE exams (
    exam_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE questions (
    question_id TEXT PRIMARY KEY,
    exam_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    max_score REAL DEFAULT 1.0,

    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE
);
CREATE TABLE test_cases (
    test_case_id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    input TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_hidden BOOLEAN DEFAULT 1,
    weight REAL DEFAULT 1.0,

    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    exam_id TEXT NOT NULL,
    start_time DATETIME,
    end_time DATETIME,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'synced', 'failed')),

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE
);
CREATE TABLE submissions (
    submission_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    code TEXT NOT NULL,
    score REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,

    UNIQUE(session_id, question_id)
);
CREATE TABLE executions (
    execution_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    stdout TEXT,
    stderr TEXT,
    exit_code INTEGER,
    execution_time REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);
CREATE TABLE activity_logs (
    log_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
CREATE TABLE code_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    code TEXT NOT NULL,
    version INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE,

    UNIQUE(session_id, question_id, version)
);
CREATE TABLE sync_queue (
    sync_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL, -- INSERT, UPDATE, DELETE
    payload TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'synced', 'failed')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_sessions_user_id 
ON sessions(user_id);

CREATE INDEX idx_sessions_exam_id 
ON sessions(exam_id);

CREATE INDEX idx_submissions_session_id 
ON submissions(session_id);

CREATE INDEX idx_submissions_question_id 
ON submissions(question_id);

CREATE INDEX idx_activity_logs_session_id 
ON activity_logs(session_id);

CREATE INDEX idx_executions_session_id 
ON executions(session_id);

CREATE INDEX idx_executions_question_id 
ON executions(question_id);

CREATE INDEX idx_test_cases_question_id 
ON test_cases(question_id);

CREATE INDEX idx_snapshots_session_id 
ON code_snapshots(session_id);