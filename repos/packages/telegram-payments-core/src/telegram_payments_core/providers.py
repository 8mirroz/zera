from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PaymentAdapter:
    provider_id: str
    supports_refunds: bool
    requires_reconciliation: bool


def normalize_payment_event(
    *,
    provider: str,
    order_id: str,
    provider_event_id: str,
    status_from: str,
    status_to: str,
    amount_minor: int,
    currency: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": f"{provider}:{provider_event_id}:{status_to}",
        "order_id": order_id,
        "provider": provider,
        "provider_event_id": provider_event_id,
        "status_from": status_from,
        "status_to": status_to,
        "amount_minor": amount_minor,
        "currency": currency,
        "idempotency_key": f"{order_id}:{provider_event_id}:{status_to}",
        "raw_payload": payload,
    }
