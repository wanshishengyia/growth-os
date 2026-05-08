"""Database service layer for Growth OS.

All SQLite CRUD operations live here.  Every public method is ``async`` – the
sqlite3 client is synchronous, so we delegate to ``asyncio.to_thread`` to keep
the FastAPI event-loop non-blocking.  A ``threading.Lock`` serialises access
to the shared connection so concurrent ``to_thread`` calls are safe.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from backend.app.models.ai_interaction import AIInteractionCreate
from backend.app.models.asset import AssetCreate
from backend.app.models.daily_log import DailyLogCreate
from backend.app.models.environment_rule import EnvironmentRuleCreate
from backend.app.models.goal import GoalCreate, GoalUpdate
from backend.app.models.insight import InsightCreate
from backend.app.models.review import ReviewCreate
from backend.app.models.responses import DashboardStats
from backend.app.services.supabase_client import get_connection

logger = logging.getLogger(__name__)

# ── Serialisation helpers ─────────────────────────────────────────────────

_db_lock = threading.Lock()

# Fields stored as JSON text per table (deserialised on read)
_JSON_FIELDS: dict[str, set[str]] = {
    "goals": {"tags"},
    "daily_logs": {"tags"},
    "insights": {"tags", "related_goal_ids"},
    "assets": {"tags", "ai_classification"},
    "reviews": {"ai_pattern_analysis", "ai_questions"},
    "environment_rules": {"condition", "action"},
    "ai_interactions": {"input", "output"},
}

# Fields stored as INTEGER but representing booleans
_BOOL_FIELDS: dict[str, set[str]] = {
    "daily_logs": {"completed"},
    "environment_rules": {"active"},
}


def _serialize(data: dict) -> dict:
    """Convert Pydantic-style values into SQLite-compatible primitives.

    * UUID → str
    * date/datetime → ISO-8601 string
    * bool → int (0/1)
    * list → JSON string
    * dict → JSON string
    * Enum → .value
    """
    out: dict[str, Any] = {}
    for k, v in data.items():
        if v is None:
            out[k] = None
        elif isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        elif isinstance(v, bool):
            out[k] = int(v)
        elif isinstance(v, list):
            processed = [str(i) if isinstance(i, uuid.UUID) else i for i in v]
            out[k] = json.dumps(processed, ensure_ascii=False)
        elif isinstance(v, dict):
            out[k] = json.dumps(v, ensure_ascii=False, default=str)
        elif hasattr(v, "value"):  # Enum
            out[k] = v.value
        else:
            out[k] = v
    return out


def _row_to_dict(row, table: str = "") -> dict:
    """Convert a ``sqlite3.Row`` to a plain dict.

    JSON-encoded fields are parsed back into Python objects; boolean fields
    are converted from int back to ``bool``.
    """
    d = dict(row)
    for field in _JSON_FIELDS.get(table, set()):
        if field in d and d[field] is not None:
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    for field in _BOOL_FIELDS.get(table, set()):
        if field in d and d[field] is not None:
            d[field] = bool(d[field])
    return d


# ── Service ───────────────────────────────────────────────────────────────


class DBService:
    """Thin data-access layer backed by SQLite."""

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._conn = get_connection()

    # helper – run blocking call in a thread, serialised by lock
    async def _run(self, fn, *args, **kwargs):
        def _locked():
            with _db_lock:
                return fn(*args, **kwargs)
        return await asyncio.to_thread(_locked)

    # ==================================================================
    # GOALS
    # ==================================================================

    async def create_goal(self, data: GoalCreate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        goal_id = uuid.uuid4().hex
        payload = _serialize(data.model_dump())
        payload["id"] = goal_id
        payload["created_at"] = now
        payload["updated_at"] = now

        def _do():
            self._conn.execute(
                """INSERT INTO goals
                   (id, title, description, level, parent_id, status, priority,
                    start_date, end_date, progress, tags, created_at, updated_at)
                VALUES
                   (:id, :title, :description, :level, :parent_id, :status, :priority,
                    :start_date, :end_date, :progress, :tags, :created_at, :updated_at)""",
                payload,
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()
            return _row_to_dict(row, "goals") if row else None

        return await self._run(_do)

    async def get_goals(
        self,
        status: str | None = None,
        level: str | None = None,
        parent_id: str | None = None,
    ) -> list[dict]:
        conditions = ["deleted_at IS NULL"]
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if level:
            conditions.append("level = ?")
            params.append(level)
        if parent_id:
            conditions.append("parent_id = ?")
            params.append(parent_id)
        where = " AND ".join(conditions)
        sql = f"SELECT * FROM goals WHERE {where} ORDER BY created_at DESC"

        def _do():
            rows = self._conn.execute(sql, params).fetchall()
            return [_row_to_dict(r, "goals") for r in rows]

        return await self._run(_do)

    async def get_goal(self, goal_id: str) -> dict | None:
        def _do():
            row = self._conn.execute(
                "SELECT * FROM goals WHERE id = ? AND deleted_at IS NULL",
                (goal_id,),
            ).fetchone()
            return _row_to_dict(row, "goals") if row else None

        return await self._run(_do)

    async def update_goal(self, goal_id: str, data: GoalUpdate) -> dict:
        payload = _serialize(data.model_dump(exclude_unset=True))
        if not payload:
            return await self.get_goal(goal_id)
        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in payload)
        values = list(payload.values()) + [goal_id]
        sql = f"UPDATE goals SET {set_clause} WHERE id = ?"

        def _do():
            self._conn.execute(sql, values)
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM goals WHERE id = ?", (goal_id,)
            ).fetchone()
            return _row_to_dict(row, "goals") if row else None

        return await self._run(_do)

    async def delete_goal(self, goal_id: str) -> None:
        """Soft-delete: set deleted_at to now."""
        now = datetime.now(timezone.utc).isoformat()

        def _do():
            self._conn.execute(
                "UPDATE goals SET deleted_at = ?, updated_at = ? WHERE id = ?",
                (now, now, goal_id),
            )
            self._conn.commit()

        await self._run(_do)

    # ==================================================================
    # DAILY LOGS
    # ==================================================================

    async def create_daily_log(self, data: DailyLogCreate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        log_id = uuid.uuid4().hex
        payload = _serialize(data.model_dump())
        payload["id"] = log_id
        payload["created_at"] = now
        payload["updated_at"] = now

        def _do():
            self._conn.execute(
                """INSERT INTO daily_logs
                   (id, log_date, goal_id, core_task, min_action, judge_criteria,
                    completed, completion_quality, mood, energy, focus_minutes,
                    raw_notes, ai_summary, ai_problem, ai_next_action, tags,
                    created_at, updated_at)
                VALUES
                   (:id, :log_date, :goal_id, :core_task, :min_action, :judge_criteria,
                    :completed, :completion_quality, :mood, :energy, :focus_minutes,
                    :raw_notes, :ai_summary, :ai_problem, :ai_next_action, :tags,
                    :created_at, :updated_at)""",
                payload,
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM daily_logs WHERE log_date = ?",
                (data.log_date.isoformat(),),
            ).fetchone()
            return _row_to_dict(row, "daily_logs") if row else None

        return await self._run(_do)

    async def get_daily_log_by_date(self, log_date: date) -> dict | None:
        def _do():
            row = self._conn.execute(
                "SELECT * FROM daily_logs WHERE log_date = ?",
                (log_date.isoformat(),),
            ).fetchone()
            return _row_to_dict(row, "daily_logs") if row else None

        return await self._run(_do)

    async def update_daily_log(self, log_id: str, data: dict) -> dict:
        payload = _serialize(data)
        if not payload:
            def _fetch():
                row = self._conn.execute(
                    "SELECT * FROM daily_logs WHERE id = ?", (log_id,)
                ).fetchone()
                return _row_to_dict(row, "daily_logs") if row else None
            return await self._run(_fetch)

        payload["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in payload)
        values = list(payload.values()) + [log_id]
        sql = f"UPDATE daily_logs SET {set_clause} WHERE id = ?"

        def _do():
            self._conn.execute(sql, values)
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM daily_logs WHERE id = ?", (log_id,)
            ).fetchone()
            return _row_to_dict(row, "daily_logs") if row else None

        return await self._run(_do)

    async def get_daily_logs(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 30,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[Any] = []
        if start_date:
            conditions.append("log_date >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("log_date <= ?")
            params.append(end_date.isoformat())
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM daily_logs{where} ORDER BY log_date DESC LIMIT ?"
        params.append(limit)

        def _do():
            rows = self._conn.execute(sql, params).fetchall()
            return [_row_to_dict(r, "daily_logs") for r in rows]

        return await self._run(_do)

    async def get_yesterday_log(self) -> dict | None:
        yesterday = date.today() - timedelta(days=1)
        return await self.get_daily_log_by_date(yesterday)

    # ==================================================================
    # INSIGHTS
    # ==================================================================

    async def create_insight(self, data: InsightCreate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        insight_id = uuid.uuid4().hex
        payload = _serialize(data.model_dump())
        payload["id"] = insight_id
        payload["created_at"] = now
        payload["updated_at"] = now

        def _do():
            self._conn.execute(
                """INSERT INTO insights
                   (id, type, content, context, source_type, source_id,
                    confidence, validated_count, tags, related_goal_ids,
                    created_at, updated_at)
                VALUES
                   (:id, :type, :content, :context, :source_type, :source_id,
                    :confidence, :validated_count, :tags, :related_goal_ids,
                    :created_at, :updated_at)""",
                payload,
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM insights WHERE id = ?", (insight_id,)
            ).fetchone()
            return _row_to_dict(row, "insights") if row else None

        return await self._run(_do)

    async def get_insights(
        self,
        type: str | None = None,
        min_confidence: int | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[Any] = []
        if type:
            conditions.append("type = ?")
            params.append(type)
        if min_confidence is not None:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        if tag:
            # JSON array search via json_each
            conditions.append(
                "EXISTS (SELECT 1 FROM json_each(insights.tags) WHERE json_each.value = ?)"
            )
            params.append(tag)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM insights{where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        def _do():
            rows = self._conn.execute(sql, params).fetchall()
            return [_row_to_dict(r, "insights") for r in rows]

        return await self._run(_do)

    async def get_insight(self, insight_id: str) -> dict | None:
        def _do():
            row = self._conn.execute(
                "SELECT * FROM insights WHERE id = ?", (insight_id,)
            ).fetchone()
            return _row_to_dict(row, "insights") if row else None

        return await self._run(_do)

    # ==================================================================
    # ASSETS
    # ==================================================================

    async def create_asset(self, data: AssetCreate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        asset_id = uuid.uuid4().hex
        payload = _serialize(data.model_dump())
        payload["id"] = asset_id
        payload["created_at"] = now
        payload["updated_at"] = now

        def _do():
            self._conn.execute(
                """INSERT INTO assets
                   (id, type, title, content, file_path, url, quality,
                    reuse_count, tags, ai_classification,
                    related_goal_id, related_log_id, created_at, updated_at)
                VALUES
                   (:id, :type, :title, :content, :file_path, :url, :quality,
                    :reuse_count, :tags, :ai_classification,
                    :related_goal_id, :related_log_id, :created_at, :updated_at)""",
                payload,
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM assets WHERE id = ?", (asset_id,)
            ).fetchone()
            return _row_to_dict(row, "assets") if row else None

        return await self._run(_do)

    async def get_assets(
        self,
        type: str | None = None,
        tag: str | None = None,
        related_goal_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[Any] = []
        if type:
            conditions.append("type = ?")
            params.append(type)
        if tag:
            conditions.append(
                "EXISTS (SELECT 1 FROM json_each(assets.tags) WHERE json_each.value = ?)"
            )
            params.append(tag)
        if related_goal_id:
            conditions.append("related_goal_id = ?")
            params.append(related_goal_id)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM assets{where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        def _do():
            rows = self._conn.execute(sql, params).fetchall()
            return [_row_to_dict(r, "assets") for r in rows]

        return await self._run(_do)

    async def get_asset(self, asset_id: str) -> dict | None:
        def _do():
            row = self._conn.execute(
                "SELECT * FROM assets WHERE id = ?", (asset_id,)
            ).fetchone()
            return _row_to_dict(row, "assets") if row else None

        return await self._run(_do)

    async def increment_reuse(self, asset_id: str) -> None:
        """Atomically bump reuse_count by 1."""

        def _do():
            self._conn.execute(
                "UPDATE assets SET reuse_count = reuse_count + 1, updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), asset_id),
            )
            self._conn.commit()

        await self._run(_do)

    # ==================================================================
    # REVIEWS
    # ==================================================================

    async def create_review(self, data: ReviewCreate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        review_id = uuid.uuid4().hex
        payload = _serialize(data.model_dump())
        payload["id"] = review_id
        payload["created_at"] = now

        def _do():
            self._conn.execute(
                """INSERT INTO reviews
                   (id, period, start_date, end_date, highlights, problems,
                    next_actions, ai_pattern_analysis, ai_questions,
                    completion_rate, asset_count, insight_count, created_at)
                VALUES
                   (:id, :period, :start_date, :end_date, :highlights, :problems,
                    :next_actions, :ai_pattern_analysis, :ai_questions,
                    :completion_rate, :asset_count, :insight_count, :created_at)""",
                payload,
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ).fetchone()
            return _row_to_dict(row, "reviews") if row else None

        return await self._run(_do)

    async def get_reviews(
        self,
        period: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        conditions: list[str] = []
        params: list[Any] = []
        if period:
            conditions.append("period = ?")
            params.append(period)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM reviews{where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        def _do():
            rows = self._conn.execute(sql, params).fetchall()
            return [_row_to_dict(r, "reviews") for r in rows]

        return await self._run(_do)

    async def get_review(self, review_id: str) -> dict | None:
        def _do():
            row = self._conn.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ).fetchone()
            return _row_to_dict(row, "reviews") if row else None

        return await self._run(_do)

    async def update_review(self, review_id: str, data: dict) -> dict:
        payload = _serialize(data)
        if not payload:
            return await self.get_review(review_id)
        set_clause = ", ".join(f"{k} = ?" for k in payload)
        values = list(payload.values()) + [review_id]
        sql = f"UPDATE reviews SET {set_clause} WHERE id = ?"

        def _do():
            self._conn.execute(sql, values)
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ).fetchone()
            return _row_to_dict(row, "reviews") if row else None

        return await self._run(_do)

    # ==================================================================
    # ENVIRONMENT RULES
    # ==================================================================

    async def get_active_rules(self) -> list[dict]:
        def _do():
            rows = self._conn.execute(
                "SELECT * FROM environment_rules WHERE active = 1 ORDER BY created_at DESC"
            ).fetchall()
            return [_row_to_dict(r, "environment_rules") for r in rows]

        return await self._run(_do)

    async def create_rule(self, data: EnvironmentRuleCreate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        rule_id = uuid.uuid4().hex
        payload = _serialize(data.model_dump())
        payload["id"] = rule_id
        payload["created_at"] = now

        def _do():
            self._conn.execute(
                """INSERT INTO environment_rules
                   (id, name, type, target, condition, action,
                    active, last_triggered_at, trigger_count, created_at)
                VALUES
                   (:id, :name, :type, :target, :condition, :action,
                    :active, :last_triggered_at, :trigger_count, :created_at)""",
                payload,
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM environment_rules WHERE id = ?", (rule_id,)
            ).fetchone()
            return _row_to_dict(row, "environment_rules") if row else None

        return await self._run(_do)

    # ==================================================================
    # AI INTERACTIONS
    # ==================================================================

    async def log_interaction(
        self,
        agent_name: str,
        prompt_version: str,
        input_data: dict,
        output_data: dict,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: int,
        status: str,
        error_message: str | None = None,
        related_table: str | None = None,
        related_id: str | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        interaction_id = uuid.uuid4().hex
        payload: dict[str, Any] = {
            "id": interaction_id,
            "agent_name": agent_name,
            "prompt_version": prompt_version,
            "input": json.dumps(input_data, ensure_ascii=False, default=str),
            "output": json.dumps(output_data, ensure_ascii=False, default=str) if output_data else None,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "status": status,
            "error_message": error_message,
            "related_table": related_table,
            "related_id": str(related_id) if related_id else None,
            "created_at": now,
        }

        def _do():
            self._conn.execute(
                """INSERT INTO ai_interactions
                   (id, agent_name, prompt_version, input, output, model,
                    input_tokens, output_tokens, cost_usd, latency_ms, status,
                    error_message, related_table, related_id, created_at)
                VALUES
                   (:id, :agent_name, :prompt_version, :input, :output, :model,
                    :input_tokens, :output_tokens, :cost_usd, :latency_ms, :status,
                    :error_message, :related_table, :related_id, :created_at)""",
                payload,
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT * FROM ai_interactions WHERE id = ?", (interaction_id,)
            ).fetchone()
            return _row_to_dict(row, "ai_interactions") if row else None

        return await self._run(_do)

    async def get_monthly_cost(self) -> float:
        """Sum of cost_usd for the current calendar month."""
        first_of_month = date.today().replace(day=1).isoformat()

        def _do():
            row = self._conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) AS total "
                "FROM ai_interactions WHERE created_at >= ?",
                (first_of_month,),
            ).fetchone()
            return float(row["total"]) if row else 0.0

        return await self._run(_do)

    async def get_agent_stats(self, agent_name: str, days: int = 30) -> dict:
        """Aggregate stats for an agent over the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        def _do():
            rows = self._conn.execute(
                "SELECT * FROM ai_interactions "
                "WHERE agent_name = ? AND created_at >= ?",
                (agent_name, cutoff),
            ).fetchall()
            rows = [_row_to_dict(r, "ai_interactions") for r in rows]

            total = len(rows)
            successes = sum(1 for r in rows if r.get("status") == "success")
            errors = sum(1 for r in rows if r.get("status") == "error")
            total_cost = sum(r.get("cost_usd") or 0 for r in rows)
            avg_latency = (
                sum(r.get("latency_ms") or 0 for r in rows) / total if total else 0
            )
            total_input_tokens = sum(r.get("input_tokens") or 0 for r in rows)
            total_output_tokens = sum(r.get("output_tokens") or 0 for r in rows)
            return {
                "agent_name": agent_name,
                "period_days": days,
                "total_calls": total,
                "successes": successes,
                "errors": errors,
                "error_rate": errors / total if total else 0,
                "total_cost_usd": round(total_cost, 6),
                "avg_latency_ms": round(avg_latency, 1),
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
            }

        return await self._run(_do)

    # ==================================================================
    # DASHBOARD
    # ==================================================================

    async def get_dashboard_stats(self) -> DashboardStats:
        """Build the aggregated dashboard view.

        We fire several queries concurrently to minimise wall-clock time.
        """
        today = date.today()
        first_of_month = today.replace(day=1)
        thirty_days_ago = today - timedelta(days=30)

        # --- concurrent fetches ---
        async def _fetch_logs_30d():
            return await self.get_daily_logs(
                start_date=thirty_days_ago, end_date=today, limit=31
            )

        async def _fetch_active_goals():
            return await self.get_goals(status="active")

        async def _fetch_assets():
            return await self.get_assets(limit=10000)

        async def _fetch_insights():
            return await self.get_insights(limit=10000)

        async def _fetch_monthly_cost():
            return await self.get_monthly_cost()

        async def _fetch_latest_review():
            reviews = await self.get_reviews(limit=1)
            return reviews[0] if reviews else None

        (
            logs_30d,
            active_goals,
            assets,
            insights,
            monthly_cost,
            latest_review,
        ) = await asyncio.gather(
            _fetch_logs_30d(),
            _fetch_active_goals(),
            _fetch_assets(),
            _fetch_insights(),
            _fetch_monthly_cost(),
            _fetch_latest_review(),
        )

        # --- derived metrics ---
        # completion rate: completed=True logs / total logs in 30d
        completed_logs = [l for l in logs_30d if l.get("completed")]
        completion_rate = (
            len(completed_logs) / len(logs_30d) if logs_30d else 0.0
        )

        # streak: count consecutive completed days ending at today
        streak = 0
        check = today
        log_dates = {l["log_date"] for l in logs_30d if l.get("completed")}
        while check.isoformat() in log_dates:
            streak += 1
            check -= timedelta(days=1)

        # focus minutes total
        total_focus = sum(l.get("focus_minutes") or 0 for l in logs_30d)

        # mood / energy averages
        moods = [l["mood"] for l in logs_30d if l.get("mood")]
        energies = [l["energy"] for l in logs_30d if l.get("energy")]
        avg_mood = round(sum(moods) / len(moods), 2) if moods else None
        avg_energy = round(sum(energies) / len(energies), 2) if energies else None

        # assets / insights this week (last 7 days)
        week_ago = today - timedelta(days=7)
        assets_week = [
            a for a in assets
            if a.get("created_at", "") >= week_ago.isoformat()
        ]
        insights_week = [
            i for i in insights
            if i.get("created_at", "") >= week_ago.isoformat()
        ]

        # total goals and completed goals + total log count (aggregate query)
        def _counts():
            all_goals = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM goals WHERE deleted_at IS NULL"
            ).fetchone()["cnt"]
            completed_goals = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM goals WHERE deleted_at IS NULL AND status = 'done'"
            ).fetchone()["cnt"]
            total_logs = self._conn.execute(
                "SELECT COUNT(*) AS cnt FROM daily_logs"
            ).fetchone()["cnt"]
            return all_goals, completed_goals, total_logs

        all_goals_count, completed_goals_count, total_logs_count = await self._run(_counts)

        return DashboardStats(
            total_goals=all_goals_count,
            active_goals=len(active_goals),
            completed_goals=completed_goals_count,
            total_logs=total_logs_count,
            current_streak=streak,
            total_focus_minutes=total_focus,
            average_mood=avg_mood,
            average_energy=avg_energy,
            insights_this_week=len(insights_week),
            assets_this_week=len(assets_week),
        )
