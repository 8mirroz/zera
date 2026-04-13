from __future__ import annotations

from .config import TelegramBotCoreSettings


def webhook_path(settings: TelegramBotCoreSettings) -> str:
    path = settings.webhook_path_value.strip() or "/telegram/webhook"
    return path if path.startswith("/") else f"/{path}"
