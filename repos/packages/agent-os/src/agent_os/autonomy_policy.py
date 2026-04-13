from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class AutonomyDecision:
    action_type: str
    action_class: str
    allowed: bool
    requires_approval: bool
    blocked: bool
    reason: str
    policy_name: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "action_class": self.action_class,
            "allowed": self.allowed,
            "requires_approval": self.requires_approval,
            "blocked": self.blocked,
            "reason": self.reason,
            "policy_name": self.policy_name,
        }


class AutonomyPolicyEngine:
    """Evaluate initiative proposals against bounded-agency policy rules."""

    def __init__(self, repo_root: Path, policy_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.policy_path = policy_path or (self.repo_root / "configs/tooling/autonomy_policy.yaml")
        self.policy = self._load_policy()

    def _load_policy(self) -> dict[str, Any]:
        if not self.policy_path.exists():
            return {
                "version": "1.0",
                "policy_name": "default",
                "default_action_class": "allowed_with_delayed_approval",
                "action_classes": {},
                "action_type_map": {},
            }
        return parse_simple_yaml(self.policy_path.read_text(encoding="utf-8"))

    def evaluate(self, action_type: str) -> AutonomyDecision:
        normalized_action = str(action_type or "unknown").strip()
        action_map = self.policy.get("action_type_map", {})
        action_class = str(action_map.get(normalized_action) or self.policy.get("default_action_class") or "allowed_with_delayed_approval")
        action_classes = self.policy.get("action_classes", {})
        action_spec = action_classes.get(action_class, {}) if isinstance(action_classes, dict) else {}

        blocked = bool(action_spec.get("blocked", False))
        requires_approval = bool(action_spec.get("requires_approval", False))
        allowed = not blocked
        if blocked:
            reason = f"Action '{normalized_action}' blocked by policy class '{action_class}'"
        elif requires_approval:
            reason = f"Action '{normalized_action}' requires approval under '{action_class}'"
        else:
            reason = f"Action '{normalized_action}' allowed under '{action_class}'"

        return AutonomyDecision(
            action_type=normalized_action,
            action_class=action_class,
            allowed=allowed,
            requires_approval=requires_approval,
            blocked=blocked,
            reason=reason,
            policy_name=str(self.policy.get("policy_name") or "default"),
        )

