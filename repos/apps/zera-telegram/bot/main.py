from __future__ import annotations
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from runtime_bridge import (
    approval_list_text,
    approval_resolve_text,
    budget_status_text,
    background_drain_text,
    background_status_text,
    health_text,
    goal_stack_text,
    incident_report_text,
    is_admin_chat,
    is_chat_allowed,
    is_rate_limited,
    mode_text,
    pause_background_text,
    response_chunks,
    resume_background_text,
    run_companion_flow,
    stop_clear_text,
    stop_signal_text,
)

router = Router()


def _resolve_bot_token() -> str | None:
    for key in ("BOT_TOKEN", "ZERA_BOT_TOKEN", "TELEGRAM_BOT_TOKEN", "TG_BOT_TOKEN", "ZERA_TOKEN"):
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    return None


async def _answer_chunks(message: Message, text: str) -> None:
    for chunk in response_chunks(text):
        await message.answer(chunk)


def _webhook_path() -> str:
    return str(os.getenv("TG_WEBHOOK_PATH") or "/telegram/webhook")


def _webhook_url() -> str | None:
    raw = str(os.getenv("TG_WEBHOOK_URL") or "").strip()
    return raw or None


def _webhook_secret() -> str | None:
    raw = str(os.getenv("TG_WEBHOOK_SECRET") or "").strip()
    return raw or None


def _webhook_host() -> str:
    return str(os.getenv("TG_WEBHOOK_HOST") or "0.0.0.0")


def _webhook_port() -> int:
    try:
        return int(os.getenv("TG_WEBHOOK_PORT") or "8080")
    except Exception:
        return 8080


async def _require_allowed(message: Message) -> bool:
    if not is_chat_allowed(message.chat.id):
        await message.answer("Access denied.")
        return False
    return True


async def _require_admin(message: Message) -> bool:
    if not await _require_allowed(message):
        return False
    if not is_admin_chat(message.chat.id):
        await message.answer("Admin access required.")
        return False
    return True


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    if not await _require_allowed(message):
        return
    await message.answer("ZeroClaw + Zera Telegram runtime is ready.")


@router.message(Command("health"))
async def health_handler(message: Message) -> None:
    if not await _require_allowed(message):
        return
    await _answer_chunks(message, health_text())


@router.message(Command("mode"))
async def mode_handler(message: Message) -> None:
    if not await _require_allowed(message):
        return
    await _answer_chunks(message, mode_text())


@router.message(Command("queue"))
async def queue_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, background_status_text())


@router.message(Command("jobs"))
async def jobs_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, background_status_text())


@router.message(Command("drain"))
async def drain_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, background_drain_text())


@router.message(Command("pause_background"))
async def pause_background_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    parts = (message.text or "").split()
    minutes = 60
    if len(parts) > 1:
        try:
            minutes = max(1, int(parts[1]))
        except Exception:
            minutes = 60
    await _answer_chunks(message, pause_background_text(minutes))


@router.message(Command("resume_background"))
async def resume_background_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, resume_background_text())


@router.message(Command("goals"))
async def goals_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, goal_stack_text())


@router.message(Command("budget"))
async def budget_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, budget_status_text())


@router.message(Command("approvals"))
async def approvals_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, approval_list_text())


@router.message(Command("approve"))
async def approve_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Usage: /approve <ticket_id>")
        return
    await _answer_chunks(message, approval_resolve_text(parts[1], "approve"))


@router.message(Command("deny"))
async def deny_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("Usage: /deny <ticket_id>")
        return
    await _answer_chunks(message, approval_resolve_text(parts[1], "deny"))


@router.message(Command("incident"))
async def incident_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, incident_report_text())


@router.message(Command("stop"))
async def stop_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    parts = (message.text or "").split()
    minutes = 30
    if len(parts) > 1:
        try:
            minutes = max(1, int(parts[1]))
        except Exception:
            minutes = 30
    await _answer_chunks(message, stop_signal_text(minutes=minutes))


@router.message(Command("resume"))
async def resume_handler(message: Message) -> None:
    if not await _require_admin(message):
        return
    await _answer_chunks(message, stop_clear_text())


@router.message(F.text)
async def chat_handler(message: Message) -> None:
    if not await _require_allowed(message):
        return
    if is_rate_limited(message.chat.id):
        await message.answer("Rate limit: wait a few seconds and retry.")
        return
    response = await asyncio.to_thread(run_companion_flow, message.text or "")
    await _answer_chunks(message, response)


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    await dp.start_polling(bot)


async def _run_webhook(bot: Bot, dp: Dispatcher) -> None:
    webhook_url = _webhook_url()
    if not webhook_url:
        raise RuntimeError("TG_WEBHOOK_URL is required when TG_BOT_MODE=webhook")
    app = web.Application()
    secret = _webhook_secret()
    handler = SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=secret)
    handler.register(app, path=_webhook_path())

    async def _healthz(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "mode": "webhook", "path": _webhook_path()})

    app.router.add_get("/healthz", _healthz)
    setup_application(app, dp, bot=bot)
    await bot.set_webhook(webhook_url, drop_pending_updates=True, secret_token=secret)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=_webhook_host(), port=_webhook_port())
    await site.start()
    await asyncio.Event().wait()


async def main() -> None:
    token = _resolve_bot_token()
    if not token:
        raise RuntimeError("No bot token found. Set one of: BOT_TOKEN, ZERA_BOT_TOKEN, TELEGRAM_BOT_TOKEN, TG_BOT_TOKEN, ZERA_TOKEN")

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    mode = str(os.getenv("TG_BOT_MODE") or "polling").strip().lower()
    if mode == "webhook":
        await _run_webhook(bot, dp)
        return
    await _run_polling(bot, dp)


if __name__ == "__main__":
    asyncio.run(main())
