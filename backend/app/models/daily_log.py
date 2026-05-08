from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DailyLogBase(BaseModel):
    log_date: date
    goal_id: Optional[UUID] = None
    core_task: Optional[str] = None
    min_action: Optional[str] = None
    judge_criteria: Optional[str] = None
    completed: bool = False
    completion_quality: Optional[int] = Field(default=None, ge=1, le=5)
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    energy: Optional[int] = Field(default=None, ge=1, le=5)
    focus_minutes: int = 0
    raw_notes: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_problem: Optional[str] = None
    ai_next_action: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DailyLogCreate(DailyLogBase):
    pass


class DailyLogUpdate(BaseModel):
    log_date: Optional[date] = None
    goal_id: Optional[UUID] = None
    core_task: Optional[str] = None
    min_action: Optional[str] = None
    judge_criteria: Optional[str] = None
    completed: Optional[bool] = None
    completion_quality: Optional[int] = Field(default=None, ge=1, le=5)
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    energy: Optional[int] = Field(default=None, ge=1, le=5)
    focus_minutes: Optional[int] = None
    raw_notes: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_problem: Optional[str] = None
    ai_next_action: Optional[str] = None
    tags: Optional[list[str]] = None


class DailyLog(DailyLogBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
