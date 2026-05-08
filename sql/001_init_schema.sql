-- Growth OS - Initial Schema
-- PostgreSQL with Supabase

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- Utility: auto-update updated_at timestamp
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 1. goals - hierarchical goal tree (yearly / monthly / weekly / daily)
-- ============================================================
CREATE TABLE goals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    description TEXT,
    level       TEXT NOT NULL CHECK (level IN ('yearly','monthly','weekly','daily')),
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','paused','cancelled')),
    parent_id   UUID REFERENCES goals(id) ON DELETE SET NULL,
    start_date  DATE,
    due_date    DATE,
    progress    SMALLINT DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    tags        JSONB DEFAULT '[]'::JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. daily_logs - daily check-in / journal entries
-- ============================================================
CREATE TABLE daily_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    log_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    mood        SMALLINT CHECK (mood >= 1 AND mood <= 5),
    energy      SMALLINT CHECK (energy >= 1 AND energy <= 5),
    content     TEXT,
    completed   JSONB DEFAULT '[]'::JSONB,
    goal_id     UUID REFERENCES goals(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. insights - AI-generated or user-created insights
-- ============================================================
CREATE TABLE insights (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type        TEXT NOT NULL CHECK (type IN ('pattern','recommendation','summary','milestone')),
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    source      TEXT DEFAULT 'ai',
    tags        JSONB DEFAULT '[]'::JSONB,
    related_goal_id UUID REFERENCES goals(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 4. assets - digital assets / artifacts produced during growth
-- ============================================================
CREATE TABLE assets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    type        TEXT NOT NULL CHECK (type IN ('document','template','checklist','note','link','media')),
    content     TEXT,
    url         TEXT,
    tags        JSONB DEFAULT '[]'::JSONB,
    goal_id     UUID REFERENCES goals(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 5. reviews - periodic reviews (weekly / monthly / quarterly)
-- ============================================================
CREATE TABLE reviews (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period      TEXT NOT NULL CHECK (period IN ('weekly','monthly','quarterly','yearly')),
    period_start DATE NOT NULL,
    period_end   DATE NOT NULL,
    summary     TEXT NOT NULL,
    highlights  JSONB DEFAULT '[]'::JSONB,
    improvements JSONB DEFAULT '[]'::JSONB,
    score       SMALLINT CHECK (score >= 1 AND score <= 10),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 6. environment_rules - environment / habit rules to enforce
-- ============================================================
CREATE TABLE environment_rules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT,
    rule_type   TEXT NOT NULL CHECK (rule_type IN ('time_block','habit','constraint','reminder')),
    config      JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 7. ai_interactions - log every AI call for cost tracking
-- ============================================================
CREATE TABLE ai_interactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent           TEXT NOT NULL,
    prompt_tokens   INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd        NUMERIC(10,6) NOT NULL DEFAULT 0,
    model           TEXT,
    request_summary TEXT,
    response_summary TEXT,
    status          TEXT NOT NULL DEFAULT 'success' CHECK (status IN ('success','error','timeout')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX idx_goals_status    ON goals(status);
CREATE INDEX idx_goals_level     ON goals(level);
CREATE INDEX idx_goals_parent    ON goals(parent_id);

CREATE INDEX idx_daily_logs_date     ON daily_logs(log_date);
CREATE INDEX idx_daily_logs_goal     ON daily_logs(goal_id);
CREATE INDEX idx_daily_logs_completed ON daily_logs USING GIN (completed);

CREATE INDEX idx_insights_type   ON insights(type);
CREATE INDEX idx_insights_tags   ON insights USING GIN (tags);

CREATE INDEX idx_assets_type     ON assets(type);
CREATE INDEX idx_assets_tags     ON assets USING GIN (tags);
CREATE INDEX idx_assets_goal     ON assets(goal_id);

CREATE INDEX idx_reviews_period  ON reviews(period, period_start);

CREATE INDEX idx_rules_active    ON environment_rules(is_active);

CREATE INDEX idx_ai_agent_time   ON ai_interactions(agent, created_at);
CREATE INDEX idx_ai_status       ON ai_interactions(status);

-- ============================================================
-- Triggers: auto-update updated_at
-- ============================================================
CREATE TRIGGER trg_goals_updated_at
    BEFORE UPDATE ON goals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_daily_logs_updated_at
    BEFORE UPDATE ON daily_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_insights_updated_at
    BEFORE UPDATE ON insights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_assets_updated_at
    BEFORE UPDATE ON assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_reviews_updated_at
    BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_environment_rules_updated_at
    BEFORE UPDATE ON environment_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_ai_interactions_updated_at
    BEFORE UPDATE ON ai_interactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
