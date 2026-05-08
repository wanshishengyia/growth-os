"""
Growth OS - Telegram Bot Integration
python-telegram-bot v21+ (async)

Provides commands: /start, /help, /morning, /night, /review, /status, /assets, /insights
"""

import logging
from datetime import date, timedelta
from typing import Any, Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from backend.app.models.daily_log import DailyLogCreate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conversation state helpers (dict-based state machine for /night flow)
# ---------------------------------------------------------------------------

NIGHT_STEP_WAITING_NOTES = "waiting_notes"
NIGHT_STEP_WAITING_MOOD = "waiting_mood"
NIGHT_STEP_WAITING_ENERGY = "waiting_energy"


def _get_conv(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> dict:
    convs: dict = context.bot_data.setdefault("conversations", {})
    return convs.setdefault(chat_id, {})


def _clear_conv(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    context.bot_data.setdefault("conversations", {}).pop(chat_id, None)


# ---------------------------------------------------------------------------
# Inline keyboard helpers
# ---------------------------------------------------------------------------

MOOD_LABELS = {1: "😫", 2: "😟", 3: "😐", 4: "🙂", 5: "😊"}
ENERGY_LABELS = {1: "😫", 2: "😟", 3: "😐", 4: "🙂", 5: "😊"}


def _mood_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"{MOOD_LABELS[i]} {i}", callback_data=f"mood:{i}")
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup([buttons])


def _energy_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"{ENERGY_LABELS[i]} {i}", callback_data=f"energy:{i}")
        for i in range(1, 6)
    ]
    return InlineKeyboardMarkup([buttons])


# ---------------------------------------------------------------------------
# GrowthBot
# ---------------------------------------------------------------------------

