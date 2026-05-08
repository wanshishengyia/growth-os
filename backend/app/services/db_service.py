"""Database service layer for Growth OS.

All Supabase CRUD operations live here.  Every public method is `async` (the
supabase-py client is synchronous under the hood, so we delegate to
`asyncio.to_thread` to keep the FastAPI event-loop non-blocking).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from app.models.ai_interaction import AIInteractionCreate
from app.models.asset import AssetCreate
from app.models.daily_log import DailyLogCreate
from app.models.environment_rule import EnvironmentRuleCreate
from app.models.goal import GoalCreate, GoalUpdate
from app.models.insight import InsightCreate
from app.models.review import ReviewCreate
from app.models.responses import DashboardStats
from app.services.supabase_client import get_client


def _serialize(data: dict) -> dict:
    """Convert Pydantic-style values (UUID, date, Enum, …) into JSON-safe
    primitives so the Supabase REST client can send them."""

    out: dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(v, UUID):
            out[k] = str(v)
        elif isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        elif isinstance(v, list):
            out[k] = [
                str(i) if isinstance(i, UUID) else i
                for i in v
            ]
        elif hasattr(v, "value"):  # Enum
            out[k] = v.value
        else:
            out[k] = v
    return out


class DBService:
    """Thin data-access layer backed by Supabase PostgREST."""

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._sb = get_client()

    # helper – run blocking call in a thread
    async def _run(self, fn, *args, **kwargs):
        return await asyncio.to_thread(fn, *args, **kwargs)

    # ==================================================================
    # GOALS
    # ==================================================================

    async def create_goal(self, data: GoalCreate) -> dict:
        payload = _serialize(data.model_dump())
        resp = await self._run(
            lambda: self._sb.table("goals").insert(payload).execute()
        )
        return resp.data[0]

    async def get_goals(
        self,
        status: str | None = None,
        level: str | None = None,
        parent_id: str | None = None,
    ) -> list[dict]:
        q = self._sb.table("goals").select("*").is_("deleted_at", "null")
        if status:
            q = q.eq("status", status)
        if level:
            q = q.eq("level", level)
        if parent_id:
            q = q.eq("parent_id", parent_id)
        q = q.order("created_at", desc=True)
        resp = await self._run(lambda: q.execute())
        return resp.data

    async def get_goal(self, goal_id: str) -> dict | None:
        resp = await self._run(
            lambda: self._sb.table("goals")
            .select("*")
            .eq("id", goal_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return resp.data[0] if resp.data else None

    async def update_goal(self, goal_id: str, data: GoalUpdate) -> dict:
        payload = _serialize(
            data.model_dump(exclude_unset=True)
        )
        resp = await self._run(
            lambda: self._sb.table("goals")
            .update(payload)
            .eq("id", goal_id)
            .execute()
        )
        return resp.data[0]

    async def delete_goal(self, goal_id: str) -> None:
        """Soft-delete: set deleted_at to now."""
        await self._run(
            lambda: self._sb.table("goals")
            .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", goal_id)
            .execute()
        )

    # ==================================================================
    # DAILY LOGS
    # ==================================================================

    async def create_daily_log(self, data: DailyLogCreate) -> dict:
        payload = _serialize(data.model_dump())
        resp = await self._run(
            lambda: self._sb.table("daily_logs").insert(payload).execute()
        )
        return resp.data[0]

    async def get_daily_log_by_date(self, log_date: date) -> dict | None:
        resp = await self._run(
            lambda: self._sb.table("daily_logs")
            .select("*")
            .eq("log_date", log_date.isoformat())
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None

    async def update_daily_log(self, log_id: str, data: dict) -> dict:
        payload = _serialize(data)
        resp = await self._run(
            lambda: self._sb.table("daily_logs")
            .update(payload)
            .eq("id", log_id)
            .execute()
        )
        return resp.data[0]

    async def get_daily_logs(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 30,
    ) -> list[dict]:
        q = self._sb.table("daily_logs").select("*")
        if start_date:
            q = q.gte("log_date", start_date.isoformat())
        if end_date:
            q = q.lte("log_date", end_date.isoformat())
        q = q.order("log_date", desc=True).limit(limit)
        resp = await self._run(lambda: q.execute())
        return resp.data

    async def get_yesterday_log(self) -> dict | None:
        yesterday = date.today() - timedelta(days=1)
        return await self.get_daily_log_by_date(yesterday)

    # ==================================================================
    # INSIGHTS
    # ==================================================================

    async def create_insight(self, data: InsightCreate) -> dict:
        payload = _serialize(data.model_dump())
        resp = await self._run(
            lambda: self._sb.table("insights").insert(payload).execute()
        )
        return resp.data[0]

    async def get_insights(
        self,
        type: str | None = None,
        min_confidence: int | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        q = self._sb.table("insights").select("*")
        if type:
            q = q.eq("type", type)
        if min_confidence is not None:
            q = q.gte("confidence", min_confidence)
        if tag:
            q = q.contains("tags", [tag])
        q = q.order("created_at", desc=True).limit(limit)
        resp = await self._run(lambda: q.execute())
        return resp.data

    async def get_insight(self, insight_id: str) -> dict | None:
        resp = await self._run(
            lambda: self._sb.table("insights")
            .select("*")
            .eq("id", insight_id)
            .execute()
        )
        return resp.data[0] if resp.data else None

    # ==================================================================
    # ASSETS
    # ==================================================================

    async def create_asset(self, data: AssetCreate) -> dict:
        payload = _serialize(data.model_dump())
        resp = await self._run(
            lambda: self._sb.table("assets").insert(payload).execute()
        )
        return resp.data[0]

    async def get_assets(
        self,
        type: str | None = None,
        tag: str | None = None,
        related_goal_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        q = self._sb.table("assets").select("*")
        if type:
            q = q.eq("type", type)
        if tag:
            q = q.contains("tags", [tag])
        if related_goal_id:
            q = q.eq("related_goal_id", related_goal_id)
        q = q.order("created_at", desc=True).limit(limit)
        resp = await self._run(lambda: q.execute())
        return resp.data

    async def get_asset(self, asset_id: str) -> dict | None:
        resp = await self._run(
            lambda: self._sb.table("assets")
            .select("*")
            .eq("id", asset_id)
            .execute()
        )
        return resp.data[0] if resp.data else None

    async def increment_reuse(self, asset_id: str) -> None:
        """Atomically bump reuse_count by 1 via an RPC or read-modify-write."""
        # Supabase doesn't support native increment in the Python client,
        # so we do a two-step read-modify-write.
        asset = await self.get_asset(asset_id)
        if asset is None:
            return
        new_count = (asset.get("reuse_count") or 0) + 1
        await self._run(
            lambda: self._sb.table("assets")
            .update({"reuse_count": new_count})
            .eq("id", asset_id)
            .execute()
        )

    # ==================================================================
    # REVIEWS
    # ==================================================================

    async def create_review(self, data: ReviewCreate) -> dict:
        payload = _serialize(data.model_dump())
        resp = await self._run(
            lambda: self._sb.table("reviews").insert(payload).execute()
        )
        return resp.data[0]

    async def get_reviews(
        self,
        period: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        q = self._sb.table("reviews").select("*")
        if period:
            q = q.eq("period", period)
        q = q.order("created_at", desc=True).limit(limit)
        resp = await self._run(lambda: q.execute())
        return resp.data

    async def get_review(self, review_id: str) -> dict | None:
        resp = await self._run(
            lambda: self._sb.table("reviews")
            .select("*")
            .eq("id", review_id)
            .execute()
        )
        return resp.data[0] if resp.data else None

    async def update_review(self, review_id: str, data: dict) -> dict:
        payload = _serialize(data)
        resp = await self._run(
            lambda: self._sb.table("reviews")
            .update(payload)
            .eq("id", review_id)
            .execute()
        )
        return resp.data[0]

    # ==================================================================
    # ENVIRONMENT RULES
    # ==================================================================

    async def get_active_rules(self) -> list[dict]:
        resp = await self._run(
            lambda: self._sb.table("environment_rules")
            .select("*")
            .eq("active", True)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data

    async def create_rule(self, data: EnvironmentRuleCreate) -> dict:
        payload = _serialize(data.model_dump())
        resp = await self._run(
            lambda: self._sb.table("environment_rules")
            .insert(payload)
            .execute()
        )
        return resp.data[0]

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
        payload: dict[str, Any] = {
            "agent_name": agent_name,
            "prompt_version": prompt_version,
            "input": input_data,
            "output": output_data,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "status": status,
        }
        if error_message is not None:
            payload["error_message"] = error_message
        if related_table is not None:
            payload["related_table"] = related_table
        if related_id is not None:
            payload["related_id"] = str(related_id)
        resp = await self._run(
            lambda: self._sb.table("ai_interactions")
            .insert(payload)
            .execute()
        )
        return resp.data[0]

    async def get_monthly_cost(self) -> float:
        """Sum of cost_usd for the current calendar month."""
        today = date.today()
        first_of_month = today.replace(day=1)
        resp = await self._run(
            lambda: self._sb.table("ai_interactions")
            .select("cost_usd")
            .gte("created_at", first_of_month.isoformat())
            .execute()
        )
        return sum(row.get("cost_usd") or 0 for row in resp.data)

    async def get_agent_stats(self, agent_name: str, days: int = 30) -> dict:
        """Aggregate stats for an agent over the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        resp = await self._run(
            lambda: self._sb.table("ai_interactions")
            .select("*")
            .eq("agent_name", agent_name)
            .gte("created_at", cutoff)
            .execute()
        )
        rows = resp.data
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

        # completed goals
        all_goals_resp = await self._run(
            lambda: self._sb.table("goals")
            .select("status", count="exact")
            .is_("deleted_at", "null")
            .execute()
        )
        all_goals = all_goals_resp.data
        completed_goals = sum(1 for g in all_goals if g.get("status") == "done")

        total_logs_resp = await self._run(
            lambda: self._sb.table("daily_logs")
            .select("id", count="exact")
            .execute()
        )
        total_logs_count = len(total_logs_resp.data)

        return DashboardStats(
            total_goals=len(all_goals),
            active_goals=len(active_goals),
            completed_goals=completed_goals,
            total_logs=total_logs_count,
            current_streak=streak,
            total_focus_minutes=total_focus,
            average_mood=avg_mood,
            average_energy=avg_energy,
            insights_this_week=len(insights_week),
            assets_this_week=len(assets_week),
        )
