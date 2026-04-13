from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FulfillmentDecision:
    should_fulfill: bool
    reason: str


def should_fulfill(status: str) -> FulfillmentDecision:
    if status == "confirmed":
        return FulfillmentDecision(should_fulfill=True, reason="payment_confirmed")
    return FulfillmentDecision(should_fulfill=False, reason="payment_not_confirmed")
