-- Growth OS - Initial Schema (SQLite)
-- All IDs are TEXT (UUID hex strings)
-- All timestamps are TEXT (ISO 8601)
-- All JSON fields are TEXT (JSON strings)

-- ============================================================
-- 1. goals - hierarchical goal tree (year/quarter/month/week/stage)
-- ============================================================
CREATE TABLE IF NOT EXISTS goals (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    level       TEXT NOT NULL CHECK (level IN ('year','quarter','month','week','stage')),
    parent_id   TEXT REFERENCES goals(id) ON DELETE SET NULL,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','done','abandoned')),
    priority    INTEGER NOT NULL DEFAULT 3 CHECK (priority >= 1 AND priority <= 5),
    start_date  TEXT,
    end_date    TEXT,
    progress    REAL DEFAULT 0.0 CHECK (progress >= 0 AND progress <= 100),
    tags        TEXT DEFAULT '[]',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    deleted_at  TEXT
);

-- ============================================================
-- 2. daily_logs - daily check-in / journal entries
-- ============================================================
CREATE TABLE IF NOT EXISTS daily_logs (
    id                TEXT PRIMARY KEY,
    log_date          TEXT NOT NULL UNIQUE,
    goal_id           TEXT REFERENCES goals(id) ON DELETE SET NULL,
    core_task         TEXT,
    min_action        TEXT,
    judge_criteria    TEXT,
    completed         INTEGER DEFAULT 0,
    completion_quality INTEGER CHECK (completion_quality >= 1 AND completion_quality <= 5),
    mood              INTEGER CHECK (mood >= 1 AND mood <= 5),
    energy            INTEGER CHECK (energy >= 1 AND energy <= 5),
    focus_minutes     INTEGER DEFAULT 0,
    raw_notes         TEXT,
    ai_summary        TEXT,
    ai_problem        TEXT,
    ai_next_action    TEXT,
    tags              TEXT DEFAULT '[]',
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- ============================================================
-- 3. insights - AI-generated or user-created insights
-- ============================================================
CREATE TABLE IF NOT EXISTS insights (
    id                TEXT PRIMARY KEY,
    type              TEXT NOT NULL CHECK (type IN ('question','insight','principle','model')),
    content           TEXT NOT NULL,
    context           TEXT,
    source_type       TEXT CHECK (source_type IN ('daily_log','review','manual','external')),
    source_id         TEXT,
    confidence        INTEGER DEFAULT 3 CHECK (confidence >= 1 AND confidence <= 5),
    validated_count   INTEGER DEFAULT 0,
    tags              TEXT DEFAULT '[]',
    related_goal_ids  TEXT DEFAULT '[]',
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- ============================================================
-- 4. assets - digital assets / artifacts produced during growth
-- ============================================================
CREATE TABLE IF NOT EXISTS assets (
    id                 TEXT PRIMARY KEY,
    type               TEXT NOT NULL CHECK (type IN ('project','method','template','output','snippet')),
    title              TEXT NOT NULL,
    content            TEXT,
    file_path          TEXT,
    url                TEXT,
    quality            INTEGER DEFAULT 3 CHECK (quality >= 1 AND quality <= 5),
    reuse_count        INTEGER DEFAULT 0,
    tags               TEXT DEFAULT '[]',
    ai_classification  TEXT,
    related_goal_id    TEXT REFERENCES goals(id) ON DELETE SET NULL,
    related_log_id     TEXT REFERENCES daily_logs(id) ON DELETE SET NULL,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);

-- ============================================================
-- 5. reviews - periodic reviews (day/week/month/quarter)
-- ============================================================
CREATE TABLE IF NOT EXISTS reviews (
    id                  TEXT PRIMARY KEY,
    period              TEXT NOT NULL CHECK (period IN ('day','week','month','quarter')),
    start_date          TEXT NOT NULL,
    end_date            TEXT NOT NULL,
    highlights          TEXT,
    problems            TEXT,
    next_actions        TEXT,
    ai_pattern_analysis TEXT,
    ai_questions        TEXT,
    completion_rate     REAL,
    asset_count         INTEGER DEFAULT 0,
    insight_count       INTEGER DEFAULT 0,
    created_at          TEXT NOT NULL,
    UNIQUE(period, start_date)
);

-- ============================================================
-- 6. environment_rules - environment / habit rules to enforce
-- ============================================================
CREATE TABLE IF NOT EXISTS environment_rules (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    type             TEXT CHECK (type IN ('block','remind','trigger','filter')),
    target           TEXT,
    condition        TEXT,
    action           TEXT,
    active           INTEGER DEFAULT 1,
    last_triggered_at TEXT,
    trigger_count    INTEGER DEFAULT 0,
    created_at       TEXT NOT NULL
);

-- ============================================================
-- 7. ai_interactions - log every AI call for cost tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_interactions (
    id              TEXT PRIMARY KEY,
    agent_name      TEXT NOT NULL,
    prompt_version  TEXT,
    input           TEXT NOT NULL,
    output          TEXT,
    model           TEXT,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    cost_usd        REAL,
    latency_ms      INTEGER,
    status          TEXT CHECK (status IN ('success','error','timeout')),
    error_message   TEXT,
    related_table   TEXT,
    related_id      TEXT,
    created_at      TEXT NOT NULL
);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_goals_status     ON goals(status);
CREATE INDEX IF NOT EXISTS idx_goals_level      ON goals(level);
CREATE INDEX IF NOT EXISTS idx_goals_parent     ON goals(parent_id);
CREATE INDEX IF NOT EXISTS idx_goals_deleted    ON goals(deleted_at);

CREATE INDEX IF NOT EXISTS idx_daily_logs_date      ON daily_logs(log_date);
CREATE INDEX IF NOT EXISTS idx_daily_logs_goal      ON daily_logs(goal_id);
CREATE INDEX IF NOT EXISTS idx_daily_logs_completed ON daily_logs(completed);

CREATE INDEX IF NOT EXISTS idx_insights_type    ON insights(type);
CREATE INDEX IF NOT EXISTS idx_insights_conf    ON insights(confidence);

CREATE INDEX IF NOT EXISTS idx_assets_type      ON assets(type);
CREATE INDEX IF NOT EXISTS idx_assets_goal      ON assets(related_goal_id);
CREATE INDEX IF NOT EXISTS idx_assets_log       ON assets(related_log_id);

CREATE INDEX IF NOT EXISTS idx_reviews_period   ON reviews(period, start_date);

CREATE INDEX IF NOT EXISTS idx_rules_active     ON environment_rules(active);

CREATE INDEX IF NOT EXISTS idx_ai_agent_time    ON ai_interactions(agent_name, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_status        ON ai_interactions(status);
