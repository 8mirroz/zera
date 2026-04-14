from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class EscalationTrigger:
    trigger_type: str
    description: str
    action: str
    target: str | None
    require_review: bool = False
    require_replan: bool = False
    require_approval: bool = False


@dataclass
class EscalationDecision:
    triggered: bool
    trigger_type: str | None
    level: int
    action: str
    target: str | None
    reason: str
    can_avoid: bool = False
    avoidance_strategy: str | None = None


class EscalationEngine:
    def __init__(self, repo_root: Path, config_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.config_path = config_path or (
            self.repo_root / "configs/tooling/escalation_policy.yaml"
        )
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return self._default_config()
        return parse_simple_yaml(self.config_path.read_text(encoding="utf-8"))

    def _default_config(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "escalation_triggers": {
                "confidence_triggers": {
                    "below_tier_minimum": {
                        "action": "escalate_to_role",
                        "target": "planner",
                    }
                }
            },
            "escalation_levels": {
                "level_0_self_recovery": {"allowed_attempts": 2},
                "level_1_role_escalation": {"targets": []},
                "level_2_orchestrator_escalation": {},
                "level_3_architect_escalation": {},
                "level_4_council_escalation": {},
                "level_5_human_escalation": {},
            },
        }

    def check_confidence_escalation(
        self,
        confidence_score: float,
        tier_min: float,
        repeated_low_confidence: int = 0,
    ) -> EscalationDecision:
        triggers = self.config.get("escalation_triggers", {}).get(
            "confidence_triggers", {}
        )

        if confidence_score < tier_min:
            trigger = triggers.get("below_tier_minimum", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="confidence_below_minimum",
                level=1,
                action=trigger.get("action", "escalate_to_role"),
                target=trigger.get("target", "planner"),
                reason=f"Confidence {confidence_score:.2f} below tier minimum {tier_min}",
                can_avoid=True,
                avoidance_strategy="retry_with_different_strategy",
            )

        if repeated_low_confidence >= 3:
            trigger = triggers.get("repeated_low_confidence", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="repeated_low_confidence",
                level=2,
                action=trigger.get("action", "escalate_to_orchestrator"),
                target="orchestrator",
                reason=f"{repeated_low_confidence} consecutive low confidence tasks",
            )

        return EscalationDecision(
            triggered=False,
            trigger_type=None,
            level=0,
            action="continue",
            target=None,
            reason="No confidence escalation triggers",
        )

    def check_risk_escalation(
        self,
        risk_score: float,
    ) -> EscalationDecision:
        triggers = self.config.get("escalation_triggers", {}).get("risk_triggers", {})

        if risk_score >= 12:
            trigger = triggers.get("critical_risk", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="critical_risk",
                level=4,
                action=trigger.get("action", "halt_and_escalate"),
                target=trigger.get("target", "architect"),
                reason=f"Critical risk score: {risk_score}",
            )

        if risk_score >= 8:
            trigger = triggers.get("high_risk_above_threshold", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="high_risk",
                level=2,
                action=trigger.get("action", "require_approval"),
                target=trigger.get("approval_from", "human"),
                reason=f"High risk score: {risk_score}",
            )

        return EscalationDecision(
            triggered=False,
            trigger_type=None,
            level=0,
            action="continue",
            target=None,
            reason="No risk escalation triggers",
        )

    def check_failure_escalation(
        self,
        failure_count: int,
        failure_type: str | None = None,
    ) -> EscalationDecision:
        triggers = self.config.get("escalation_triggers", {}).get(
            "failure_triggers", {}
        )

        if failure_type == "same_failure" and failure_count >= 3:
            trigger = triggers.get("same_failure_three_times", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="same_failure_three_times",
                level=3,
                action=trigger.get("action", "escalate_to_architect"),
                target="architect",
                reason=f"Same failure occurred 3 times",
            )

        if failure_count >= 2:
            trigger = triggers.get("repeated_failure", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="repeated_failure",
                level=1,
                action=trigger.get("action", "escalate_to_reviewer"),
                target="reviewer",
                reason=f"Task failed {failure_count} times",
            )

        return EscalationDecision(
            triggered=False,
            trigger_type=None,
            level=0,
            action="continue",
            target=None,
            reason="No failure escalation triggers",
        )

    def check_budget_escalation(
        self,
        budget_remaining_pct: float,
        pending_tasks: int,
        hard_limit_exceeded: bool = False,
    ) -> EscalationDecision:
        triggers = self.config.get("escalation_triggers", {}).get("budget_triggers", {})

        if hard_limit_exceeded:
            trigger = triggers.get("hard_limit_exceeded", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="budget_hard_limit",
                level=5,
                action=trigger.get("action", "halt_execution"),
                target="human",
                reason="Budget hard limit exceeded",
            )

        if pending_tasks > 0 and budget_remaining_pct < 10:
            trigger = triggers.get("budget_depleted_with_pending_tasks", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="budget_depleted",
                level=2,
                action=trigger.get("action", "escalate_to_orchestrator"),
                target="orchestrator",
                reason=f"Budget low ({budget_remaining_pct:.1f}%) with {pending_tasks} pending tasks",
            )

        return EscalationDecision(
            triggered=False,
            trigger_type=None,
            level=0,
            action="continue",
            target=None,
            reason="No budget escalation triggers",
        )

    def check_complexity_escalation(
        self,
        task_expanded: bool = False,
        architecture_decision_needed: bool = False,
        design_implications: bool = False,
    ) -> EscalationDecision:
        triggers = self.config.get("escalation_triggers", {}).get(
            "complexity_triggers", {}
        )

        if architecture_decision_needed:
            trigger = triggers.get("architecture_decision_needed", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="architecture_decision",
                level=3,
                action=trigger.get("action", "escalate_to_architect"),
                target="architect",
                reason="Architecture decision required",
            )

        if design_implications:
            trigger = triggers.get("design_implications", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="design_implications",
                level=2,
                action=trigger.get("action", "escalate_to_design_lead"),
                target="design_lead",
                reason="Design implications detected",
            )

        if task_expanded:
            trigger = triggers.get("task_expansion", {})
            return EscalationDecision(
                triggered=True,
                trigger_type="task_expansion",
                level=2,
                action=trigger.get("action", "return_to_orchestrator"),
                target="orchestrator",
                reason="Task scope expanded beyond original",
            )

        return EscalationDecision(
            triggered=False,
            trigger_type=None,
            level=0,
            action="continue",
            target=None,
            reason="No complexity escalation triggers",
        )

    def get_escalation_level_name(self, level: int) -> str:
        levels = self.config.get("escalation_levels", {})
        level_keys = [k for k in levels.keys() if f"level_{level}" in k]
        if level_keys:
            return level_keys[0]
        return f"level_{level}"

    def get_prevention_checks(self) -> list[str]:
        prevention = self.config.get("escalation_prevention", {})
        return prevention.get("pre_escalation_checks", [])
