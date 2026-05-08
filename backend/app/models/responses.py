from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class DashboardStats(BaseModel):
    total_goals: int = 0
    active_goals: int = 0
    completed_goals: int = 0
    total_logs: int = 0
    current_streak: int = 0
    total_focus_minutes: int = 0
    average_mood: Optional[float] = None
    average_energy: Optional[float] = None
    insights_this_week: int = 0
    assets_this_week: int = 0


class MorningResponse(BaseModel):
    date: str
    greeting: str
    todays_focus: Optional[str] = None
    pending_actions: list[str] = Field(default_factory=list)
    motivational_insight: Optional[str] = None
    related_insights: list[str] = Field(default_factory=list)


class EveningResponse(BaseModel):
    date: str
    ai_summary: Optional[str] = None
    ai_problem: Optional[str] = None
    ai_next_action: Optional[str] = None
    insights_extracted: list[dict[str, Any]] = Field(default_factory=list)
    assets_identified: list[dict[str, Any]] = Field(default_factory=list)
    streak_info: Optional[str] = None
