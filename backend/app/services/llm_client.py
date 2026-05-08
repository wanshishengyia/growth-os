"""LLM client wrapper for Growth OS.

Uses Xiaomi MiMo API (OpenAI-compatible) as the primary provider,
with OpenAI as fallback. Supports retry, token counting, and cost tracking.
"""

from __future__ import annotations

import json
import re
import asyncio
import logging
from typing import Any, Optional

import openai

logger = logging.getLogger(__name__)

# Cost per 1M tokens (approximate)
COST_MAP: dict[str, dict[str, float]] = {
    "mimo-v2.5-pro": {"input": 0.5, "output": 2.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
}


class LLMClient:
    """Unified LLM client using OpenAI-compatible API.

    Primary: Xiaomi MiMo API (token-plan-cn.xiaomimimo.com/v1)
    Fallback: OpenAI API (api.openai.com/v1)
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        fallback_api_key: str | None = None,
        fallback_base_url: str = "https://api.openai.com/v1",
        fallback_model: str = "gpt-4o-mini",
    ) -> None:
        from backend.app.config import settings

        # Primary provider — MiMo
        self.api_key = api_key or settings.mimo_api_key
        self.base_url = base_url or settings.mimo_base_url
        self.model = model or settings.ai_model
        self.client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # Fallback provider — OpenAI
        self.fallback_api_key = fallback_api_key or settings.openai_api_key
        self.fallback_base_url = fallback_base_url
        self.fallback_model = fallback_model
        self.fallback_client: openai.AsyncOpenAI | None = None
        if self.fallback_api_key:
            self.fallback_client = openai.AsyncOpenAI(
                api_key=self.fallback_api_key,
                base_url=self.fallback_base_url,
            )

        # Cost tracking
        self.total_cost_usd: float = 0.0
        self.usage_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API — matches the interface agents expect
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Send a chat completion request. Returns {content, input_tokens, output_tokens, model}.

        Tries the primary (MiMo) client first; falls back to OpenAI on failure.
        """
        model = model or self.model
        max_retries = 3

        # Try primary (MiMo) first
        try:
            return await self._call_api(
                self.client, model, messages, temperature, max_tokens, max_retries
            )
        except Exception as primary_err:
            logger.warning(f"Primary LLM ({model}) failed after retries: {primary_err}")
            if self.fallback_client:
                logger.info(f"Falling back to OpenAI ({self.fallback_model})")
                return await self._call_api(
                    self.fallback_client,
                    self.fallback_model,
                    messages,
                    temperature,
                    max_tokens,
                    max_retries,
                )
            raise

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Like chat(), but guarantees the response content is valid JSON.

        Returns {content: <json-string>, input_tokens, output_tokens, model}.
        """
        json_instruction = {
            "role": "system",
            "content": (
                "你必须只返回合法的JSON，不要包含任何解释文字、markdown标记或代码块包裹。"
                "只返回纯JSON。"
            ),
        }
        enhanced_messages = [json_instruction] + list(messages)

        result = await self.chat(
            enhanced_messages, model=model, temperature=temperature, max_tokens=max_tokens
        )

        content = result["content"].strip()
        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        try:
            json.loads(content)
            result["content"] = content
        except json.JSONDecodeError:
            # Try to extract the first JSON object from the content
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result["content"] = json_match.group()
            else:
                logger.error(f"Failed to parse JSON from LLM response: {content[:200]}")
                raise ValueError(f"LLM response is not valid JSON: {content[:100]}")

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _call_api(
        self,
        client: openai.AsyncOpenAI,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        max_retries: int,
    ) -> dict[str, Any]:
        """Call the OpenAI-compatible API with exponential-backoff retries."""
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                usage = response.usage
                result: dict[str, Any] = {
                    "content": response.choices[0].message.content or "",
                    "input_tokens": usage.prompt_tokens if usage else 0,
                    "output_tokens": usage.completion_tokens if usage else 0,
                    "model": model,
                }
                # Track cost
                cost = self._estimate_cost(result)
                self.total_cost_usd += cost
                self.usage_log.append(
                    {
                        "model": model,
                        "tokens_in": result["input_tokens"],
                        "tokens_out": result["output_tokens"],
                        "cost": cost,
                    }
                )
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    f"LLM attempt {attempt + 1}/{max_retries} failed ({model}): {exc}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        raise last_exc  # type: ignore[misc]

    def _estimate_cost(self, result: dict[str, Any]) -> float:
        """Estimate USD cost for a completion."""
        costs = COST_MAP.get(result["model"], COST_MAP["mimo-v2.5-pro"])
        input_cost = result["input_tokens"] * costs["input"] / 1_000_000
        output_cost = result["output_tokens"] * costs["output"] / 1_000_000
        return round(input_cost + output_cost, 6)
