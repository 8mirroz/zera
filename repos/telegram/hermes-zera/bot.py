#!/usr/bin/env python3
"""Hermes Zera — Telegram bot with Agent OS integration.

Usage:
    python bot.py          # Production (polling)
    python bot.py --debug  # Show routing info in responses
"""
from __future__ import annotations

import os
import sys
import argparse
import logging
from pathlib import Path

# Ensure we can import from src/
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from telegram_agent import HermesZeraAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hermes-zera-bot")

# Global agent instance
_agent: HermesZeraAgent | None = None
_debug_mode = False


def get_agent() -> HermesZeraAgent:
    global _agent
    if _agent is None:
        _agent = HermesZeraAgent()
    return _agent


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    agent_name = os.getenv("AGENT_NAME", "Hermes Zera")
    await update.message.reply_text(
        f"🌌 Привет! Я {agent_name}. Чем могу помочь?\n"
        f"Используй /stats для статистики, /debug для режима отладки."
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command — show session stats."""
    if not update.message:
        return
    chat_id = update.message.chat_id
    agent = get_agent()
    stats = agent.get_session_stats(chat_id)

    lines = [
        "📊 **Статистика сессии:**",
        f"Сообщений: {stats['total_messages']}",
        f"Последний tier: {stats['last_tier']}",
        f"Средняя задержка: {stats['avg_latency_ms']:.0f}ms",
    ]
    if stats["model_usage"]:
        lines.append("\n🔧 Модели:")
        for model, count in stats["model_usage"].items():
            lines.append(f"  • {model}: {count}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle debug mode."""
    global _debug_mode
    _debug_mode = not _debug_mode
    status = "вкл" if _debug_mode else "выкл"
    if update.message:
        await update.message.reply_text(f"🔍 Debug режим: {status}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    if not update.message or not update.message.text:
        return

    chat_id = update.message.chat_id
    text = update.message.text.strip()

    # Skip commands (handled separately)
    if text.startswith("/"):
        return

    agent = get_agent()

    # Typing indicator
    await update.message.chat.send_action("typing")

    # Process through Agent OS
    response, routing_info = agent.process_message(chat_id, text)

    # Append debug info if enabled
    if _debug_mode:
        debug_lines = [
            f"\n\n--- 🔍 Routing ---",
            f"Tier: `{routing_info['tier']}`",
            f"Model: `{routing_info['model']}`",
            f"Latency: `{routing_info['latency_ms']:.0f}ms`",
            f"Fallback: `{'yes' if routing_info['fallback_used'] else 'no'}`",
        ]
        response += "\n".join(debug_lines)

    await update.message.reply_text(response, parse_mode="Markdown")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes Zera Telegram Bot")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    global _debug_mode
    _debug_mode = args.debug

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    agent_name = os.getenv("AGENT_NAME", "Hermes Zera")
    logger.info(f"🌌 {agent_name} запущен в Telegram...")

    # Initialize Agent OS
    agent = get_agent()

    # Build bot
    app = Application.builder().token(token).build()

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("debug", cmd_debug))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
