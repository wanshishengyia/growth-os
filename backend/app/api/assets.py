"""Asset CRUD endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.app.models.asset import AssetCreate, AssetType
from backend.app.models.schemas import AssetClassifierInput
from backend.app.services.db_service import DBService
from backend.app.services.llm_client import LLMClient
from backend.app.services.prompt_loader import PromptLoader
from backend.app.agents import AssetClassifierAgent

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _get_db() -> DBService:
    return DBService()


@router.get("")
async def list_assets(
    type: Optional[str] = None,
    tag: Optional[str] = None,
    related_goal_id: Optional[str] = None,
    q: Optional[str] = None,
):
    """List assets with optional filters.

    - type: filter by asset type (project, method, template, output, snippet)
    - tag: filter by tag presence
    - related_goal_id: filter by linked goal
    - q: text search in title/content
    """
    db = _get_db()
    assets = await db.get_assets(
        type=type,
        tag=tag,
        related_goal_id=related_goal_id,
        limit=200,
    )

    # Client-side text search if q is provided
    if q:
        q_lower = q.lower()
        assets = [
            a for a in assets
            if q_lower in (a.get("title", "") + " " + (a.get("content") or "")).lower()
        ]

    return {"assets": assets, "count": len(assets)}


@router.post("", status_code=201)
async def create_asset(data: AssetCreate, auto_classify: bool = False):
    """Create a new asset.

    If auto_classify=true, runs A4 AssetClassifier to auto-tag and classify.
    """
    db = _get_db()

    if auto_classify:
        llm = LLMClient()
        prompt_loader = PromptLoader()
        classifier = AssetClassifierAgent(llm=llm, prompt_loader=prompt_loader, db=db)

        a4_input = AssetClassifierInput(
            title=data.title,
            content=data.content,
            file_path=data.file_path,
            url=data.url,
            existing_tags=data.tags,
        )

        try:
            result = await classifier.run(a4_input.model_dump())
            # Enrich the asset with classifier output
            if not data.type:
                data.type = AssetType(result.get("asset_type", "snippet"))
            if result.get("suggested_tags"):
                data.tags = list(set(data.tags + result["suggested_tags"]))
            data.quality = result.get("quality_estimate", data.quality)
            data.ai_classification = result
        except Exception as e:
            # Proceed without classification on failure
            pass

    asset = await db.create_asset(data)
    return asset


@router.get("/{asset_id}")
async def get_asset(asset_id: str):
    """Get a single asset by ID."""
    db = _get_db()
    asset = await db.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
