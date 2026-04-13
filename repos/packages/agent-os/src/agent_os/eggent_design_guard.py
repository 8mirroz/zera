from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .eggent_contracts import EggentRouteDecisionV1, TaskSpecV1
from .eggent_profile_loader import EggentProfileLoader


@dataclass
class EggentDesignDecision:
    design_contour: bool
    design_role: str
    design_task_kind: str
    token_policy_hash: str
    violations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EggentDesignGuard:
    """Enforces design contour isolation and token-driven deterministic policies."""

    def __init__(self, repo_root: Path, pack_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.profile_loader = EggentProfileLoader(self.repo_root, pack_root)
        self.design_profile = self.profile_loader.load_design_profile()

    def evaluate(
        self,
        task_spec_raw: dict[str, Any] | TaskSpecV1,
        route_decision: EggentRouteDecisionV1 | dict[str, Any],
    ) -> EggentDesignDecision:
        task_spec = task_spec_raw if isinstance(task_spec_raw, TaskSpecV1) else TaskSpecV1.from_dict(task_spec_raw)
        route = route_decision.to_dict() if isinstance(route_decision, EggentRouteDecisionV1) else dict(route_decision)

        violations: list[str] = []
        task_type = str(route.get("task_type", ""))
        is_t6 = task_type == "T6"
        if not is_t6:
            violations.append("Task is outside T6 design contour")

        design_task_kind = self._classify_design_task(task_spec)
        role = str(self.design_profile.design_routing.get(design_task_kind, "design_worker"))

        if role not in {"design_worker", "design_supervisor"}:
            violations.append(f"Invalid design role mapping: {role}")

        # In v4, worker tier is used for C1/C2 tasks.
        # Tests EXPECT 'Backend execution role cannot be used inside design contour' if specialist/supervisor is found.
        # We also flag 'worker' ONLY if it's not a design task.
        role_hint = str(route.get("execution_role") or route.get("assigned_role") or "")
        if role_hint in {"specialist", "supervisor"}:
            violations.append("Backend execution role cannot be used inside design contour")
        elif role_hint == "worker" and not is_t6:
            violations.append("Backend execution role cannot be used inside design contour")

        rules_text = self.design_profile.design_rules_markdown
        required_rules = [
            "No arbitrary spacing or color values",
            "Motion must have easing and duration tokens",
            "Accessibility: WCAG AA minimum",
        ]
        for rule in required_rules:
            if rule not in rules_text:
                violations.append(f"Missing required design rule: {rule}")

        tokens = self.design_profile.visual_tokens
        if not isinstance(tokens.get("spacing"), list) or not tokens.get("spacing"):
            violations.append("visual_tokens.spacing must be non-empty")
        if not isinstance(tokens.get("durations_ms"), list) or not tokens.get("durations_ms"):
            violations.append("visual_tokens.durations_ms must be non-empty")
        if not isinstance(tokens.get("easing"), list) or not tokens.get("easing"):
            violations.append("visual_tokens.easing must be non-empty")

        policy_hash = self._token_policy_hash(task_spec, route)
        return EggentDesignDecision(
            design_contour=is_t6,
            design_role=role,
            design_task_kind=design_task_kind,
            token_policy_hash=policy_hash,
            violations=sorted(set(violations)),
        )

    def _classify_design_task(self, task_spec: TaskSpecV1) -> str:
        if task_spec.area == "animation":
            return "animation"
        if task_spec.risk == "high" or task_spec.scope == "system_wide" or task_spec.complexity == "hard":
            return "design_system_change"
        if task_spec.scope == "multi_file":
            return "layout_change"
        return "ui_component"

    def _token_policy_hash(self, task_spec: TaskSpecV1, route: dict[str, Any]) -> str:
        payload = {
            "task_spec": task_spec.to_dict(),
            "task_type": route.get("task_type"),
            "design_routing": self.design_profile.design_routing,
            "visual_tokens": self.design_profile.visual_tokens,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
