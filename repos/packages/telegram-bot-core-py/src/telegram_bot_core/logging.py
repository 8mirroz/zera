from __future__ import annotations

from typing import Any


def make_log_event(
    *,
    event: str,
    correlation_id: str,
    chat_id: int,
    user_id: int,
    handler: str,
    dedupe_key: str,
    latency_ms: int | None = None,
    retry_attempt: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "correlation_id": correlation_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "handler": handler,
        "dedupe_key": dedupe_key,
        "retry_attempt": retry_attempt,
    }
    if latency_ms is not None:
        payload["latency_ms"] = latency_ms
    if extra:
        payload.update(extra)
    return payload
