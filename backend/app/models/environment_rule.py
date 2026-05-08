from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RuleType(str, Enum):
    BLOCK = "block"
    REMIND = "remind"
    TRIGGER = "trigger"
    FILTER = "filter"


class EnvironmentRuleBase(BaseModel):
    name: str
    type: Optional[RuleType] = None
    target: Optional[str] = None
    condition: Optional[dict[str, Any]] = None
    action: Optional[dict[str, Any]] = None
    active: bool = True
    last_triggered_at: Optional[datetime] = None
    trigger_count: int = 0


class EnvironmentRuleCreate(EnvironmentRuleBase):
    pass


class EnvironmentRule(EnvironmentRuleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
