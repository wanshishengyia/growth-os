from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InsightType(str, Enum):
    QUESTION = "question"
    INSIGHT = "insight"
    PRINCIPLE = "principle"
    MODEL = "model"


class SourceType(str, Enum):
    DAILY_LOG = "daily_log"
    REVIEW = "review"
    MANUAL = "manual"
    EXTERNAL = "external"


class InsightBase(BaseModel):
    type: InsightType
    content: str
    context: Optional[str] = None
    source_type: Optional[SourceType] = None
    source_id: Optional[UUID] = None
    confidence: int = Field(default=3, ge=1, le=5)
    validated_count: int = 0
    tags: list[str] = Field(default_factory=list)
    related_goal_ids: list[UUID] = Field(default_factory=list)


class InsightCreate(InsightBase):
    pass


class Insight(InsightBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
