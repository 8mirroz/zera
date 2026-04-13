from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReconciliationTask:
    provider: str
    order_id: str
    payment_id: str
    reason: str
