from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RecoveryState(str, Enum):
    SUBMITTED = "SUBMITTED"
    SPAWNING = "SPAWNING"
    PREFLIGHT = "PREFLIGHT"
    RUNNING = "RUNNING"
    BLOCKED = "BLOCKED"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    DEGRADED = "DEGRADED"
    ESCALATED = "ESCALATED"
    VERIFYING = "VERIFYING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


LEGAL_TRANSITIONS: dict[RecoveryState, set[RecoveryState]] = {
    RecoveryState.SUBMITTED: {RecoveryState.SPAWNING, RecoveryState.CANCELLED},
    RecoveryState.SPAWNING: {RecoveryState.PREFLIGHT, RecoveryState.BLOCKED, RecoveryState.RECOVERY_IN_PROGRESS, RecoveryState.FAILED, RecoveryState.CANCELLED},
    RecoveryState.PREFLIGHT: {RecoveryState.RUNNING, RecoveryState.BLOCKED, RecoveryState.RECOVERY_IN_PROGRESS, RecoveryState.FAILED, RecoveryState.CANCELLED},
    RecoveryState.RUNNING: {RecoveryState.VERIFYING, RecoveryState.RECOVERY_IN_PROGRESS, RecoveryState.BLOCKED, RecoveryState.DONE, RecoveryState.FAILED, RecoveryState.CANCELLED},
    RecoveryState.BLOCKED: {RecoveryState.RECOVERY_IN_PROGRESS, RecoveryState.ESCALATED, RecoveryState.CANCELLED},
    RecoveryState.RECOVERY_IN_PROGRESS: {RecoveryState.DEGRADED, RecoveryState.RUNNING, RecoveryState.ESCALATED, RecoveryState.FAILED, RecoveryState.CANCELLED},
    RecoveryState.DEGRADED: {RecoveryState.RUNNING, RecoveryState.VERIFYING, RecoveryState.DONE, RecoveryState.FAILED, RecoveryState.CANCELLED},
    RecoveryState.ESCALATED: {RecoveryState.RUNNING, RecoveryState.FAILED, RecoveryState.CANCELLED},
    RecoveryState.VERIFYING: {RecoveryState.DONE, RecoveryState.RECOVERY_IN_PROGRESS, RecoveryState.FAILED, RecoveryState.CANCELLED},
    RecoveryState.DONE: set(),
    RecoveryState.FAILED: set(),
    RecoveryState.CANCELLED: set(),
}


@dataclass
class RecoveryStateMachine:
    run_id: str
    current: RecoveryState = RecoveryState.SUBMITTED
    trace: list[dict[str, Any]] = field(default_factory=list)

    def transition(self, next_state: RecoveryState | str, *, reason: str, data: dict[str, Any] | None = None) -> None:
        target = next_state if isinstance(next_state, RecoveryState) else RecoveryState(str(next_state))
        allowed = LEGAL_TRANSITIONS[self.current]
        if target not in allowed:
            raise ValueError(f"Illegal recovery state transition: {self.current.value} -> {target.value}")
        previous = self.current
        self.current = target
        self.trace.append(
            {
                "run_id": self.run_id,
                "from": previous.value,
                "to": target.value,
                "reason": str(reason),
                "ts": datetime.now(tz=timezone.utc).isoformat(),
                "data": dict(data or {}),
            }
        )

    def event_payload(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "component": "recovery",
            "status": "ok" if self.current in {RecoveryState.DONE, RecoveryState.RUNNING, RecoveryState.VERIFYING} else "warn",
            "message": f"Recovery state: {self.current.value}",
            "data": {
                "current_state": self.current.value,
                "trace": list(self.trace),
            },
        }