class GrowthBot:
    """Telegram bot front-end for Growth OS.

    Parameters
    ----------
    token : str
        Telegram bot API token (``settings.telegram_bot_token``).
    db : DBService
        Data-access layer instance.
    agents : dict
        Mapping of agent names to ``BaseAgent`` instances, e.g.
        ``{"A1_action_decider": ActionDeciderAgent(...), "A2_loop_closer": LoopCloserAgent(...)}``.
    """

    def __init__(self, token: str, db: Any, agents: dict[str, Any]) -> None:
        self.token = token
        self.db = db
        self.agents = agents
        self._app: Optional[Application] = None

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(self) -> Application:
        """Build and configure the :class:`Application`, register all handlers."""
        app = ApplicationBuilder().token(self.token).build()

        # Store shared objects on bot_data so handlers can access them
        app.bot_data["db"] = self.db
        app.bot_data["agents"] = self.agents
        app.bot_data["conversations"] = {}

        # Command handlers
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("help", self._cmd_help))
        app.add_handler(CommandHandler("morning", self._cmd_morning))
        app.add_handler(CommandHandler("night", self._cmd_night))
        app.add_handler(CommandHandler("review", self._cmd_review))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(CommandHandler("assets", self._cmd_assets))
        app.add_handler(CommandHandler("insights", self._cmd_insights))

        # Callback query handler for inline keyboards (mood / energy buttons)
        app.add_handler(CallbackQueryHandler(self._on_callback))

        # Catch-all for plain text messages during /night conversation
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_text)
        )

        # Error handler
        app.add_error_handler(self._on_error)

        self._app = app
        return app

    # ------------------------------------------------------------------
    # /start
    # ------------------------------------------------------------------

    async def _cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        welcome = (
            "🚀 *欢迎使用 Growth OS！*\n\n"
            "这是一个 AI 驱动的个人成长系统，帮你：\n"
            "• 🎯 每天聚焦核心任务\n"
            "• 📝 复盘并持续改进\n"
            "• 📊 追踪成长数据\n\n"
            "可用命令：\n"
            "/morning \\- 今日任务规划\n"
            "/night \\- 晚间复盘\n"
            "/review \\- 本周复盘\n"
            "/status \\- 系统状态\n"
            "/assets \\- 最近资产\n"
            "/insights \\- AI 洞察\n"
            "/help \\- 帮助\n"
        )
        await update.message.reply_text(welcome, parse_mode="MarkdownV2")

    # ------------------------------------------------------------------
    # /help
    # ------------------------------------------------------------------

    async def _cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        text = (
            "📖 *命令列表*\n\n"
            "🌅 /morning \\- AI 生成今日核心任务与行动建议\n"
            "🌙 /night \\- 晚间复盘，记录今日情况与 AI 分析\n"
            "📋 /review \\- 生成本周复盘报告\n"
            "📊 /status \\- 查看系统运行状态与数据概览\n"
            "🗂 /assets \\- 列出最近 5 条资产\n"
            "💡 /insights \\- 列出最近 5 条 AI 洞察\n"
            "❓ /help \\- 显示本帮助\n"
        )
        await update.message.reply_text(text, parse_mode="MarkdownV2")

    # ------------------------------------------------------------------
    # /morning
    # ------------------------------------------------------------------

    async def _cmd_morning(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        agents: dict = context.bot_data["agents"]

        await update.message.reply_text("🌅 正在规划今日任务…")

        try:
            a1 = agents.get("A1_action_decider")
            if a1 is None:
                await update.message.reply_text("⚠️ A1 代理未配置。")
                return

            # BaseAgent.run() takes a single input_data dict.
            # ActionDeciderAgent.build_variables() pulls context from self.db.
            result = await a1.run(input_data={
                "date": date.today().isoformat(),
            })

            core_task = result.get("core_task", "—")
            min_action = result.get("min_action", "—")
            judge_criteria = result.get("judge_criteria", "—")
            estimated_minutes = result.get("estimated_minutes", "?")
            reasoning = result.get("reasoning", "—")
            alternatives = result.get("alternatives", [])

            alt_lines = ""
            for idx, alt in enumerate(alternatives[:2], 1):
                alt_lines += f"  {idx}\\. {alt}\n"

            msg = (
                f"🎯 *今日核心*\n"
                f"任务: {core_task}\n"
                f"起步: {min_action}\n"
                f"标准: {judge_criteria}\n"
                f"预估: {estimated_minutes}分钟\n\n"
                f"💡 理由: {reasoning}\n\n"
                f"📋 备选:\n{alt_lines}"
            )
            await update.message.reply_text(msg, parse_mode="MarkdownV2")

        except Exception as e:
            logger.exception("Error in /morning: %s", e)
            await update.message.reply_text(
                "暂时无法处理，请稍后再试。"
            )

    # ------------------------------------------------------------------
    # /night  (multi-step conversation)
    # ------------------------------------------------------------------

    async def _cmd_night(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        chat_id = update.effective_chat.id
        _clear_conv(context, chat_id)
        _get_conv(context, chat_id)["step"] = NIGHT_STEP_WAITING_NOTES
        await update.message.reply_text("🌙 今天怎么样？写几句话即可。")

    # ------------------------------------------------------------------
    # /review
    # ------------------------------------------------------------------

    async def _cmd_review(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        db: Any = context.bot_data["db"]
        agents: dict = context.bot_data["agents"]

        await update.message.reply_text("📋 正在生成本周复盘…")

        try:
            week_ago = date.today() - timedelta(days=7)
            week_entries = await db.get_daily_logs(
                start_date=week_ago, end_date=date.today(), limit=7
            )

            a2 = agents.get("A2_loop_closer")
            if a2 is None:
                await update.message.reply_text("⚠️ A2 代理未配置。")
                return

            review = await a2.run(input_data={
                "mode": "weekly_review",
                "week_entries": week_entries,
                "date": date.today().isoformat(),
            })

            msg = (
                f"📋 *本周复盘*\n\n"
                f"📈 总结:\n{review.get('summary', '—')}\n\n"
                f"❓ AI 提问:\n"
            )
            for q in review.get("questions", []):
                msg += f"• {q}\n"

            await update.message.reply_text(msg, parse_mode="MarkdownV2")

        except Exception as e:
            logger.exception("Error in /review: %s", e)
            await update.message.reply_text(
                "暂时无法处理，请稍后再试。"
            )

    # ------------------------------------------------------------------
    # /status
    # ------------------------------------------------------------------

    async def _cmd_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        db: Any = context.bot_data["db"]

        try:
            stats = await db.get_dashboard_stats()
            cost = await db.get_monthly_cost()

            msg = (
                f"📊 *系统状态*\n\n"
                f"30天完成率: {round(stats.current_streak and stats.total_logs and (stats.current_streak / max(stats.total_logs, 1) * 100) or 0)}%\n"
                f"连续天数: {stats.current_streak}\n"
                f"资产总数: {stats.assets_this_week}\n"
                f"本月AI成本: ${cost:.2f}\n"
            )
            await update.message.reply_text(msg, parse_mode="MarkdownV2")

        except Exception as e:
            logger.exception("Error in /status: %s", e)
            await update.message.reply_text(
                "暂时无法处理，请稍后再试。"
            )

    # ------------------------------------------------------------------
    # /assets
    # ------------------------------------------------------------------

    async def _cmd_assets(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        db: Any = context.bot_data["db"]

        try:
            assets = await db.get_assets(limit=5)
            if not assets:
                await update.message.reply_text("暂无资产。")
                return

            lines = ["🗂 *最近资产*\n"]
            for a in assets:
                created = (a.get("created_at") or "—")[:10]
                title = a.get("title", "无标题")
                asset_type = a.get("type", "—")
                lines.append(f"• \[{created}\] {title} \\({asset_type}\\)")

            await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")

        except Exception as e:
            logger.exception("Error in /assets: %s", e)
            await update.message.reply_text(
                "暂时无法处理，请稍后再试。"
            )

    # ------------------------------------------------------------------
    # /insights
    # ------------------------------------------------------------------

    async def _cmd_insights(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        db: Any = context.bot_data["db"]

        try:
            insights = await db.get_insights(limit=5)
            if not insights:
                await update.message.reply_text("暂无洞察。")
                return

            lines = ["💡 *最近洞察*\n"]
            for ins in insights:
                conf = ins.get("confidence", 0)
                text = ins.get("text", "—")
                lines.append(f"• \[{conf}%\] {text}")

            await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")

        except Exception as e:
            logger.exception("Error in /insights: %s", e)
            await update.message.reply_text(
                "暂时无法处理，请稍后再试。"
            )

    # ------------------------------------------------------------------
    # Callback query handler (inline keyboard buttons)
    # ------------------------------------------------------------------

    async def _on_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat_id
        data = query.data or ""
        conv = _get_conv(context, chat_id)

        # --- Mood selection ---
        if data.startswith("mood:"):
            try:
                mood = int(data.split(":")[1])
            except (IndexError, ValueError):
                return

            if conv.get("step") != NIGHT_STEP_WAITING_MOOD:
                return

            conv["mood"] = mood
            conv["step"] = NIGHT_STEP_WAITING_ENERGY
            await query.edit_message_text(f"情绪: {MOOD_LABELS.get(mood, '?')} {mood}")
            await context.bot.send_message(
                chat_id, "精力呢？选一个：", reply_markup=_energy_keyboard()
            )
            return

        # --- Energy selection ---
        if data.startswith("energy:"):
            try:
                energy = int(data.split(":")[1])
            except (IndexError, ValueError):
                return

            if conv.get("step") != NIGHT_STEP_WAITING_ENERGY:
                return

            conv["energy"] = energy
            await query.edit_message_text(f"精力: {ENERGY_LABELS.get(energy, '?')} {energy}")

            # Collect all gathered data
            raw_notes = conv.get("raw_notes", "")
            mood_val = conv.get("mood", 3)
            energy_val = energy

            _clear_conv(context, chat_id)

            await context.bot.send_message(chat_id, "✅ 收到，AI分析中…")

            # Call A2 loop closer
            db: Any = context.bot_data["db"]
            agents: dict = context.bot_data["agents"]

            try:
                a2 = agents.get("A2_loop_closer")
                if a2 is None:
                    await context.bot.send_message(chat_id, "⚠️ A2 代理未配置。")
                    return

                # LoopCloserAgent.build_variables expects: raw_notes, core_task, date
                result = await a2.run(input_data={
                    "raw_notes": raw_notes,
                    "mood": mood_val,
                    "energy": energy_val,
                    "date": date.today().isoformat(),
                })

                summary = result.get("summary", "—")
                problem = result.get("ai_problem", "—")
                next_action = result.get("ai_next_action", "—")
                tags = result.get("tags", [])

                msg = (
                    f"📝 *今日闭环*\n\n"
                    f"核心收获: {summary}\n"
                    f"暴露问题: {problem}\n"
                    f"明日修正: {next_action}\n\n"
                    f"🏷️ 标签: {', '.join(tags) if tags else '—'}"
                )
                await context.bot.send_message(
                    chat_id, msg, parse_mode="MarkdownV2"
                )

                # Persist entry to DB using the real DailyLogCreate model
                log_entry = DailyLogCreate(
                    log_date=date.today(),
                    raw_notes=raw_notes,
                    mood=mood_val,
                    energy=energy_val,
                    ai_summary=summary,
                    ai_problem=problem,
                    ai_next_action=next_action,
                    tags=tags,
                )
                await db.create_daily_log(log_entry)

            except Exception as e:
                logger.exception("Error in /night finalisation: %s", e)
                await context.bot.send_message(
                    chat_id, "暂时无法处理，请稍后再试。"
                )

            return

    # ------------------------------------------------------------------
    # Text message handler (for /night conversation flow)
    # ------------------------------------------------------------------

    async def _on_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        chat_id = update.effective_chat.id
        conv = _get_conv(context, chat_id)
        step = conv.get("step")

        if step == NIGHT_STEP_WAITING_NOTES:
            conv["raw_notes"] = update.message.text
            conv["step"] = NIGHT_STEP_WAITING_MOOD
            await update.message.reply_text(
                "情绪怎么样？选一个：", reply_markup=_mood_keyboard()
            )
            return

        # If not in a conversation, ignore silently

    # ------------------------------------------------------------------
    # Error handler
    # ------------------------------------------------------------------

    async def _on_error(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        logger.error("Unhandled exception in handler:", exc_info=context.error)
        if isinstance(update, Update) and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ 发生了内部错误，请稍后再试。",
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Run (blocking, for standalone use)
    # ------------------------------------------------------------------

    def run_polling(self) -> None:
        """Convenience: set up and start polling (blocks the event loop)."""
        app = self.setup()
        logger.info("Growth OS Telegram bot starting polling…")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
