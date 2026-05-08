"""Direct agent call endpoints.

Each endpoint accepts the agent's input schema and returns the output.
Useful for testing, debugging, or manual triggering of individual agents.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.models.schemas import (
    ActionDeciderInput,
    ActionDeciderOutput,
    LoopCloserInput,
    LoopCloserOutput,
    PatternFinderInput,
    PatternFinderOutput,
    AssetClassifierInput,
    AssetClassifierOutput,
    InsightMinerInput,
    InsightMinerOutput,
    SocraticQuestionerInput,
    SocraticQuestionerOutput,
    DirectionCalibratorInput,
    DirectionCalibratorOutput,
)
from backend.app.services.db_service import DBService
from backend.app.services.llm_client import LLMClient
from backend.app.services.prompt_loader import PromptLoader
from backend.app.agents import (
    ActionDeciderAgent,
    LoopCloserAgent,
    PatternFinderAgent,
    AssetClassifierAgent,
    InsightMinerAgent,
    SocraticQuestionerAgent,
    DirectionCalibratorAgent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get_deps() -> tuple[LLMClient, PromptLoader, DBService]:
    return LLMClient(), PromptLoader(), DBService()


# ---------------------------------------------------------------------------
# POST /api/agents/action_decider
# ---------------------------------------------------------------------------

@router.post("/action_decider")
async def call_action_decider(data: ActionDeciderInput) -> dict[str, Any]:
    """Run A1 ActionDecider agent directly."""
    llm, pl, db = _get_deps()
    agent = ActionDeciderAgent(llm=llm, prompt_loader=pl, db=db)
    try:
        result = await agent.run(data.model_dump())
        return {"agent": "action_decider", "output": result}
    except Exception as e:
        logger.error(f"ActionDecider failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/agents/loop_closer
# ---------------------------------------------------------------------------

@router.post("/loop_closer")
async def call_loop_closer(data: LoopCloserInput) -> dict[str, Any]:
    """Run A2 LoopCloser agent directly."""
    llm, pl, db = _get_deps()
    agent = LoopCloserAgent(llm=llm, prompt_loader=pl, db=db)
    try:
        result = await agent.run(data.model_dump())
        return {"agent": "loop_closer", "output": result}
    except Exception as e:
        logger.error(f"LoopCloser failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/agents/pattern_finder
# ---------------------------------------------------------------------------

@router.post("/pattern_finder")
async def call_pattern_finder(data: PatternFinderInput) -> dict[str, Any]:
    """Run A3 PatternFinder agent directly."""
    llm, pl, db = _get_deps()
    agent = PatternFinderAgent(llm=llm, prompt_loader=pl, db=db)
    try:
        result = await agent.run(data.model_dump())
        return {"agent": "pattern_finder", "output": result}
    except Exception as e:
        logger.error(f"PatternFinder failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/agents/asset_classifier
# ---------------------------------------------------------------------------

@router.post("/asset_classifier")
async def call_asset_classifier(data: AssetClassifierInput) -> dict[str, Any]:
    """Run A4 AssetClassifier agent directly."""
    llm, pl, db = _get_deps()
    agent = AssetClassifierAgent(llm=llm, prompt_loader=pl, db=db)
    try:
        result = await agent.run(data.model_dump())
        return {"agent": "asset_classifier", "output": result}
    except Exception as e:
        logger.error(f"AssetClassifier failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/agents/insight_miner
# ---------------------------------------------------------------------------

@router.post("/insight_miner")
async def call_insight_miner(data: InsightMinerInput) -> dict[str, Any]:
    """Run A5 InsightMiner agent directly."""
    llm, pl, db = _get_deps()
    agent = InsightMinerAgent(llm=llm, prompt_loader=pl, db=db)
    try:
        result = await agent.run(data.model_dump())
        return {"agent": "insight_miner", "output": result}
    except Exception as e:
        logger.error(f"InsightMiner failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/agents/socratic_questioner
# ---------------------------------------------------------------------------

@router.post("/socratic_questioner")
async def call_socratic_questioner(data: SocraticQuestionerInput) -> dict[str, Any]:
    """Run A6 SocraticQuestioner agent directly."""
    llm, pl, db = _get_deps()
    agent = SocraticQuestionerAgent(llm=llm, prompt_loader=pl, db=db)
    try:
        result = await agent.run(data.model_dump())
        return {"agent": "socratic_questioner", "output": result}
    except Exception as e:
        logger.error(f"SocraticQuestioner failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")


# ---------------------------------------------------------------------------
# POST /api/agents/direction_calibrator
# ---------------------------------------------------------------------------

@router.post("/direction_calibrator")
async def call_direction_calibrator(data: DirectionCalibratorInput) -> dict[str, Any]:
    """Run A7 DirectionCalibrator agent directly."""
    llm, pl, db = _get_deps()
    agent = DirectionCalibratorAgent(llm=llm, prompt_loader=pl, db=db)
    try:
        result = await agent.run(data.model_dump())
        return {"agent": "direction_calibrator", "output": result}
    except Exception as e:
        logger.error(f"DirectionCalibrator failed: {e}")
        raise HTTPException(status_code=502, detail=f"Agent error: {str(e)}")
