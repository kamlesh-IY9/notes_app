-- Notes Generator — SQLite Schema
-- Stores jobs, entries, and dedup registry

CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending, running, paused, completed, failed, cancelled
    batch_size  INTEGER NOT NULL,
    config      TEXT NOT NULL,  -- JSON blob of generation config
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    started_at  TEXT,
    completed_at TEXT,
    -- counters
    total       INTEGER NOT NULL DEFAULT 0,
    generated   INTEGER NOT NULL DEFAULT 0,
    accepted    INTEGER NOT NULL DEFAULT 0,
    rejected    INTEGER NOT NULL DEFAULT 0,
    failed      INTEGER NOT NULL DEFAULT 0,
    retried     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS entries (
    id              TEXT PRIMARY KEY,
    job_id          TEXT NOT NULL REFERENCES jobs(id),
    entry_num       INTEGER NOT NULL,  -- sequential within job
    global_id       INTEGER NOT NULL,  -- global ID (1100, 1101, ...)
    part_num        INTEGER NOT NULL,  -- PART number
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending, generating, accepted, rejected, failed
    -- persona (internal only, never exported)
    persona_json    TEXT,
    -- note content
    note_text       TEXT,
    has_title       INTEGER NOT NULL DEFAULT 1,  -- boolean
    title           TEXT,
    -- metadata (internal)
    app_type        TEXT,  -- apple_notes, google_keep, samsung_notes
    theme           TEXT,  -- light, dark
    connectivity    TEXT,  -- wifi_cellular, cellular_only, wifi_only, no_service
    note_date       TEXT,  -- ISO datetime for the note
    relationship    TEXT,
    topic           TEXT,
    mood            TEXT,
    word_count      INTEGER,
    line_count      INTEGER,
    -- file paths
    txt_filename    TEXT,
    jpg_filename    TEXT,
    txt_path        TEXT,
    jpg_path        TEXT,
    -- validation
    validation_json TEXT,  -- JSON array of check results
    retry_count     INTEGER NOT NULL DEFAULT 0,
    -- dedup
    embedding       BLOB,  -- numpy array bytes
    -- language / localisation
    language        TEXT NOT NULL DEFAULT 'english',  -- 'english' or 'hindi'
    note_text_en    TEXT,  -- English source (set for Hindi jobs; NULL for English jobs)
    -- timestamps
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_entries_job ON entries(job_id);
CREATE INDEX IF NOT EXISTS idx_entries_status ON entries(status);
CREATE INDEX IF NOT EXISTS idx_entries_global_id ON entries(global_id);

-- Dedup registry: tracks used names, titles, 3-grams, combos
CREATE TABLE IF NOT EXISTS dedup_registry (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id    TEXT REFERENCES entries(id),
    -- uniqueness fields
    full_name       TEXT,
    normalized_title TEXT,
    opening_trigram TEXT,
    rel_topic_mood  TEXT,  -- "relationship|topic|mood"
    -- timestamps
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_dedup_name ON dedup_registry(full_name);
CREATE INDEX IF NOT EXISTS idx_dedup_title ON dedup_registry(normalized_title);
CREATE INDEX IF NOT EXISTS idx_dedup_trigram ON dedup_registry(opening_trigram);
CREATE INDEX IF NOT EXISTS idx_dedup_combo ON dedup_registry(rel_topic_mood);

-- Checkpoint: tracks generation progress for resume
CREATE TABLE IF NOT EXISTS checkpoints (
    job_id      TEXT PRIMARY KEY REFERENCES jobs(id),
    last_entry  INTEGER NOT NULL DEFAULT 0,
    next_global_id INTEGER NOT NULL DEFAULT 1100,
    next_part   INTEGER NOT NULL DEFAULT 32,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
