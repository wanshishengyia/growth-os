"""Goal CRUD endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.models.goal import GoalCreate, GoalUpdate
from backend.app.services.db_service import DBService

router = APIRouter(prefix="/api/goals", tags=["goals"])


def _get_db() -> DBService:
    return DBService()


@router.get("")
async def list_goals(
    status: Optional[str] = None,
    level: Optional[str] = None,
    parent_id: Optional[str] = None,
):
    """List goals with optional filters."""
    db = _get_db()
    goals = await db.get_goals(status=status, level=level, parent_id=parent_id)
    return {"goals": goals, "count": len(goals)}


@router.post("", status_code=201)
async def create_goal(data: GoalCreate):
    """Create a new goal."""
    db = _get_db()
    goal = await db.create_goal(data)
    return goal


@router.get("/{goal_id}")
async def get_goal(goal_id: str):
    """Get a single goal by ID."""
    db = _get_db()
    goal = await db.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.patch("/{goal_id}")
async def update_goal(goal_id: str, data: GoalUpdate):
    """Update a goal."""
    db = _get_db()
    existing = await db.get_goal(goal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Goal not found")
    updated = await db.update_goal(goal_id, data)
    return updated


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(goal_id: str):
    """Soft-delete a goal."""
    db = _get_db()
    existing = await db.get_goal(goal_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete_goal(goal_id)
    return None
