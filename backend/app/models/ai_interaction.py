from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AIStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class AIInteractionBase(BaseModel):
    agent_name: str
    prompt_version: Optional[str] = None
    input: dict[str, Any]
    output: Optional[dict[str, Any]] = None
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    status: Optional[AIStatus] = None
    error_message: Optional[str] = None
    related_table: Optional[str] = None
    related_id: Optional[UUID] = None


class AIInteractionCreate(AIInteractionBase):
    pass


class AIInteraction(AIInteractionBase):
    id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
