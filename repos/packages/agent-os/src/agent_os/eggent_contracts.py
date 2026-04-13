from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class TaskSpecValidationError(ValueError):
    """Raised when TaskSpecV1 payload is malformed."""


@dataclass(frozen=True)
class TaskSpecV1:
    task_id: str
    area: str
    risk: str
    scope: str
    complexity: str
    requires_reasoning: bool
    requires_accuracy: bool

    _AREA_ALLOWED = {"ui", "backend", "infra", "animation", "tests"}
    _RISK_ALLOWED = {"low", "medium", "high"}
    _SCOPE_ALLOWED = {"single_file", "multi_file", "system_wide"}
    _COMPLEXITY_ALLOWED = {"trivial", "normal", "hard"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskSpecV1":
        if not isinstance(data, dict):
            raise TaskSpecValidationError("TaskSpec must be an object")

        required = [
            "task_id",
            "area",
            "risk",
            "scope",
            "complexity",
            "requires_reasoning",
            "requires_accuracy",
        ]
        missing = [k for k in required if k not in data]
        if missing:
            raise TaskSpecValidationError(f"TaskSpec missing required fields: {', '.join(sorted(missing))}")

        task_id = str(data["task_id"]).strip()
        area = str(data["area"]).strip()
        risk = str(data["risk"]).strip()
        scope = str(data["scope"]).strip()
        complexity = str(data["complexity"]).strip()

        if not task_id:
            raise TaskSpecValidationError("task_id must be a non-empty string")
        if area not in cls._AREA_ALLOWED:
            raise TaskSpecValidationError(f"area must be one of: {', '.join(sorted(cls._AREA_ALLOWED))}")
        if risk not in cls._RISK_ALLOWED:
            raise TaskSpecValidationError(f"risk must be one of: {', '.join(sorted(cls._RISK_ALLOWED))}")
        if scope not in cls._SCOPE_ALLOWED:
            raise TaskSpecValidationError(f"scope must be one of: {', '.join(sorted(cls._SCOPE_ALLOWED))}")
        if complexity not in cls._COMPLEXITY_ALLOWED:
            raise TaskSpecValidationError(
                f"complexity must be one of: {', '.join(sorted(cls._COMPLEXITY_ALLOWED))}"
            )

        requires_reasoning = data["requires_reasoning"]
        requires_accuracy = data["requires_accuracy"]
        if not isinstance(requires_reasoning, bool):
            raise TaskSpecValidationError("requires_reasoning must be boolean")
        if not isinstance(requires_accuracy, bool):
            raise TaskSpecValidationError("requires_accuracy must be boolean")

        return cls(
            task_id=task_id,
            area=area,
            risk=risk,
            scope=scope,
            complexity=complexity,
            requires_reasoning=requires_reasoning,
            requires_accuracy=requires_accuracy,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EggentRouteDecisionV1:
    task_id: str
    task_type: str
    complexity_tier: str
    execution_role: str
    primary_model: str
    fallback_chain: list[str] = field(default_factory=list)
    escalation_policy: dict[str, Any] = field(default_factory=dict)
    design_contour: bool = False
    route_reason: str = ""
    routing_source: str = "v4"
    telemetry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
