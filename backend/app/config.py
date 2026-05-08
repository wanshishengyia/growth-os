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

    # ── SQLite ───────────────────────────────────────────────────────────
    sqlite_db_path: str = str(
        Path(__file__).resolve().parents[2] / "data" / "growth.db"
    )

    # ── AI / LLM (MiMo) ─────────────────────────────────────────────────
    mimo_api_key: str = ""
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    ai_model: str = "xiaomicoding/mimo-v2.5-pro"
    ai_monthly_budget_usd: float = 10.0
    openai_api_key: str = ""  # optional fallback

    # ── Feishu (Lark) ────────────────────────────────────────────────────
    feishu_webhook_url: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_user_id: str = ""

    # ── Telegram ──────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_user_id: str = ""

    # ── API ───────────────────────────────────────────────────────────────
    api_token: str = ""
    api_port: int = 8000

    # ── Scheduler ─────────────────────────────────────────────────────────
    scheduler_enabled: bool = True
    morning_time: str = "07:30"
    evening_time: str = "22:00"

    # ── Prompts directory ─────────────────────────────────────────────────
    prompts_dir: str = str(
        Path(__file__).resolve().parents[1] / "prompts"
    )


# Module-level singleton
settings = Settings()
