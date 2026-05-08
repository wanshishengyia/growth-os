from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    PROJECT = "project"
    METHOD = "method"
    TEMPLATE = "template"
    OUTPUT = "output"
    SNIPPET = "snippet"


class AssetBase(BaseModel):
    type: AssetType
    title: str
    content: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None
    quality: int = Field(default=3, ge=1, le=5)
    reuse_count: int = 0
    tags: list[str] = Field(default_factory=list)
    ai_classification: Optional[dict[str, Any]] = None
    related_goal_id: Optional[UUID] = None
    related_log_id: Optional[UUID] = None


class AssetCreate(AssetBase):
    pass


class Asset(AssetBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
