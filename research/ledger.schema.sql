-- Research Ledger Database Schema
-- Purpose: Track experiments, runs, and outcomes for Station Calyx learning loop

-- Experiments table: Track experiment definitions and hypotheses
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    domain TEXT NOT NULL CHECK(domain IN ('planning', 'protocol', 'infrastructure', 'expansion')),
    metrics JSON NOT NULL,
    safety JSON NOT NULL,
    success_criteria TEXT NOT NULL,
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'approved', 'running', 'completed', 'failed')),
    owner TEXT NOT NULL,
    created_at REAL DEFAULT (julianday('now')),
    completed_at REAL,
    notes TEXT
);

-- Runs table: Track individual experiment executions
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exp_id TEXT NOT NULL,
    config JSON NOT NULL,
    result JSON,
    notes TEXT,
    status TEXT DEFAULT 'running' CHECK(status IN ('running', 'completed', 'failed', 'rolled_back')),
    started_at REAL DEFAULT (julianday('now')),
    completed_at REAL,
    FOREIGN KEY (exp_id) REFERENCES experiments(id)
);

-- Protocol RFCs table: Track protocol development artifacts
CREATE TABLE IF NOT EXISTS rfcs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    protocol_type TEXT NOT NULL,
    spec JSON NOT NULL,
    test_plan JSON,
    acceptance_criteria TEXT NOT NULL,
    status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'approved', 'canary', 'merged', 'rejected')),
    author TEXT NOT NULL,
    created_at REAL DEFAULT (julianday('now')),
    reviewed_at REAL,
    notes TEXT
);

-- Playbooks table: Track distilled procedures and lessons learned
CREATE TABLE IF NOT EXISTS playbooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    domain TEXT NOT NULL,
    procedure TEXT NOT NULL,
    preconditions TEXT,
    success_checks TEXT,
    created_at REAL DEFAULT (julianday('now')),
    last_used REAL,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0
);

-- Contradictions table: Track conflicting outputs across agents
CREATE TABLE IF NOT EXISTS contradictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL DEFAULT (julianday('now')),
    agent_1 TEXT NOT NULL,
    agent_2 TEXT NOT NULL,
    output_1 TEXT NOT NULL,
    output_2 TEXT NOT NULL,
    resolved BOOLEAN DEFAULT 0,
    resolution TEXT
);

-- Incident TTRC tracking table: Time-to-root-cause on incidents
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_type TEXT NOT NULL,
    detected_at REAL DEFAULT (julianday('now')),
    root_cause_identified_at REAL,
    resolution_at REAL,
    ttrc_minutes REAL,
    resolution_notes TEXT
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_exp_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_exp_domain ON experiments(domain);
CREATE INDEX IF NOT EXISTS idx_runs_exp ON runs(exp_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_rfcs_status ON rfcs(status);
CREATE INDEX IF NOT EXISTS idx_playbooks_domain ON playbooks(domain);
CREATE INDEX IF NOT EXISTS idx_incidents_type ON incidents(incident_type);

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at REAL DEFAULT (julianday('now'))
);

INSERT OR REPLACE INTO metadata (key, value) VALUES 
    ('schema_version', '1.0'),
    ('created_at', datetime('now')),
    ('last_compaction', datetime('now'));

