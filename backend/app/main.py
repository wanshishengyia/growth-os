"""Growth OS — FastAPI application entry point.

AI-driven personal growth operating system with 7 specialised agents
and 4 time-scale feedback loops.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import loops, goals, assets, insights, reviews, agents, dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Growth OS starting…")

    # ── Initialize SQLite schema ─────────────────────────────────────────
    from backend.app.services.supabase_client import init_schema
    try:
        init_schema()
        logger.info("SQLite schema initialized")
    except Exception as e:
        logger.error("Schema init failed: %s", e, exc_info=True)

    # ── Start APScheduler (replaces n8n workflows) ──────────────────────
    from backend.app.config import settings
    from backend.app.services.scheduler import GrowthScheduler
    from backend.app.services.db_service import DBService
    from backend.app.services.llm_client import LLMClient
    from backend.app.services.prompt_loader import PromptLoader
    from backend.app.services.feishu_messenger import FeishuMessenger

    scheduler: GrowthScheduler | None = None

    if settings.scheduler_enabled:
        try:
            db = DBService()
            llm = LLMClient()
            prompt_loader = PromptLoader()
            messenger = FeishuMessenger()

            scheduler = GrowthScheduler(
                db=db, llm=llm, prompt_loader=prompt_loader, messenger=messenger
            )
            scheduler.setup(
                morning_time=settings.morning_time,
                evening_time=settings.evening_time,
            )
            scheduler.start()
            logger.info("APScheduler started successfully")
        except Exception as e:
            logger.error("Failed to start APScheduler: %s", e, exc_info=True)
    else:
        logger.info("APScheduler disabled via config (scheduler_enabled=False)")

    yield

    # ── Shutdown ────────────────────────────────────────────────────────
    if scheduler is not None:
        try:
            scheduler.shutdown()
            logger.info("APScheduler stopped")
        except Exception as e:
            logger.error("Error stopping APScheduler: %s", e)

    logger.info("Growth OS shutting down…")


app = FastAPI(
    title="Personal Growth OS",
    description=(
        "AI-driven personal growth operating system with multi-scale "
        "feedback loops (daily / weekly / monthly / quarterly), "
        "7 specialised AI agents, asset management, and insight mining."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include all routers ─────────────────────────────────────────────────
app.include_router(loops.router)
app.include_router(goals.router)
app.include_router(assets.router)
app.include_router(insights.router)
app.include_router(reviews.router)
app.include_router(agents.router)
app.include_router(dashboard.router)


# ── Health check ────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    """Simple liveness probe."""
    return {"status": "ok", "version": "1.0.0"}
