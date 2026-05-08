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
    yield
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
