"""Loop endpoints — the 4 time-scale loops of Growth OS.

Morning, Evening, Weekly, Monthly, and Quarterly loop drivers.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.app.models.daily_log import DailyLogCreate
from backend.app.models.review import ReviewCreate, PeriodEnum
from backend.app.models.requests import EveningSubmitRequest, WeeklySubmitRequest
from backend.app.models.responses import MorningResponse, EveningResponse
from backend.app.models.schemas import (
    ActionDeciderInput,
    LoopCloserInput,
    PatternFinderInput,
    AssetClassifierInput,
    InsightMinerInput,
    SocraticQuestionerInput,
    DirectionCalibratorInput,
)
from backend.app.models.asset import AssetCreate, AssetType
from backend.app.models.insight import InsightCreate, InsightType, SourceType
from backend.app.services.db_service import DBService
from backend.app.services.llm_client import LLMClient
from backend.app.services.prompt_loader import PromptLoader
from backend.app.agents import (
    ActionDeciderAgent,
    LoopCloserAgent,
    PatternFinderAgent,
    AssetClassifierAgent,
    InsightMinerAgent,
    SocraticQuestionerAgent,
    DirectionCalibratorAgent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/loop", tags=["loops"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db() -> DBService:
    return DBService()


def _get_llm() -> LLMClient:
    return LLMClient()


def _get_prompt_loader() -> PromptLoader:
    return PromptLoader()


def _today_str() -> str:
    return date.today().isoformat()


def _greeting() -> str:
    hour = datetime.now(timezone.utc).hour
    if hour < 12:
        return "早安！新的一天开始了 ☀️"
    elif hour < 18:
        return "下午好！继续加油 💪"
    else:
        return "晚上好！今天辛苦了 🌙"


# ---------------------------------------------------------------------------
# GET /api/loop/daily/morning
# ---------------------------------------------------------------------------

@router.get("/daily/morning", response_model=MorningResponse)
async def morning_loop():
    """Run the morning planning loop.

    1. Fetch yesterday's log, active goals, 7-day pattern
    2. Run A1 ActionDecider
    3. Create today's daily_log with core_task, min_action, judge_criteria
    """
    db = _get_db()
    today = date.today()

    # Check if today's log already exists
    existing = await db.get_daily_log_by_date(today)
    if existing and existing.get("core_task"):
        return MorningResponse(
            date=today.isoformat(),
            greeting=_greeting(),
            todays_focus=existing["core_task"],
            pending_actions=[],
            motivational_insight=existing.get("ai_summary"),
            related_insights=[],
        )

    # Gather context
    yesterday_log = await db.get_yesterday_log()
    active_goals = await db.get_goals(status="active")
    week_start = today - timedelta(days=7)
    recent_logs = await db.get_daily_logs(start_date=week_start, end_date=today, limit=8)
    recent_insights = await db.get_insights(limit=5)

    # Pick the highest-priority active goal
    target_goal = None
    if active_goals:
        target_goal = sorted(active_goals, key=lambda g: g.get("priority", 3))[0]

    # Build A1 input
    a1_input = ActionDeciderInput(
        goal_title=target_goal["title"] if target_goal else "Daily improvement",
        goal_description=target_goal.get("description") if target_goal else None,
        goal_level=target_goal.get("level", "week") if target_goal else "week",
        current_progress=target_goal.get("progress", 0) if target_goal else 0,
        days_remaining=None,
        recent_logs=recent_logs,
        recent_insights=[i.get("content", "") for i in recent_insights],
    )

    # Run A1
    llm = _get_llm()
    prompt_loader = _get_prompt_loader()
    agent = ActionDeciderAgent(llm=llm, prompt_loader=prompt_loader, db=db)

    try:
        result = await agent.run(a1_input.model_dump())
    except Exception as e:
        logger.error(f"A1 ActionDecider failed: {e}")
        # Fallback
        result = {
            "core_task": "Review your goals and pick one small action.",
            "reasoning": "Agent unavailable.",
            "estimated_minutes": 30,
        }

    # Create today's log
    log_data = DailyLogCreate(
        log_date=today,
        goal_id=target_goal["id"] if target_goal else None,
        core_task=result.get("core_task", result.get("next_action", "")),
        min_action=result.get("min_action"),
        judge_criteria=result.get("judge_criteria"),
    )
    await db.create_daily_log(log_data)

    # Format pending actions from yesterday
    pending: list[str] = []
    if yesterday_log and yesterday_log.get("ai_next_action"):
        pending.append(yesterday_log["ai_next_action"])

    return MorningResponse(
        date=today.isoformat(),
        greeting=_greeting(),
        todays_focus=result.get("core_task", result.get("next_action", "")),
        pending_actions=pending,
        motivational_insight=result.get("reasoning"),
        related_insights=[i.get("content", "") for i in recent_insights[:3]],
    )


# ---------------------------------------------------------------------------
# POST /api/loop/daily/evening
# ---------------------------------------------------------------------------

@router.post("/daily/evening", response_model=EveningResponse)
async def evening_loop(req: EveningSubmitRequest):
    """Run the evening reflection loop.

    1. Get today's daily_log (create if missing)
    2. Run A2 LoopCloser
    3. For asset candidates → run A4 AssetClassifier, create assets
    4. For insight candidates → create insights
    """
    db = _get_db()
    today = date.today()

    # Get or create today's log
    log = await db.get_daily_log_by_date(today)
    if not log:
        log_data = DailyLogCreate(
            log_date=today,
            raw_notes=req.raw_notes,
            mood=req.mood,
            energy=req.energy,
            completed=req.completed if req.completed is not None else False,
            focus_minutes=req.focus_minutes or 0,
        )
        log = await db.create_daily_log(log_data)
    else:
        # Update with evening data
        update_data: dict[str, Any] = {
            "raw_notes": req.raw_notes,
            "mood": req.mood,
            "energy": req.energy,
            "focus_minutes": req.focus_minutes or 0,
        }
        if req.completed is not None:
            update_data["completed"] = req.completed
        log = await db.update_daily_log(log["id"], update_data)

    # Run A2 LoopCloser
    llm = _get_llm()
    prompt_loader = _get_prompt_loader()

    active_goals = await db.get_goals(status="active")
    target_goal = active_goals[0] if active_goals else None

    a2_input = LoopCloserInput(
        goal_id=target_goal["id"] if target_goal else "00000000-0000-0000-0000-000000000000",
        goal_title=target_goal["title"] if target_goal else "General improvement",
        expected_outcome=log.get("core_task"),
        actual_outcome=req.raw_notes,
        daily_logs=[log],
    )

    loop_closer = LoopCloserAgent(llm=llm, prompt_loader=prompt_loader, db=db)

    try:
        result = await loop_closer.run(a2_input.model_dump())
    except Exception as e:
        logger.error(f"A2 LoopCloser failed: {e}")
        result = {
            "gap_analysis": "Unable to analyze.",
            "corrective_actions": [],
        }

    # Update log with AI output
    ai_update: dict[str, Any] = {
        "ai_summary": result.get("gap_analysis", ""),
        "ai_problem": result.get("root_cause", ""),
        "ai_next_action": (
            result["corrective_actions"][0]
            if result.get("corrective_actions")
            else ""
        ),
    }
    log = await db.update_daily_log(log["id"], ai_update)

    # Process asset candidates from the raw notes
    assets_created: list[dict[str, Any]] = []
    asset_classifier = AssetClassifierAgent(llm=llm, prompt_loader=prompt_loader, db=db)
    a4_input = AssetClassifierInput(
        title=f"Log {today.isoformat()}",
        content=req.raw_notes,
        context=log.get("core_task", ""),
    )
    try:
        classify_result = await asset_classifier.run(a4_input.model_dump())
        if classify_result.get("quality_estimate", 0) >= 3:
            asset_data = AssetCreate(
                type=AssetType(classify_result.get("asset_type", "snippet")),
                title=f"Asset from {today.isoformat()}",
                content=req.raw_notes,
                quality=classify_result.get("quality_estimate", 3),
                tags=classify_result.get("suggested_tags", []),
                ai_classification=classify_result,
                related_log_id=log["id"],
            )
            asset = await db.create_asset(asset_data)
            assets_created.append(asset)
    except Exception as e:
        logger.error(f"A4 AssetClassifier failed: {e}")

    # Mine insights from raw notes
    insights_created: list[dict[str, Any]] = []
    insight_miner = InsightMinerAgent(llm=llm, prompt_loader=prompt_loader, db=db)
    a5_input = InsightMinerInput(
        raw_notes=req.raw_notes,
        log_date=today,
        goal_context=target_goal["title"] if target_goal else None,
        mood=req.mood,
        energy=req.energy,
    )
    try:
        insight_result = await insight_miner.run(a5_input.model_dump())
        for item in insight_result.get("insights", []):
            insight_data = InsightCreate(
                type=InsightType.INSIGHT,
                content=item.get("content", str(item)),
                source_type=SourceType.DAILY_LOG,
                source_id=log["id"],
                tags=item.get("tags", []),
            )
            created = await db.create_insight(insight_data)
            insights_created.append(created)
    except Exception as e:
        logger.error(f"A5 InsightMiner failed: {e}")

    # Streak info
    recent_logs = await db.get_daily_logs(limit=30)
    streak = 0
    check = today
    completed_dates = {l["log_date"] for l in recent_logs if l.get("completed")}
    while check.isoformat() in completed_dates:
        streak += 1
        check -= timedelta(days=1)
    streak_info = f"🔥 连续完成 {streak} 天" if streak > 0 else "从今天开始新的连续记录吧！"

    return EveningResponse(
        date=today.isoformat(),
        ai_summary=result.get("gap_analysis", ""),
        ai_problem=result.get("root_cause", ""),
        ai_next_action=(
            result["corrective_actions"][0]
            if result.get("corrective_actions")
            else None
        ),
        insights_extracted=insights_created,
        assets_identified=assets_created,
        streak_info=streak_info,
    )


# ---------------------------------------------------------------------------
# POST /api/loop/weekly/run
# ---------------------------------------------------------------------------

class WeeklyRunResponse(BaseModel):
    review: dict[str, Any]
    socratic_questions: list[str] = Field(default_factory=list)
    patterns: dict[str, Any] = Field(default_factory=dict)


@router.post("/weekly/run", response_model=WeeklyRunResponse)
async def weekly_run(week_start_date: Optional[str] = None):
    """Run the weekly review loop.

    1. Get 7 daily logs for the week
    2. Run A3 PatternFinder + A5 InsightMiner in parallel
    3. Create Review (period=week)
    4. Run A6 SocraticQuestioner
    """
    db = _get_db()
    today = date.today()

    if week_start_date:
        ws = date.fromisoformat(week_start_date)
    else:
        ws = today - timedelta(days=today.weekday())  # Monday
    we = ws + timedelta(days=6)

    # Get the week's logs
    logs = await db.get_daily_logs(start_date=ws, end_date=we, limit=7)

    llm = _get_llm()
    prompt_loader = _get_prompt_loader()

    # Run A3 PatternFinder and A5 InsightMiner in parallel
    pattern_finder = PatternFinderAgent(llm=llm, prompt_loader=prompt_loader, db=db)
    insight_miner = InsightMinerAgent(llm=llm, prompt_loader=prompt_loader, db=db)

    a3_input = PatternFinderInput(
        daily_logs=logs,
        time_range_start=ws,
        time_range_end=we,
    )

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
    except Exception as e:
        logger.error(f"Weekly agents failed: {e}")
        pattern_result = {"patterns": [], "summary": "Unable to analyze patterns."}
        insight_result = {"insights": [], "summary": "Unable to mine insights."}

    # Compute completion rate
    completed = sum(1 for l in logs if l.get("completed"))
    completion_rate = round(completed / len(logs), 2) if logs else 0.0

    # Count assets and insights for the week
    week_iso = ws.isoformat()
    assets = await db.get_assets(limit=200)
    insights = await db.get_insights(limit=200)
    assets_week = [a for a in assets if a.get("created_at", "") >= week_iso]
    insights_week = [i for i in insights if i.get("created_at", "") >= week_iso]

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
    review = await db.create_review(review_data)

    # Run A6 SocraticQuestioner
    socratic = SocraticQuestionerAgent(llm=llm, prompt_loader=prompt_loader, db=db)
    a6_input = SocraticQuestionerInput(
        topic="Weekly review reflection",
        current_understanding=pattern_result.get("summary", ""),
        recent_logs=logs,
    )

    try:
        socratic_result = await socratic.run(a6_input.model_dump())
        questions = socratic_result.get("questions", [])
    except Exception as e:
        logger.error(f"A6 SocraticQuestioner failed: {e}")
        questions = ["本周最大的收获是什么？", "下周你想改变的一件事是什么？"]

    return WeeklyRunResponse(
        review=review,
        socratic_questions=questions,
        patterns=pattern_result,
    )


# ---------------------------------------------------------------------------
# POST /api/loop/weekly/submit
# ---------------------------------------------------------------------------

@router.post("/weekly/submit")
async def weekly_submit(req: WeeklySubmitRequest):
    """Submit weekly review reflections."""
    db = _get_db()

    review = await db.get_review(str(req.review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    update_data: dict[str, Any] = {}
    if req.highlights is not None:
        update_data["highlights"] = req.highlights
    if req.problems is not None:
        update_data["problems"] = req.problems
    if req.next_actions is not None:
        update_data["next_actions"] = req.next_actions

    updated = await db.update_review(str(req.review_id), update_data)
    return {"review": updated, "status": "submitted"}


# ---------------------------------------------------------------------------
# POST /api/loop/monthly/run
# ---------------------------------------------------------------------------

class MonthlyRunResponse(BaseModel):
    review: dict[str, Any]
    stats: dict[str, Any] = Field(default_factory=dict)


@router.post("/monthly/run", response_model=MonthlyRunResponse)
async def monthly_run():
    """Run the monthly review loop.

    1. Aggregate 4 weekly reviews + asset stats
    2. Create Review (period=month) with stats
    """
    db = _get_db()
    today = date.today()

    # Current month boundaries
    month_start = today.replace(day=1)
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

    # Get weekly reviews for this month
    weekly_reviews = await db.get_reviews(period="week", limit=8)
    month_reviews = [
        r for r in weekly_reviews
        if r.get("start_date", "") >= month_start.isoformat()
    ]

    # Get monthly logs
    logs = await db.get_daily_logs(start_date=month_start, end_date=today, limit=31)
    completed = sum(1 for l in logs if l.get("completed"))
    total_focus = sum(l.get("focus_minutes", 0) for l in logs)

    # Asset and insight counts
    assets = await db.get_assets(limit=500)
    insights = await db.get_insights(limit=500)
    month_assets = [a for a in assets if a.get("created_at", "") >= month_start.isoformat()]
    month_insights = [i for i in insights if i.get("created_at", "") >= month_start.isoformat()]

    stats = {
        "days_logged": len(logs),
        "days_completed": completed,
        "completion_rate": round(completed / len(logs), 2) if logs else 0,
        "total_focus_minutes": total_focus,
        "weekly_reviews_count": len(month_reviews),
        "assets_created": len(month_assets),
        "insights_created": len(month_insights),
        "avg_mood": (
            round(sum(l.get("mood", 0) for l in logs if l.get("mood")) / max(1, len([l for l in logs if l.get("mood")])), 2)
        ),
        "avg_energy": (
            round(sum(l.get("energy", 0) for l in logs if l.get("energy")) / max(1, len([l for l in logs if l.get("energy")])), 2)
        ),
    }

    review_data = ReviewCreate(
        period=PeriodEnum.MONTH,
        start_date=month_start,
        end_date=month_end,
        completion_rate=stats["completion_rate"],
        asset_count=len(month_assets),
        insight_count=len(month_insights),
    )
    review = await db.create_review(review_data)

    return MonthlyRunResponse(review=review, stats=stats)


# ---------------------------------------------------------------------------
# POST /api/loop/quarterly/run
# ---------------------------------------------------------------------------

class QuarterlyRunResponse(BaseModel):
    calibration: dict[str, Any]
    review: dict[str, Any]


@router.post("/quarterly/run", response_model=QuarterlyRunResponse)
async def quarterly_run():
    """Run the quarterly calibration loop.

    1. Aggregate 3 months of data
    2. Run A7 DirectionCalibrator
    """
    db = _get_db()
    today = date.today()

    # Current quarter boundaries
    quarter = (today.month - 1) // 3
    q_start_month = quarter * 3 + 1
    quarter_start = date(today.year, q_start_month, 1)

    # Get all data for the quarter
    goals = await db.get_goals(limit=100)
    monthly_reviews = await db.get_reviews(period="month", limit=6)
    quarter_reviews = [
        r for r in monthly_reviews
        if r.get("start_date", "") >= quarter_start.isoformat()
    ]
    insights = await db.get_insights(limit=200)
    logs = await db.get_daily_logs(start_date=quarter_start, end_date=today, limit=100)

    # Run A7 DirectionCalibrator
    llm = _get_llm()
    prompt_loader = _get_prompt_loader()
    calibrator = DirectionCalibratorAgent(llm=llm, prompt_loader=prompt_loader, db=db)

    a7_input = DirectionCalibratorInput(
        goals=goals,
        recent_reviews=quarter_reviews,
        insights=insights[:50],
        current_life_areas=list(set(
            g.get("level", "general") for g in goals
        )),
        time_horizon="quarter",
    )

    try:
        calibration = await calibrator.run(a7_input.model_dump())
    except Exception as e:
        logger.error(f"A7 DirectionCalibrator failed: {e}")
        calibration = {
            "alignment_score": 5.0,
            "reasoning": "Unable to run calibration. Please try again.",
            "suggested_adjustments": [],
            "misaligned_goals": [],
            "new_direction_ideas": [],
        }

    # Create quarterly review record
    completed = sum(1 for l in logs if l.get("completed"))
    assets = await db.get_assets(limit=500)
    quarter_assets = [a for a in assets if a.get("created_at", "") >= quarter_start.isoformat()]

    review_data = ReviewCreate(
        period=PeriodEnum.QUARTER,
        start_date=quarter_start,
        end_date=today,
        completion_rate=round(completed / len(logs), 2) if logs else 0,
        asset_count=len(quarter_assets),
        insight_count=len([i for i in insights if i.get("created_at", "") >= quarter_start.isoformat()]),
        ai_pattern_analysis=calibration,
    )
    review = await db.create_review(review_data)

    return QuarterlyRunResponse(calibration=calibration, review=review)
