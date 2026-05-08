"""Growth OS configuration — loaded from .env via pydantic-settings."""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: str = ""

    # ── AI / LLM ──────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    ai_primary_provider: str = "claude"
    ai_monthly_budget_usd: float = 10.0

    # ── Telegram ──────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_user_id: str = ""

    # ── API ───────────────────────────────────────────────────────────────
    api_token: str = ""
    api_port: int = 8000

    # ── Prompts directory ─────────────────────────────────────────────────
    prompts_dir: str = str(
        Path(__file__).resolve().parents[1] / "prompts"
    )


# Module-level singleton
settings = Settings()
