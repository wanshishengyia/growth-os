"""Insight CRUD endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.models.insight import InsightCreate
from backend.app.services.db_service import DBService

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _get_db() -> DBService:
    return DBService()


@router.get("")
async def list_insights(
    type: Optional[str] = None,
    tag: Optional[str] = None,
    min_confidence: Optional[int] = None,
):
    """List insights with optional filters."""
    db = _get_db()
    insights = await db.get_insights(
        type=type,
        tag=tag,
        min_confidence=min_confidence,
        limit=200,
    )
    return {"insights": insights, "count": len(insights)}


@router.post("", status_code=201)
async def create_insight(data: InsightCreate):
    """Create a new insight manually."""
    db = _get_db()
    insight = await db.create_insight(data)
    return insight


@router.get("/{insight_id}")
async def get_insight(insight_id: str):
    """Get a single insight by ID."""
    db = _get_db()
    insight = await db.get_insight(insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight
