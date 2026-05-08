"""LLM client wrapper for Growth OS.

Handles API calls to OpenAI / Anthropic with retry, token counting,
and cost tracking.  Actual implementation will be filled in when the
agent layer is built; this is a minimal placeholder so imports work.
"""

from __future__ import annotations

import os
from typing import Any


class LLMClient:
    """Unified interface to LLM providers."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    async def complete(
        self,
        prompt: str,
        *,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Return {"text": str, "input_tokens": int, "output_tokens": int,
        "cost_usd": float, "latency_ms": int}."""
        raise NotImplementedError("LLMClient.complete will be implemented with agent layer")
