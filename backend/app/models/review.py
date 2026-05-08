from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PeriodEnum(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"


class ReviewBase(BaseModel):
    period: PeriodEnum
    start_date: date
    end_date: date
    highlights: Optional[str] = None
    problems: Optional[str] = None
    next_actions: Optional[str] = None
    ai_pattern_analysis: Optional[dict] = None
    ai_questions: Optional[list[str]] = None
    completion_rate: Optional[float] = None
    asset_count: int = 0
    insight_count: int = 0


class ReviewCreate(ReviewBase):
    pass


class Review(ReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
