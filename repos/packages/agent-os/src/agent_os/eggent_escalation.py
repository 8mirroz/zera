from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .eggent_contracts import TaskSpecV1
from .eggent_profile_loader import EggentProfileLoader


@dataclass
class EggentEscalationDecision:
    next_role: str
    reason: str
    attempt_counters: dict[str, int]
    allowed_actions: list[str]
    matched_signals: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EggentEscalationEngine:
    """State-machine escalation worker->specialist->supervisor."""

    def __init__(self, repo_root: Path, pack_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.profile_loader = EggentProfileLoader(self.repo_root, pack_root)
        self.profile = self.profile_loader.load()

        tracking = self.profile.escalation_rules.get("failure_tracking", {})
        self.max_worker_attempts = int(tracking.get("max_worker_attempts", 3))
        self.max_specialist_attempts = int(tracking.get("max_specialist_attempts", 2))

        self.signal_map = self.profile.escalation_rules.get("signals", {})
        sup = self.profile.escalation_rules.get("supervisor_usage", {})
        actions = sup.get("allowed_actions", [])
        self.supervisor_actions = [str(a) for a in actions] if isinstance(actions, list) else []

    def decide(
        self,
        task_spec_raw: dict[str, Any] | TaskSpecV1,
        *,
        signals: list[str],
        attempts_worker: int,
        attempts_specialist: int,
        current_role: str | None = None,
    ) -> EggentEscalationDecision:
        task_spec = task_spec_raw if isinstance(task_spec_raw, TaskSpecV1) else TaskSpecV1.from_dict(task_spec_raw)

        normalized_signals = [s.strip() for s in signals if str(s).strip()]
        matched_signals: list[str] = []

        next_role = current_role or "worker"
        reason = "no escalation triggers"

        if attempts_specialist >= self.max_specialist_attempts:
            next_role = "supervisor"
            reason = "specialist attempt limit exceeded"
        elif attempts_worker >= self.max_worker_attempts:
            next_role = "specialist"
            reason = "worker attempt limit exceeded"

        signal_targets = self._signal_targets(normalized_signals, matched_signals)
        if "supervisor" in signal_targets:
            next_role = "supervisor"
            reason = "supervisor-level signal matched"
        elif "specialist" in signal_targets and next_role != "supervisor":
            next_role = "specialist"
            reason = "specialist-level signal matched"

        if task_spec.scope == "system_wide" and task_spec.risk == "high":
            next_role = "supervisor"
            reason = "system-wide high-risk task"

        if any(s not in self.signal_map for s in normalized_signals):
            next_role = "supervisor"
            reason = "unknown signal fail-safe escalation"

        allowed_actions = self.supervisor_actions if next_role == "supervisor" else []
        return EggentEscalationDecision(
            next_role=next_role,
            reason=reason,
            attempt_counters={
                "worker": int(attempts_worker),
                "specialist": int(attempts_specialist),
                "max_worker_attempts": self.max_worker_attempts,
                "max_specialist_attempts": self.max_specialist_attempts,
            },
            allowed_actions=allowed_actions,
            matched_signals=matched_signals,
        )

    def _signal_targets(self, signals: list[str], matched_signals: list[str]) -> set[str]:
        targets: set[str] = set()
        for signal in signals:
            mapped = self.signal_map.get(signal)
            if not isinstance(mapped, str):
                continue
            matched_signals.append(signal)
            norm = mapped.strip().lower()
            if "supervisor" in norm:
                targets.add("supervisor")
            elif "specialist" in norm:
                targets.add("specialist")
        return targets
