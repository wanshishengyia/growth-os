-- Growth OS - Views

-- ============================================================
-- 1. v_daily_completion_30d — daily completion rate over last 30 days
-- ============================================================
CREATE OR REPLACE VIEW v_daily_completion_30d AS
SELECT
    log_date,
    COUNT(*)                                          AS total_entries,
    COUNT(*) FILTER (WHERE completed IS NOT NULL
                          AND jsonb_array_length(completed) > 0) AS entries_with_tasks,
    COALESCE(SUM(
        (SELECT COUNT(*) FROM jsonb_array_elements(completed))
    ), 0)                                             AS total_tasks,
    COALESCE(SUM(
        (SELECT COUNT(*) FROM jsonb_array_elements(completed)
         WHERE value->>'done' = 'true')
    ), 0)                                             AS completed_tasks,
    CASE
        WHEN COALESCE(SUM(
            (SELECT COUNT(*) FROM jsonb_array_elements(completed))
        ), 0) > 0
        THEN ROUND(
            COALESCE(SUM(
                (SELECT COUNT(*) FROM jsonb_array_elements(completed)
                 WHERE value->>'done' = 'true')
            ), 0)::NUMERIC
            / SUM((SELECT COUNT(*) FROM jsonb_array_elements(completed))) * 100, 1)
        ELSE 0
    END                                               AS completion_rate
FROM daily_logs
WHERE log_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY log_date
ORDER BY log_date DESC;

-- ============================================================
-- 2. v_monthly_assets — asset count grouped by month and type
-- ============================================================
CREATE OR REPLACE VIEW v_monthly_assets AS
SELECT
    DATE_TRUNC('month', created_at)::DATE AS month,
    type,
    COUNT(*) AS asset_count
FROM assets
GROUP BY DATE_TRUNC('month', created_at), type
ORDER BY month DESC, type;

-- ============================================================
-- 3. v_monthly_ai_cost — monthly AI spend breakdown
-- ============================================================
CREATE OR REPLACE VIEW v_monthly_ai_cost AS
SELECT
    DATE_TRUNC('month', created_at)::DATE AS month,
    agent,
    COUNT(*)                               AS total_calls,
    SUM(prompt_tokens)                     AS total_prompt_tokens,
    SUM(completion_tokens)                 AS total_completion_tokens,
    ROUND(SUM(cost_usd)::NUMERIC, 4)      AS total_cost_usd
FROM ai_interactions
GROUP BY DATE_TRUNC('month', created_at), agent
ORDER BY month DESC, total_cost_usd DESC;

-- ============================================================
-- 4. v_weekly_summary — compact weekly overview
-- ============================================================
CREATE OR REPLACE VIEW v_weekly_summary AS
SELECT
    DATE_TRUNC('week', dl.log_date)::DATE          AS week_start,
    COUNT(DISTINCT dl.log_date)                    AS days_logged,
    ROUND(AVG(dl.mood), 1)                         AS avg_mood,
    ROUND(AVG(dl.energy), 1)                       AS avg_energy,
    COUNT(DISTINCT dl.goal_id)                     AS goals_touched,
    (SELECT COUNT(*) FROM insights i
     WHERE i.created_at >= DATE_TRUNC('week', dl.log_date)
       AND i.created_at <  DATE_TRUNC('week', dl.log_date) + INTERVAL '7 days'
    )                                              AS insights_count,
    (SELECT COUNT(*) FROM assets a
     WHERE a.created_at >= DATE_TRUNC('week', dl.log_date)
       AND a.created_at <  DATE_TRUNC('week', dl.log_date) + INTERVAL '7 days'
    )                                              AS assets_count
FROM daily_logs dl
GROUP BY DATE_TRUNC('week', dl.log_date)
ORDER BY week_start DESC;
