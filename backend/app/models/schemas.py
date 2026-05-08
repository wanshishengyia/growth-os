"""Agent I/O Pydantic models for all Growth OS AI agents."""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action Decider
# ---------------------------------------------------------------------------

class ActionDeciderInput(BaseModel):
    goal_title: str
    goal_description: Optional[str] = None
    goal_level: str
    current_progress: float = Field(ge=0, le=100)
    days_remaining: Optional[int] = Field(default=None, ge=0)
    recent_logs: list[dict[str, Any]] = Field(default_factory=list)
    recent_insights: list[str] = Field(default_factory=list)
    energy_level: Optional[int] = Field(default=None, ge=1, le=5)
    available_hours: Optional[float] = Field(default=None, ge=0)


class ActionDeciderOutput(BaseModel):
    next_action: str
    reasoning: str
    estimated_minutes: Optional[int] = Field(default=None, ge=0)
    priority_score: float = Field(ge=0, le=10)
    suggested_time: Optional[str] = None


# ---------------------------------------------------------------------------
# Loop Closer
# ---------------------------------------------------------------------------

class LoopCloserInput(BaseModel):
    goal_id: UUID
    goal_title: str
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    daily_logs: list[dict[str, Any]] = Field(default_factory=list)
    review_highlights: Optional[str] = None
    review_problems: Optional[str] = None
    completion_rate: Optional[float] = Field(default=None, ge=0, le=1)


class LoopCloserOutput(BaseModel):
    loop_status: str = Field(description="open | partial | closed")
    gap_analysis: str
    root_cause: Optional[str] = None
    corrective_actions: list[str] = Field(default_factory=list)
    pattern_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Pattern Finder
# ---------------------------------------------------------------------------

class PatternFinderInput(BaseModel):
    daily_logs: list[dict[str, Any]] = Field(default_factory=list)
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    time_range_start: Optional[date] = None
    time_range_end: Optional[date] = None
    focus_area: Optional[str] = None


class PatternFinderOutput(BaseModel):
    patterns: list[dict[str, Any]] = Field(default_factory=list)
    correlations: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    summary: str


# ---------------------------------------------------------------------------
# Asset Classifier
# ---------------------------------------------------------------------------

class AssetClassifierInput(BaseModel):
    title: str
    content: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None
    context: Optional[str] = None
    existing_tags: list[str] = Field(default_factory=list)


class AssetClassifierOutput(BaseModel):
    asset_type: str = Field(description="project | method | template | output | snippet")
    suggested_tags: list[str] = Field(default_factory=list)
    quality_estimate: int = Field(ge=1, le=5)
    summary: Optional[str] = None
    classification_reasoning: Optional[str] = None


# ---------------------------------------------------------------------------
# Insight Miner
# ---------------------------------------------------------------------------

class InsightMinerInput(BaseModel):
    raw_notes: str
    log_date: Optional[date] = None
    goal_context: Optional[str] = None
    recent_insights: list[str] = Field(default_factory=list)
    mood: Optional[int] = Field(default=None, ge=1, le=5)
    energy: Optional[int] = Field(default=None, ge=1, le=5)


class InsightMinerOutput(BaseModel):
    insights: list[dict[str, Any]] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    principles: list[str] = Field(default_factory=list)
    summary: str
    raw_emotions: Optional[str] = None


# ---------------------------------------------------------------------------
# Socratic Questioner
# ---------------------------------------------------------------------------

class SocraticQuestionerInput(BaseModel):
    topic: str
    current_understanding: Optional[str] = None
    goal_context: Optional[str] = None
    recent_logs: list[dict[str, Any]] = Field(default_factory=list)
    depth_level: int = Field(default=1, ge=1, le=5)
    user_mood: Optional[int] = Field(default=None, ge=1, le=5)


class SocraticQuestionerOutput(BaseModel):
    questions: list[str] = Field(min_length=1)
    reflection_prompt: Optional[str] = None
    underlying_assumption: Optional[str] = None
    suggested_experiment: Optional[str] = None


# ---------------------------------------------------------------------------
# Direction Calibrator
# ---------------------------------------------------------------------------

class DirectionCalibratorInput(BaseModel):
    goals: list[dict[str, Any]] = Field(default_factory=list)
    recent_reviews: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    current_life_areas: list[str] = Field(default_factory=list)
    time_horizon: str = Field(default="quarter", description="month | quarter | year")


class DirectionCalibratorOutput(BaseModel):
    alignment_score: float = Field(ge=0, le=10)
    misaligned_goals: list[dict[str, Any]] = Field(default_factory=list)
    suggested_adjustments: list[str] = Field(default_factory=list)
    new_direction_ideas: list[str] = Field(default_factory=list)
    reasoning: str
