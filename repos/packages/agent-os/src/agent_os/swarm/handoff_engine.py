from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set
from ..contracts import AgentOutput
from ..role_contract_loader import RoleContractLoader

logger = logging.getLogger(__name__)

class HandoffEngine:
    """Resolves the next agent role based on current agent output and triggers."""

    def __init__(self, contract_loader: RoleContractLoader) -> None:
        self.contract_loader = contract_loader

    def resolve_next_role(self, current_role: str, output: AgentOutput) -> Optional[str]:
        """Analyzes triggers to determine the next role."""
        try:
            contract = self.contract_loader.get_contract(current_role)
        except Exception:
            logger.warning("Contract not found for role %s, cannot resolve handoff.", current_role)
            return None

        triggers = contract.get("handoff_triggers", [])
        if not triggers:
            return None

        # Check explicit handoff_target from meta if present (highest priority)
        if isinstance(output.meta, dict) and output.meta.get("handoff_target"):
            return str(output.meta["handoff_target"])

        # Otherwise, evaluate triggers
        # A trigger has: 'condition_type', 'value', 'target'
        # Example: {condition_type: "status", value: "success", target: "engineer"}
        for trigger in triggers:
            if self._evaluate_trigger(trigger, output):
                return str(trigger.get("target"))

        return None

    def _evaluate_trigger(self, trigger: Dict[str, Any], output: AgentOutput) -> bool:
        """Simple evaluator for handoff triggers."""
        ctype = trigger.get("condition_type")
        value = trigger.get("value")
        
        if ctype == "status":
            return output.status == value
        
        if ctype == "contains_keyword":
            summary = output.diff_summary.lower()
            return str(value).lower() in summary

        return False
