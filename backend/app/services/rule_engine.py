"""Business rules engine for Growth OS.

Evaluates 6 automated rules against current system state and returns
triggered notifications with severity levels.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

from backend.app.config import settings
from backend.app.services.db_service import DBService

logger = logging.getLogger(__name__)


class RuleEngine:
    """Evaluates business rules and returns triggered notifications."""

    async def check_all_rules(self, db: DBService) -> list[dict[str, Any]]:
        """Run all 6 rules concurrently and return those that are triggered."""
        results = await asyncio.gather(
            self._rule_consecutive_incomplete(db),
            self._rule_low_mood_energy(db),
            self._rule_zero_assets(db),
            self._rule_low_completion_rate(db),
            self._rule_skipped_weekly_reviews(db),
            self._rule_ai_budget_warning(db),
            return_exceptions=True,
        )

        triggered: list[dict[str, Any]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Rule evaluation failed: {result}")
                continue
            if result.get("triggered"):
                triggered.append(result)
        return triggered

    # ------------------------------------------------------------------
    # Rule 1: 3 consecutive days of incomplete core tasks
    # ------------------------------------------------------------------
    async def _rule_consecutive_incomplete(self, db: DBService) -> dict[str, Any]:
        """如果连续3天未完成核心任务，生成一个简化版任务建议。"""
        today = date.today()
        start = today - timedelta(days=4)  # fetch a little extra
        logs = await db.get_daily_logs(start_date=start, end_date=today, limit=5)

        consecutive_missed = 0
        for log in sorted(logs, key=lambda l: l.get("log_date", ""), reverse=True):
            if log.get("log_date") == today.isoformat():
                continue  # today's log may not be finalised yet
            if log.get("completed") is False:
                consecutive_missed += 1
            else:
                break

        triggered = consecutive_missed >= 3
        return {
            "rule_name": "consecutive_incomplete_tasks",
            "triggered": triggered,
            "message": (
                "⚠️ 你已经连续3天未完成核心任务。建议把今天的核心任务简化为一个"
                "5分钟就能完成的最小行动，先恢复节奏。"
                if triggered
                else ""
            ),
            "severity": "warning" if triggered else "info",
        }

    # ------------------------------------------------------------------
    # Rule 2: Low mood + energy for 3 consecutive days
    # ------------------------------------------------------------------
    async def _rule_low_mood_energy(self, db: DBService) -> dict[str, Any]:
        """如果情绪+精力平均值低于2.5（连续3天），触发休息建议。"""
        today = date.today()
        start = today - timedelta(days=5)
        logs = await db.get_daily_logs(start_date=start, end_date=today, limit=6)

        consecutive_low = 0
        for log in sorted(logs, key=lambda l: l.get("log_date", ""), reverse=True):
            mood = log.get("mood")
            energy = log.get("energy")
            if mood is None or energy is None:
                continue
            if log.get("log_date") == today.isoformat():
                continue
            avg = (mood + energy) / 2
            if avg < 2.5:
                consecutive_low += 1
            else:
                break

        triggered = consecutive_low >= 3
        return {
            "rule_name": "low_mood_energy",
            "triggered": triggered,
            "message": (
                "💛 你的情绪和精力连续3天偏低。建议今天降低任务强度，"
                "做一些放松活动，照顾好自己。"
                if triggered
                else ""
            ),
            "severity": "warning" if triggered else "info",
        }

    # ------------------------------------------------------------------
    # Rule 3: Zero assets for > 7 days
    # ------------------------------------------------------------------
    async def _rule_zero_assets(self, db: DBService) -> dict[str, Any]:
        """如果资产数为0超过7天，提醒用户注意产出。"""
        assets = await db.get_assets(limit=200)

        today = date.today()
        seven_days_ago = (today - timedelta(days=7)).isoformat()

        recent_assets = [
            a for a in assets
            if a.get("created_at", "") >= seven_days_ago
        ]

        triggered = len(recent_assets) == 0
        return {
            "rule_name": "zero_assets_7d",
            "triggered": triggered,
            "message": (
                "📦 你已经7天没有产出任何资产了。试着从今天的日志中提取一个"
                "可复用的方法、模板或代码片段。"
                if triggered
                else ""
            ),
            "severity": "info" if triggered else "info",
        }

    # ------------------------------------------------------------------
    # Rule 4: Completion rate < 50% for a week
    # ------------------------------------------------------------------
    async def _rule_low_completion_rate(self, db: DBService) -> dict[str, Any]:
        """如果完成率低于50%连续一周，建议降低目标难度。"""
        today = date.today()
        week_ago = today - timedelta(days=7)
        logs = await db.get_daily_logs(start_date=week_ago, end_date=today, limit=8)

        if len(logs) < 3:
            return {
                "rule_name": "low_completion_rate",
                "triggered": False,
                "message": "",
                "severity": "info",
            }

        completed = sum(1 for l in logs if l.get("completed"))
        rate = completed / len(logs)
        triggered = rate < 0.5

        return {
            "rule_name": "low_completion_rate",
            "triggered": triggered,
            "message": (
                f"📉 本周完成率仅 {rate:.0%}。建议降低目标难度或拆分任务，"
                "让每一天都有小的胜利感。"
                if triggered
                else ""
            ),
            "severity": "warning" if triggered else "info",
        }

    # ------------------------------------------------------------------
    # Rule 5: Weekly review skipped 2 times
    # ------------------------------------------------------------------
    async def _rule_skipped_weekly_reviews(self, db: DBService) -> dict[str, Any]:
        """如果周复盘被跳过2次，发送提醒。"""
        today = date.today()
        reviews = await db.get_reviews(period="week", limit=4)

        # Calculate the start of the current week (Monday) and previous weeks
        last_week_start = today - timedelta(days=today.weekday() + 7)
        two_weeks_start = last_week_start - timedelta(days=7)

        has_last_week = any(
            r for r in reviews
            if r.get("start_date", "") >= last_week_start.isoformat()
        )
        has_two_weeks_ago = any(
            r for r in reviews
            if two_weeks_start.isoformat() <= r.get("start_date", "") < last_week_start.isoformat()
        )

        skipped = int(not has_last_week) + int(not has_two_weeks_ago)
        triggered = skipped >= 2

        return {
            "rule_name": "skipped_weekly_reviews",
            "triggered": triggered,
            "message": (
                "📋 你已经跳过了最近2次周复盘。花15分钟回顾一下过去两周，"
                "能帮你及时调整方向。"
                if triggered
                else ""
            ),
            "severity": "warning" if triggered else "info",
        }

    # ------------------------------------------------------------------
    # Rule 6: AI monthly cost exceeds 80% of budget
    # ------------------------------------------------------------------
    async def _rule_ai_budget_warning(self, db: DBService) -> dict[str, Any]:
        """如果AI月度成本超过预算的80%，发出警告。"""
        monthly_cost = await db.get_monthly_cost()
        budget = settings.ai_monthly_budget_usd

        usage_pct = monthly_cost / budget if budget > 0 else 0
        triggered = usage_pct >= 0.8

        return {
            "rule_name": "ai_budget_warning",
            "triggered": triggered,
            "message": (
                f"💰 AI 月度费用已达 ${monthly_cost:.2f}，"
                f"占预算的 {usage_pct:.0%}。请注意控制调用频率。"
                if triggered
                else ""
            ),
            "severity": (
                "critical" if usage_pct >= 1.0
                else ("warning" if triggered else "info")
            ),
        }


# Module-level singleton
rule_engine = RuleEngine()
