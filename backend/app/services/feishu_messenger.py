"""
Growth OS - Feishu (飞书) Messaging Integration

Replaces the former Telegram Bot. Uses Feishu webhook or Bot API
to deliver formatted messages (cards) to the user.

Provides the same message types as the former bot:
  - morning decision
  - evening loop-closer
  - weekly review
  - system status
  - assets list
  - insights list
  - alerts
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class FeishuMessenger:
    """Send messages to Feishu via Incoming Webhook or Bot API.

    Parameters
    ----------
    webhook_url : str, optional
        Feishu Incoming Webhook URL for a group chat bot.
    app_id : str, optional
        Feishu app ID (for Bot API direct messages).
    app_secret : str, optional
        Feishu app secret (for Bot API direct messages).
    user_id : str, optional
        Default Feishu user open_id to send DMs to.
    """

    def __init__(
        self,
        webhook_url: str | None = None,
        app_id: str | None = None,
        app_secret: str | None = None,
        user_id: str | None = None,
    ) -> None:
        from backend.app.config import settings

        self.webhook_url: str = webhook_url or settings.feishu_webhook_url
        self.app_id: str = app_id or settings.feishu_app_id
        self.app_secret: str = app_secret or settings.feishu_app_secret
        self.user_id: str = user_id or settings.feishu_user_id
        self._tenant_token: str | None = None

    # ------------------------------------------------------------------
    # Low-level send helpers
    # ------------------------------------------------------------------

    async def _post_json(self, url: str, payload: dict) -> dict | None:
        """POST JSON and return parsed response or None on failure."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                # Feishu API returns {"code": 0, ...} on success
                if data.get("code", 0) != 0:
                    logger.error("Feishu API error: %s", data)
                    return None
                return data
            except Exception as e:
                logger.error("Feishu POST failed: %s", e)
                return None

    async def _get_tenant_token(self) -> str | None:
        """Obtain a tenant_access_token for Bot API calls."""
        if self._tenant_token:
            return self._tenant_token
        if not self.app_id or not self.app_secret:
            return None

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code", 0) != 0:
                    logger.error("Feishu token error: %s", data)
                    return None
                self._tenant_token = data.get("tenant_access_token")
                return self._tenant_token
            except Exception as e:
                logger.error("Feishu token request failed: %s", e)
                return None

    # ------------------------------------------------------------------
    # Webhook senders
    # ------------------------------------------------------------------

    async def send_text(self, text: str, user_id: str | None = None) -> None:
        """Send a plain-text message via webhook."""
        if not self.webhook_url:
            logger.warning("Feishu webhook not configured, skipping text message")
            return

        payload = {
            "msg_type": "text",
            "content": {"text": text},
        }
        await self._post_json(self.webhook_url, payload)
        logger.info("Feishu text sent: %s…", text[:80])

    async def send_card(
        self,
        title: str,
        content: str,
        color: str = "blue",
    ) -> None:
        """Send an interactive card message via webhook.

        Parameters
        ----------
        title : str
            Card header title.
        content : str
            Card body in **Lark Markdown** (lark_md).
        color : str
            Header template colour: blue, green, purple, red, indigo, orange, etc.
        """
        if not self.webhook_url:
            logger.warning("Feishu webhook not configured, skipping card")
            return

        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": color,
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": content},
                    }
                ],
            },
        }
        await self._post_json(self.webhook_url, card)
        logger.info("Feishu card sent: %s", title)

    # ------------------------------------------------------------------
    # Bot API direct message sender (optional, requires app credentials)
    # ------------------------------------------------------------------

    async def send_dm(self, text: str, user_id: str | None = None) -> None:
        """Send a direct message via the Feishu Bot API.

        Falls back to webhook if Bot API is not configured.
        """
        uid = user_id or self.user_id
        token = await self._get_tenant_token()

        if not token or not uid:
            # Fallback to webhook
            await self.send_text(text, user_id)
            return

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        import json as _json

        payload = {
            "receive_id": uid,
            "msg_type": "text",
            "content": _json.dumps({"text": text}),
        }
        params = {"receive_id_type": "open_id"}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url, json=payload, headers=headers, params=params, timeout=10
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code", 0) != 0:
                    logger.error("Feishu DM error: %s", data)
                else:
                    logger.info("Feishu DM sent to %s", uid)
            except Exception as e:
                logger.error("Feishu DM failed: %s", e)

    async def send_dm_card(
        self,
        title: str,
        content: str,
        color: str = "blue",
        user_id: str | None = None,
    ) -> None:
        """Send a card as a direct message via Bot API.

        Falls back to webhook card if Bot API is not configured.
        """
        uid = user_id or self.user_id
        token = await self._get_tenant_token()

        if not token or not uid:
            await self.send_card(title, content, color)
            return

        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        import json as _json

        card = {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": content},
                }
            ],
        }

        payload = {
            "receive_id": uid,
            "msg_type": "interactive",
            "content": _json.dumps(card),
        }
        params = {"receive_id_type": "open_id"}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url, json=payload, headers=headers, params=params, timeout=10
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code", 0) != 0:
                    logger.error("Feishu DM card error: %s", data)
                else:
                    logger.info("Feishu DM card sent to %s", uid)
            except Exception as e:
                logger.error("Feishu DM card failed: %s", e)

    # ==================================================================
    # Domain-specific message formatters
    # ==================================================================

    async def send_morning(self, result: dict[str, Any]) -> None:
        """Send morning decision formatted card."""
        core_task = result.get("core_task", "—")
        min_action = result.get("min_action", "—")
        judge_criteria = result.get("judge_criteria", "—")
        estimated_minutes = result.get("estimated_minutes", "?")
        reasoning = result.get("reasoning", "—")
        alternatives = result.get("alternatives", [])

        alt_lines = ""
        for i, alt in enumerate(alternatives[:3], 1):
            task = alt.get("task", alt) if isinstance(alt, dict) else alt
            reason = alt.get("reason", "") if isinstance(alt, dict) else ""
            suffix = f" — {reason}" if reason else ""
            alt_lines += f"\n{i}. {task}{suffix}"

        content = (
            f"🎯 **今日核心**\n\n"
            f"**核心任务**: {core_task}\n"
            f"**最小起步**: {min_action}\n"
            f"**判断标准**: {judge_criteria}\n"
            f"**预估时间**: {estimated_minutes} 分钟\n\n"
            f"💡 **理由**: {reasoning}\n\n"
            f"📋 **备选方案**:{alt_lines}"
        )

        await self.send_card("☀️ 早安 · 今日决策", content, "blue")

    async def send_evening(self, result: dict[str, Any]) -> None:
        """Send evening loop-closer formatted card."""
        summary = result.get("ai_summary", result.get("summary", "—"))
        problem = result.get("ai_problem", result.get("problem", "—"))
        next_action = result.get("ai_next_action", result.get("next_action", "—"))
        tags = result.get("tags", [])

        content = (
            f"📝 **今日闭环**\n\n"
            f"**核心收获**: {summary}\n"
            f"**暴露问题**: {problem}\n"
            f"**明日修正**: {next_action}\n\n"
            f"🏷️ **标签**: {', '.join(tags) if tags else '—'}"
        )

        assets = result.get("asset_candidates", [])
        if assets:
            content += "\n\n📦 **可沉淀资产**:"
            for a in assets:
                atype = a.get("type", "—") if isinstance(a, dict) else "—"
                title = a.get("title", str(a)) if isinstance(a, dict) else str(a)
                content += f"\n- [{atype}] {title}"

        await self.send_card("🌙 晚安 · 今日分析", content, "green")

    async def send_review(self, review: dict[str, Any], questions: list | None = None) -> None:
        """Send weekly review card."""
        summary = review.get("summary", "—")
        completion_rate = review.get("completion_rate", 0)
        asset_count = review.get("asset_count", 0)
        insight_count = review.get("insight_count", 0)

        content = (
            f"📊 **周复盘**\n\n"
            f"**完成率**: {completion_rate:.0f}%\n"
            f"**资产新增**: {asset_count}\n"
            f"**洞察新增**: {insight_count}\n\n"
            f"📈 **总结**: {summary}"
        )

        if questions:
            content += "\n\n❓ **AI 提问**:"
            for q in questions:
                q_text = q.get("question", q) if isinstance(q, dict) else q
                content += f"\n- {q_text}"

        await self.send_card("📋 周复盘", content, "purple")

    async def send_status(self, stats: dict[str, Any]) -> None:
        """Send dashboard status card."""
        completion_rate = stats.get("completion_rate_30d", 0)
        streak_days = stats.get("streak_days", stats.get("current_streak", 0))
        assets_total = stats.get("assets_total", stats.get("assets_this_week", 0))
        insights_total = stats.get("insights_total", 0)
        ai_cost = stats.get("ai_cost_this_month_usd", 0)

        content = (
            f"📊 **系统状态**\n\n"
            f"**30天完成率**: {completion_rate:.0f}%\n"
            f"**连续天数**: {streak_days}\n"
            f"**资产总数**: {assets_total}\n"
            f"**本月洞察**: {insights_total}\n"
            f"**本月AI成本**: ${ai_cost:.2f}"
        )

        await self.send_card("📊 系统状态", content, "indigo")

    async def send_assets(self, assets: list[dict[str, Any]]) -> None:
        """Send recent assets list card."""
        if not assets:
            await self.send_text("🗂 暂无资产。")
            return

        content = ""
        for a in assets:
            created = (a.get("created_at") or "—")[:10]
            title = a.get("title", "无标题")
            asset_type = a.get("type", "—")
            content += f"• **[{created}]** {title} ({asset_type})\n"

        await self.send_card("🗂 最近资产", content.strip(), "orange")

    async def send_insights(self, insights: list[dict[str, Any]]) -> None:
        """Send recent insights list card."""
        if not insights:
            await self.send_text("💡 暂无洞察。")
            return

        content = ""
        for ins in insights:
            conf = ins.get("confidence", 0)
            text = ins.get("text", "—")
            content += f"• [{conf}%] {text}\n"

        await self.send_card("💡 最近洞察", content.strip(), "yellow")

    async def send_alert(self, title: str, message: str) -> None:
        """Send an alert/warning card (red)."""
        await self.send_card(f"⚠️ {title}", message, "red")

    async def send_welcome(self) -> None:
        """Send welcome / help message."""
        content = (
            "这是一个 AI 驱动的个人成长系统，帮你：\n"
            "• 🎯 每天聚焦核心任务\n"
            "• 📝 复盘并持续改进\n"
            "• 📊 追踪成长数据\n\n"
            "**使用方式**\n"
            "通过 FastAPI 接口调用：\n"
            "- `POST /api/loops/morning` — 今日任务规划\n"
            "- `POST /api/loops/night` — 晚间复盘\n"
            "- `POST /api/reviews/weekly` — 本周复盘\n"
            "- `GET /api/dashboard/stats` — 系统状态\n"
            "- `GET /api/assets` — 最近资产\n"
            "- `GET /api/insights` — AI 洞察\n"
        )
        await self.send_card("🚀 欢迎使用 Growth OS！", content, "blue")
