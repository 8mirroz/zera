from __future__ import annotations

from typing import Any

REQUIRED_TELEGRAM_EVENT_FIELDS = [
    "event",
    "correlation_id",
    "chat_id",
    "user_id",
    "handler",
    "runtime_provider",
    "runtime_profile",
]

REQUIRED_PAYMENT_EVENT_FIELDS = [
    "event_id",
    "order_id",
    "provider",
    "provider_payment_id",
    "status",
    "amount_minor",
    "currency",
    "correlation_id",
]


def make_correlation_context(*, correlation_id: str, project: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "correlation_id": correlation_id,
        "project": project,
    }
    if extra:
        payload.update(extra)
    return payload
