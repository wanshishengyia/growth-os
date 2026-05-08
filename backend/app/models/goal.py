from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GoalLevel(str, Enum):
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"
    WEEK = "week"
    STAGE = "stage"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"
    ABANDONED = "abandoned"


class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    level: GoalLevel
    parent_id: Optional[UUID] = None
    status: GoalStatus = GoalStatus.ACTIVE
    priority: int = Field(default=3, ge=1, le=5)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    tags: list[str] = Field(default_factory=list)


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level: Optional[GoalLevel] = None
    parent_id: Optional[UUID] = None
    status: Optional[GoalStatus] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    tags: Optional[list[str]] = None


class Goal(GoalBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
