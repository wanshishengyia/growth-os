from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EveningSubmitRequest(BaseModel):
    raw_notes: str
    mood: int = Field(ge=1, le=5)
    energy: int = Field(ge=1, le=5)
    completed: Optional[bool] = None
    focus_minutes: Optional[int] = Field(default=None, ge=0)


class WeeklySubmitRequest(BaseModel):
    review_id: UUID
    highlights: Optional[str] = None
    problems: Optional[str] = None
    next_actions: Optional[str] = None
