"""Supabase client singleton for Growth OS."""

from __future__ import annotations

import logging
from typing import Optional

from supabase import Client, create_client

from backend.app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


class SupabaseConnectionError(RuntimeError):
    """Raised when Supabase client cannot be initialised."""


def get_client() -> Client:
    """Return (and lazily initialise) the Supabase client singleton.

    Raises:
        SupabaseConnectionError: If required settings are missing or
            the client cannot be created.
    """
    global _client
    if _client is not None:
        return _client

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SupabaseConnectionError(
            "Supabase URL and service-role key must be set in the environment."
        )

    try:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
        logger.info("Supabase client initialised (%s)", settings.supabase_url)
    except Exception as exc:
        raise SupabaseConnectionError(
            f"Failed to initialise Supabase client: {exc}"
        ) from exc

    return _client


def reset_client() -> None:
    """Reset the cached client (useful for tests)."""
    global _client
    _client = None
