from __future__ import annotations


class PaymentTransitionError(ValueError):
    pass


class PaymentStateMachine:
    _transitions = {
        "created": {"pending"},
        "pending": {"confirmed", "failed"},
        "confirmed": {"fulfilled"},
        "failed": {"recoverable"},
        "recoverable": {"pending"},
        "fulfilled": set(),
    }

    def can_transition(self, current: str, new: str) -> bool:
        return new in self._transitions.get(current, set())

    def apply(self, current: str, new: str) -> str:
        if not self.can_transition(current, new):
            raise PaymentTransitionError(f"invalid transition: {current} -> {new}")
        return new
