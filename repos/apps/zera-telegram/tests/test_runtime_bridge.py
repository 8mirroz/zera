from __future__ import annotations

import sys
from pathlib import Path


BOT_DIR = Path(__file__).resolve().parents[1] / "bot"
sys.path.insert(0, str(BOT_DIR))

from runtime_bridge import _select_user_response, sanitize_runtime_text


def test_sanitize_runtime_text_removes_internal_tool_markup() -> None:
    raw = (
        "tool_call>\n"
        "<tools>\n"
        "<tool name=\"spawn_agent\">\n"
        "{\"query\":\"market\"}\n"
        "</tool>\n"
        "</tools>\n"
    )
    assert sanitize_runtime_text(raw) == ""


def test_sanitize_runtime_text_keeps_real_text_after_tool_markup() -> None:
    raw = (
        "tool_call>\n"
        "<tools>\n"
        "<tool name=\"spawn_agent\">{\"q\":\"Москва\"}</tool>\n"
        "</tools>\n"
        "Готово. Начинаю исследование рынка и соберу краткий отчёт."
    )
    assert sanitize_runtime_text(raw) == "Готово. Начинаю исследование рынка и соберу краткий отчёт."


def test_select_user_response_falls_back_to_next_candidate() -> None:
    leaked = "tool_call>\n<tools><tool name=\"x\"></tool></tools>"
    selected = _select_user_response(leaked, "Нормальный ответ для пользователя.")
    assert selected == "Нормальный ответ для пользователя."
