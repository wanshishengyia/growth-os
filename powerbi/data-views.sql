-- Growth OS - Power BI Data Views
-- Optimized SQL views for Power BI dashboard connections
-- Database: PostgreSQL (Supabase)

-- ============================================================
-- View: v_action_dashboard
-- Daily completion data with mood/energy for the last 90 days
-- Used by: Action Dashboard (行动看板)
-- ============================================================
CREATE OR REPLACE VIEW v_action_dashboard AS
SELECT 
  dl.log_date,
  dl.completed,
  dl.mood,
  dl.energy,
  dl.focus_minutes,
  dl.core_task,
  dl.ai_summary,
  dl.completion_quality,
  EXTRACT(DOW FROM dl.log_date) as day_of_week,
  g.title as goal_title,
  g.level as goal_level
FROM daily_logs dl
LEFT JOIN goals g ON dl.goal_id = g.id
WHERE dl.log_date >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY dl.log_date DESC;

-- ============================================================
-- View: v_asset_dashboard
-- Asset statistics for visualization
-- Used by: Asset Dashboard (资产看板)
-- ============================================================
CREATE OR REPLACE VIEW v_asset_dashboard AS
SELECT 
  a.id,
  a.type,
  a.title,
  a.quality,
  a.reuse_count,
  a.tags,
  a.created_at::date as created_date,
  DATE_TRUNC('month', a.created_at) as month,
  g.title as related_goal
FROM assets a
LEFT JOIN goals g ON a.related_goal_id = g.id
ORDER BY a.created_at DESC;

-- ============================================================
-- View: v_cognition_dashboard
-- Insight statistics
-- Used by: Cognition Dashboard (认知看板)
-- ============================================================
CREATE OR REPLACE VIEW v_cognition_dashboard AS
SELECT 
  i.id,
  i.type,
  i.content,
  i.confidence,
  i.validated_count,
  i.tags,
  i.created_at::date as created_date,
  DATE_TRUNC('month', i.created_at) as month
FROM insights i
ORDER BY i.created_at DESC;

-- ============================================================
-- View: v_life_dashboard
-- Goal progress and review timeline
-- Used by: Life Dashboard (主线看板)
-- ============================================================
CREATE OR REPLACE VIEW v_life_dashboard AS
SELECT 
  g.id,
  g.title,
  g.level,
  g.status,
  g.progress,
  g.start_date,
  g.end_date,
  g.tags,
  (SELECT COUNT(*) FROM assets WHERE related_goal_id = g.id) as asset_count,
  (SELECT COUNT(*) FROM daily_logs WHERE goal_id = g.id AND completed = true) as completed_days
FROM goals g
WHERE g.deleted_at IS NULL
ORDER BY g.level, g.created_at;

-- ============================================================
-- View: v_monthly_trends
-- Monthly aggregated metrics for trend analysis
-- Used by: All dashboards (cross-cutting trends)
-- ============================================================
CREATE OR REPLACE VIEW v_monthly_trends AS
SELECT 
  DATE_TRUNC('month', dl.log_date) as month,
  COUNT(*) as total_days,
  SUM(CASE WHEN dl.completed THEN 1 ELSE 0 END) as completed_days,
  ROUND(AVG(dl.mood), 1) as avg_mood,
  ROUND(AVG(dl.energy), 1) as avg_energy,
  SUM(dl.focus_minutes) as total_focus_minutes,
  (SELECT COUNT(*) FROM assets WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', dl.log_date)) as new_assets,
  (SELECT COUNT(*) FROM insights WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', dl.log_date)) as new_insights
FROM daily_logs dl
GROUP BY DATE_TRUNC('month', dl.log_date)
ORDER BY month DESC;

-- ============================================================
-- View: v_streak_calc
-- Current streak calculation
-- Used by: Action Dashboard KPI card
-- ============================================================
CREATE OR REPLACE VIEW v_streak_calc AS
WITH ranked AS (
  SELECT 
    log_date,
    completed,
    log_date - ROW_NUMBER() OVER (ORDER BY log_date DESC) * INTERVAL '1 day' as grp
  FROM daily_logs
  WHERE completed = true
  ORDER BY log_date DESC
)
SELECT 
  MIN(log_date) as streak_start,
  MAX(log_date) as streak_end,
  COUNT(*) as streak_days
FROM ranked
WHERE grp = (SELECT grp FROM ranked LIMIT 1)
GROUP BY grp;
