"""
Role Policy Guard — Antigravity Core v4.2

Enforces role contract boundaries at runtime:
- Action boundary checks (forbidden_from)
- Handoff trigger evaluation
- Constraint enforcement (token budget, tool calls, file modifications)
- Quality gate collection
- Escalation determination

Works in conjunction with RoleContractLoader.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .exceptions import AgentOSError
from .role_contract_loader import RoleContractLoader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RolePolicyError(AgentOSError):
    """Base error for role policy enforcement."""


class ForbiddenActionError(RolePolicyError):
    def __init__(self, role_name: str, action_description: str):
        super().__init__(
            f"Role '{role_name}' attempted forbidden action: {action_description}"
        )
        self.role_name = role_name
        self.action_description = action_description


class ConstraintViolationError(RolePolicyError):
    def __init__(self, role_name: str, constraint: str, limit: int, actual: int):
        super().__init__(
            f"Role '{role_name}' violated constraint: {constraint} "
            f"(limit={limit}, actual={actual})"
        )
        self.role_name = role_name
        self.constraint = constraint
        self.limit = limit
        self.actual = actual


class HandoffRequiredError(RolePolicyError):
    def __init__(self, role_name: str, target_role: str, condition: str):
        super().__init__(
            f"Role '{role_name}' must hand off to '{target_role}': {condition}"
        )
        self.role_name = role_name
        self.target_role = target_role
        self.condition = condition


# ---------------------------------------------------------------------------
# Policy check result
# ---------------------------------------------------------------------------

@dataclass
class PolicyCheckResult:
    """Result of a policy evaluation."""
    allowed: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    handoff_required: bool = False
    handoff_target: Optional[str] = None
    handoff_condition: Optional[str] = None
    quality_gates: List[str] = field(default_factory=list)
    constraints_remaining: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Policy guard
# ---------------------------------------------------------------------------

class RolePolicyGuard:
    """Enforces role contract policies at runtime boundaries."""

    def __init__(self, loader: RoleContractLoader):
        self.loader = loader

    # ------------------------------------------------------------------
    # Action boundary enforcement
    # ------------------------------------------------------------------

    def check_action_allowed(
        self, role_name: str, action_description: str
    ) -> PolicyCheckResult:
        """Check if an action is allowed for a given role.

        Evaluates forbidden_from rules in the role contract.
        """
        result = PolicyCheckResult(allowed=True)
        contract = self._get_contract(role_name, result)
        if not contract:
            return result

        forbidden = contract.get("forbidden_from", [])
        if not isinstance(forbidden, list):
            return result

        for rule in forbidden:
            if self._rule_matches(rule, action_description):
                result.allowed = False
                result.violations.append(
                    f"Action violates rule: {rule}"
                )
                break

        return result

    def _rule_matches(self, rule: str, action: str) -> bool:
        """Check if a forbidden rule matches the action description.

        Uses keyword matching — if any keyword from the rule appears
        in the action description, the rule is considered triggered.
        """
        rule_lower = rule.lower()
        action_lower = action.lower()

        # Simple keyword matching
        rule_words = set(rule_lower.split())
        action_words = set(action_lower.split())

        # If majority of rule keywords are in action, consider it a match
        if rule_words and len(rule_words & action_words) >= max(1, len(rule_words) // 2):
            return True

        # Also check substring matching for short rules
        if len(rule_lower) > 5 and rule_lower in action_lower:
            return True

        return False

    # ------------------------------------------------------------------
    # Handoff trigger evaluation
    # ------------------------------------------------------------------

    def check_handoff_required(
        self, role_name: str, task_context: Dict[str, Any]
    ) -> PolicyCheckResult:
        """Evaluate handoff triggers for a role given task context.

        Returns handoff target if a trigger condition matches.
        """
        result = PolicyCheckResult(allowed=True)
        contract = self._get_contract(role_name, result)
        if not contract:
            return result

        triggers = contract.get("handoff_triggers", [])
        if not isinstance(triggers, list):
            return result

        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue
            condition = trigger.get("condition", "")
            target = trigger.get("target")

            if not condition or not target:
                continue

            if self._condition_matches(condition, task_context):
                result.handoff_required = True
                result.handoff_target = target
                result.handoff_condition = condition
                result.warnings.append(
                    f"Handoff to '{target}' triggered: {condition}"
                )
                break

        return result

    def _condition_matches(
        self, condition: str, context: Dict[str, Any]
    ) -> bool:
        """Evaluate a handoff condition against task context.

        Supports simple pattern matching:
        - "Task complexity in ['C1','C2']" → checks context.get("complexity")
        - "Task exceeds C2 complexity" → checks if complexity > C2
        - "Implementation required" → checks context.get("requires_implementation")
        - Contains keywords from context
        """
        condition_lower = condition.lower()

        # Check complexity tier matching
        if "complexity" in condition_lower:
            context_complexity = str(context.get("complexity", "")).upper()
            complexity_levels = ["C1", "C2", "C3", "C4", "C5"]

            # "exceeds C2" → complexity > C2
            if "exceeds" in condition_lower or "exceed" in condition_lower:
                for tier in complexity_levels:
                    if tier.lower() in condition_lower:
                        ctx_idx = complexity_levels.index(context_complexity) if context_complexity in complexity_levels else -1
                        tier_idx = complexity_levels.index(tier)
                        if ctx_idx > tier_idx:
                            return True

            # "in ['C1','C2']" → complexity in list
            if " in " in condition_lower or "in[" in condition_lower:
                for tier in complexity_levels:
                    if tier.lower() in condition_lower and tier == context_complexity:
                        return True

            # Direct tier match (case-insensitive)
            for tier in complexity_levels:
                if tier.lower() in condition_lower and tier == context_complexity:
                    return True

        # Check keyword matching from context
        context_keywords = {
            "implementation": context.get("requires_implementation", False),
            "validation": context.get("requires_validation", False),
            "design": context.get("requires_design", False),
            "architecture": context.get("requires_architecture", False),
            "review": context.get("requires_review", False),
            "ux": context.get("requires_ux", False),
            "visual": context.get("requires_visual", False),
        }

        for keyword, value in context_keywords.items():
            if keyword in condition_lower and value:
                return True

        # Check if any context flag is explicitly set
        for key, value in context.items():
            if isinstance(value, bool) and value and key.lower() in condition_lower:
                return True

        return False

    # ------------------------------------------------------------------
    # Constraint enforcement
    # ------------------------------------------------------------------

    def check_constraints(
        self,
        role_name: str,
        run_state: Dict[str, Any],
    ) -> PolicyCheckResult:
        """Check if role constraints are satisfied.

        Evaluates:
        - token_budget
        - max_tool_calls
        - max_files_modified
        """
        result = PolicyCheckResult(allowed=True)
        contract = self._get_contract(role_name, result)
        if not contract:
            return result

        constraints = contract.get("constraints", {})
        if not isinstance(constraints, dict):
            return result

        # Token budget check
        token_budget = constraints.get("token_budget")
        if token_budget is not None:
            tokens_used = int(run_state.get("tokens_used", 0))
            if tokens_used > int(token_budget):
                result.allowed = False
                result.violations.append(
                    f"Token budget exceeded: {tokens_used} > {token_budget}"
                )
            result.constraints_remaining["token_budget"] = max(
                0, int(token_budget) - tokens_used
            )

        # Tool calls check
        max_tools = constraints.get("max_tool_calls")
        if max_tools is not None:
            tools_used = int(run_state.get("tool_calls_made", 0))
            if tools_used > int(max_tools):
                result.allowed = False
                result.violations.append(
                    f"Tool call limit exceeded: {tools_used} > {max_tools}"
                )
            result.constraints_remaining["tool_calls"] = max(
                0, int(max_tools) - tools_used
            )

        # File modifications check
        max_files = constraints.get("max_files_modified")
        if max_files is not None:
            files_modified = int(run_state.get("files_modified", 0))
            if int(max_files) >= 0 and files_modified > int(max_files):
                result.allowed = False
                result.violations.append(
                    f"File modification limit exceeded: {files_modified} > {max_files}"
                )
            if int(max_files) >= 0:
                result.constraints_remaining["files_remaining"] = max(
                    0, int(max_files) - files_modified
                )

        return result

    # ------------------------------------------------------------------
    # Quality gates
    # ------------------------------------------------------------------

    def get_quality_gates(self, role_name: str) -> List[str]:
        """Get the quality gates for a role."""
        contract = self.loader.contracts.get(role_name)
        if not contract:
            return []
        gates = contract.get("quality_gates", [])
        return gates if isinstance(gates, list) else []

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    def get_escalation_path(self, role_name: str) -> Optional[str]:
        """Get the escalation path for a role."""
        contract = self.loader.contracts.get(role_name)
        if not contract:
            return None
        path = contract.get("escalation_path")
        return path if isinstance(path, str) else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_contract(
        self, role_name: str, result: Optional[PolicyCheckResult] = None
    ) -> Optional[Dict[str, Any]]:
        """Get contract and record error if not found."""
        contract = self.loader.contracts.get(role_name)
        if contract is None:
            msg = f"Role contract '{role_name}' not loaded"
            if result is not None:
                result.allowed = False
                result.violations.append(msg)
            else:
                logger.error(msg)
            return None
        return contract
