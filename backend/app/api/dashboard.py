"""Dashboard statistics endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.models.responses import DashboardStats
from backend.app.services.db_service import DBService
from backend.app.services.rule_engine import rule_engine

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _get_db() -> DBService:
    return DBService()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get aggregated dashboard statistics.

    Returns goal counts, streak info, mood/energy averages,
    weekly asset/insight counts, and more.
    """
    db = _get_db()
    stats = await db.get_dashboard_stats()
    return stats


@router.get("/rules")
async def get_triggered_rules():
    """Run the business rule engine and return any triggered rules."""
    db = _get_db()
    triggered = await rule_engine.check_all_rules(db)
    return {
        "triggered_rules": triggered,
        "count": len(triggered),
    }
