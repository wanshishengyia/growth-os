"""Review list/detail endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.services.db_service import DBService

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _get_db() -> DBService:
    return DBService()


@router.get("")
async def list_reviews(period: Optional[str] = None):
    """List reviews, optionally filtered by period (week, month, quarter)."""
    db = _get_db()
    reviews = await db.get_reviews(period=period, limit=50)
    return {"reviews": reviews, "count": len(reviews)}


@router.get("/{review_id}")
async def get_review(review_id: str):
    """Get a single review by ID."""
    db = _get_db()
    review = await db.get_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review
