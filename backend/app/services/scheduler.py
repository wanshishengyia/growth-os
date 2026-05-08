"""Growth OS — APScheduler service replacing n8n workflows.

Replaces the former n8n workflows (W1–W7) with in-process scheduled jobs:
  - W1  Morning push (ActionDecider → Feishu card)
  - W2  Evening reminder (Feishu prompt)
  - W3  Weekly review (PatternFinder + InsightMiner + Socratic → Feishu card)
  - W4  Monthly aggregate (dashboard stats → Feishu card)
  - W5  Health check (every 30 min, DB liveness)
  - (W6/W7 backup + asset archive are lower priority; health-check covers liveness)

Runs inside the FastAPI lifespan using ``AsyncIOScheduler`` so jobs share
the same event-loop as the web server.

Config keys (from ``backend.app.config.settings``):
  - scheduler_enabled : bool  — master on/off
  - morning_time      : str   — 'HH:MM' (Asia/Shanghai)
  - evening_time      : str   — 'HH:MM' (Asia/Shanghai)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class GrowthScheduler:
    """APScheduler wrapper that owns all Growth OS cron jobs.

    Parameters
    ----------
    db : DBService
    llm : LLMClient
    prompt_loader : PromptLoader
    messenger : FeishuMessenger
    """

    def __init__(self, db, llm, prompt_loader, messenger):
        self.db = db
        self.llm = llm
        self.prompt_loader = prompt_loader
        self.messenger = messenger
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def setup(
        self,
        morning_time: str = "07:30",
        evening_time: str = "22:00",
    ) -> None:
        """Register all scheduled jobs. Call once before ``start()``."""
        # W1 — Morning push
        h, m = morning_time.split(":")
        self.scheduler.add_job(
            self.morning_push,
            CronTrigger(hour=int(h), minute=int(m), timezone="Asia/Shanghai"),
            id="morning_push",
            name="晨间推送",
            replace_existing=True,
        )

        # W2 — Evening reminder
        h, m = evening_time.split(":")
        self.scheduler.add_job(
            self.evening_reminder,
            CronTrigger(hour=int(h), minute=int(m), timezone="Asia/Shanghai"),
            id="evening_reminder",
            name="晚间提醒",
            replace_existing=True,
        )

        # W3 — Weekly review (Sunday 20:00)
        self.scheduler.add_job(
            self.weekly_review,
            CronTrigger(
                day_of_week="sun", hour=20, minute=0, timezone="Asia/Shanghai"
            ),
            id="weekly_review",
            name="周复盘",
            replace_existing=True,
        )

        # W4 — Monthly report (last day of month 21:00)
        self.scheduler.add_job(
            self.monthly_report,
            CronTrigger(day="last", hour=21, minute=0, timezone="Asia/Shanghai"),
            id="monthly_report",
            name="月报告",
            replace_existing=True,
        )

        # W5 — Health check (every 30 min)
        self.scheduler.add_job(
            self.health_check,
            CronTrigger(minute="*/30", timezone="Asia/Shanghai"),
            id="health_check",
            name="健康检查",
            replace_existing=True,
        )

        logger.info(
            "Scheduler configured: morning=%s, evening=%s", morning_time, evening_time
        )

    def start(self) -> None:
        """Start the scheduler (non-blocking)."""
        self.scheduler.start()
        jobs = self.scheduler.get_jobs()
        logger.info(
            "Scheduler started with %d jobs: %s",
            len(jobs),
            ", ".join(f"{j.id}({j.name})" for j in jobs),
        )

    def shutdown(self, wait: bool = True) -> None:
        """Gracefully shut down the scheduler."""
        self.scheduler.shutdown(wait=wait)
        logger.info("Scheduler stopped")

    # ------------------------------------------------------------------
    # W1 — Morning Push
    # ------------------------------------------------------------------

    async def morning_push(self) -> None:
        """Daily morning: run ActionDecider agent, create daily log, send to Feishu.

        Mirrors the logic in ``POST /api/loop/daily/morning`` but without
        HTTP round-trip; called directly by the scheduler.
        """
        try:
            from backend.app.agents.action_decider import ActionDeciderAgent
            from backend.app.models.daily_log import DailyLogCreate

            today = date.today()

            # Skip if today's log already exists with a core_task
            existing = await self.db.get_daily_log_by_date(today)
            if existing and existing.get("core_task"):
                logger.info("Morning push: today's log already exists, skipping")
                return

            # Gather context
            yesterday_log = await self.db.get_yesterday_log()
            active_goals = await self.db.get_goals(status="active")
            week_start = today - timedelta(days=7)
            recent_logs = await self.db.get_daily_logs(
                start_date=week_start, end_date=today, limit=8
            )
            recent_insights = await self.db.get_insights(limit=5)

            # Pick highest-priority active goal
            target_goal = None
            if active_goals:
                target_goal = sorted(
                    active_goals, key=lambda g: g.get("priority", 3)
                )[0]

            # Build agent input
            from backend.app.models.schemas import ActionDeciderInput

            a1_input = ActionDeciderInput(
                goal_title=(
                    target_goal["title"] if target_goal else "Daily improvement"
                ),
                goal_description=(
                    target_goal.get("description") if target_goal else None
                ),
                goal_level=target_goal.get("level", "week") if target_goal else "week",
                current_progress=target_goal.get("progress", 0) if target_goal else 0,
                days_remaining=None,
                recent_logs=recent_logs,
                recent_insights=[i.get("content", "") for i in recent_insights],
            )

            # Run A1
            agent = ActionDeciderAgent(
                llm=self.llm, prompt_loader=self.prompt_loader, db=self.db
            )

            try:
                result = await agent.run(a1_input.model_dump())
            except Exception as agent_err:
                logger.error("A1 ActionDecider failed in morning push: %s", agent_err)
                result = {
                    "core_task": "Review your goals and pick one small action.",
                    "reasoning": "Agent unavailable.",
                    "estimated_minutes": 30,
                }

            # Create today's daily log
            log_data = DailyLogCreate(
                log_date=today,
                goal_id=target_goal["id"] if target_goal else None,
                core_task=result.get("core_task", result.get("next_action", "")),
                min_action=result.get("min_action"),
                judge_criteria=result.get("judge_criteria"),
            )
            await self.db.create_daily_log(log_data)

            # Send to Feishu
            await self.messenger.send_morning(result)
            logger.info("Morning push completed")

        except Exception as e:
            logger.error("Morning push failed: %s", e, exc_info=True)
            try:
                await self.messenger.send_alert("晨间推送失败", str(e))
            except Exception:
                logger.error("Failed to send morning push failure alert")

    # ------------------------------------------------------------------
    # W2 — Evening Reminder
    # ------------------------------------------------------------------

    async def evening_reminder(self) -> None:
        """Daily evening: remind user to submit notes via Feishu."""
        try:
            today = date.today()
            log = await self.db.get_daily_log_by_date(today)

            if log and log.get("raw_notes"):
                logger.info("Evening reminder: today's notes already submitted")
                return

            await self.messenger.send_text(
                "🌙 该写流水账了！\n\n"
                "今日记录要点：\n"
                "• 今天完成了什么？\n"
                "• 遇到了什么问题？\n"
                "• 明天想怎么调整？\n\n"
                "用 `POST /api/loop/daily/evening` 提交今天的记录。"
            )
            logger.info("Evening reminder sent")

        except Exception as e:
            logger.error("Evening reminder failed: %s", e, exc_info=True)

    # ------------------------------------------------------------------
    # W3 — Weekly Review
    # ------------------------------------------------------------------

    async def weekly_review(self) -> None:
        """Weekly: run PatternFinder + InsightMiner + SocraticQuestioner.

        Mirrors ``POST /api/loop/weekly/run``.
        """
        try:
            from backend.app.agents.pattern_finder import PatternFinderAgent
            from backend.app.agents.insight_miner import InsightMinerAgent
            from backend.app.agents.socratic_questioner import SocraticQuestionerAgent
            from backend.app.models.review import ReviewCreate, PeriodEnum
            from backend.app.models.schemas import (
                PatternFinderInput,
                InsightMinerInput,
                SocraticQuestionerInput,
            )

            today = date.today()
            ws = today - timedelta(days=today.weekday())  # Monday
            we = ws + timedelta(days=6)

            # Get week's logs
            logs = await self.db.get_daily_logs(
                start_date=ws, end_date=we, limit=7
            )
            if not logs:
                await self.messenger.send_text("本周没有日志数据，跳过周复盘。")
                logger.info("Weekly review: no logs, skipped")
                return

            # Run A3 PatternFinder and A5 InsightMiner in parallel
            pattern_finder = PatternFinderAgent(
                llm=self.llm, prompt_loader=self.prompt_loader, db=self.db
            )
            insight_miner = InsightMinerAgent(
                llm=self.llm, prompt_loader=self.prompt_loader, db=self.db
            )

            a3_input = PatternFinderInput(
                daily_logs=logs,
                time_range_start=ws,
                time_range_end=we,
            )

            import asyncio

            all_notes = "\n".join(
                l.get("raw_notes", "") for l in logs if l.get("raw_notes")
            )
            a5_input = InsightMinerInput(
                raw_notes=all_notes or "No notes this week.",
                log_date=we,
            )

            try:
                pattern_result, insight_result = await asyncio.gather(
                    pattern_finder.run(a3_input.model_dump()),
                    insight_miner.run(a5_input.model_dump()),
                )
            except Exception as agent_err:
                logger.error("Weekly agents failed: %s", agent_err)
                pattern_result = {
                    "patterns": [],
                    "summary": "Unable to analyze patterns.",
                }
                insight_result = {
                    "insights": [],
                    "summary": "Unable to mine insights.",
                }

            # Compute completion rate
            completed = sum(1 for l in logs if l.get("completed"))
            completion_rate = round(completed / len(logs), 2) if logs else 0.0

            # Count assets and insights for the week
            week_iso = ws.isoformat()
            assets = await self.db.get_assets(limit=200)
            insights = await self.db.get_insights(limit=200)
            assets_week = [
                a for a in assets if a.get("created_at", "") >= week_iso
            ]
            insights_week = [
                i for i in insights if i.get("created_at", "") >= week_iso
            ]

            # Create review record
            review_data = ReviewCreate(
                period=PeriodEnum.WEEK,
                start_date=ws,
                end_date=we,
                ai_pattern_analysis=pattern_result,
                completion_rate=completion_rate,
                asset_count=len(assets_week),
                insight_count=len(insights_week),
            )
            review = await self.db.create_review(review_data)

            # Run A6 SocraticQuestioner
            socratic = SocraticQuestionerAgent(
                llm=self.llm, prompt_loader=self.prompt_loader, db=self.db
            )
            a6_input = SocraticQuestionerInput(
                topic="Weekly review reflection",
                current_understanding=pattern_result.get("summary", ""),
                recent_logs=logs,
            )

            try:
                socratic_result = await socratic.run(a6_input.model_dump())
                questions = socratic_result.get("questions", [])
            except Exception as agent_err:
                logger.error("A6 SocraticQuestioner failed: %s", agent_err)
                questions = [
                    "本周最大的收获是什么？",
                    "下周你想改变的一件事是什么？",
                ]

            # Send review card to Feishu
            await self.messenger.send_review(review, questions)
            logger.info("Weekly review completed")

        except Exception as e:
            logger.error("Weekly review failed: %s", e, exc_info=True)
            try:
                await self.messenger.send_alert("周复盘失败", str(e))
            except Exception:
                logger.error("Failed to send weekly review failure alert")

    # ------------------------------------------------------------------
    # W4 — Monthly Report
    # ------------------------------------------------------------------

    async def monthly_report(self) -> None:
        """Monthly: aggregate stats and create monthly review.

        Mirrors ``POST /api/loop/monthly/run``.
        """
        try:
            from backend.app.models.review import ReviewCreate, PeriodEnum

            today = date.today()

            # Current month boundaries
            month_start = today.replace(day=1)
            if today.month == 12:
                month_end = today.replace(
                    year=today.year + 1, month=1, day=1
                ) - timedelta(days=1)
            else:
                month_end = today.replace(
                    month=today.month + 1, day=1
                ) - timedelta(days=1)

            # Get monthly logs
            logs = await self.db.get_daily_logs(
                start_date=month_start, end_date=today, limit=31
            )
            completed = sum(1 for l in logs if l.get("completed"))
            total_focus = sum(l.get("focus_minutes", 0) for l in logs)

            # Asset and insight counts
            assets = await self.db.get_assets(limit=500)
            insights = await self.db.get_insights(limit=500)
            month_assets = [
                a for a in assets if a.get("created_at", "") >= month_start.isoformat()
            ]
            month_insights = [
                i
                for i in insights
                if i.get("created_at", "") >= month_start.isoformat()
            ]

            stats = {
                "days_logged": len(logs),
                "days_completed": completed,
                "completion_rate": round(completed / len(logs), 2) if logs else 0,
                "total_focus_minutes": total_focus,
                "assets_created": len(month_assets),
                "insights_created": len(month_insights),
            }

            # Create monthly review record
            review_data = ReviewCreate(
                period=PeriodEnum.MONTH,
                start_date=month_start,
                end_date=month_end,
                completion_rate=stats["completion_rate"],
                asset_count=len(month_assets),
                insight_count=len(month_insights),
            )
            review = await self.db.create_review(review_data)

            # Also send dashboard stats to Feishu
            dashboard_stats = await self.db.get_dashboard_stats()
            # Convert pydantic model to dict for messenger
            stats_dict = (
                dashboard_stats.model_dump()
                if hasattr(dashboard_stats, "model_dump")
                else dashboard_stats.__dict__
            )
            await self.messenger.send_status(stats_dict)
            logger.info("Monthly report sent")

        except Exception as e:
            logger.error("Monthly report failed: %s", e, exc_info=True)
            try:
                await self.messenger.send_alert("月报告失败", str(e))
            except Exception:
                logger.error("Failed to send monthly report failure alert")

    # ------------------------------------------------------------------
    # W5 — Health Check
    # ------------------------------------------------------------------

    async def health_check(self) -> None:
        """Periodic: verify DB connectivity and send alert on failure."""
        try:
            # Simple DB liveness probe
            await self.db.get_daily_logs(limit=1)
            logger.debug("Health check passed")
        except Exception as e:
            logger.error("Health check failed: %s", e, exc_info=True)
            try:
                await self.messenger.send_alert(
                    "系统异常", f"健康检查失败: {e}"
                )
            except Exception:
                logger.error("Failed to send health check alert")
