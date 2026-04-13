import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_loader import ModularConfigLoader
from .approval_engine import ApprovalEngine

logger = logging.getLogger(__name__)

class ConnectorGater:
    """Policy-aware risk assessment for external integrations (Connectors).
    
    Consumes connector_risk_policy.yaml and connector_capability_registry.yaml.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.config_loader = ModularConfigLoader(str(repo_root))
        self._policy = self.config_loader.get("connector_risk_policy")
        self._registry = self.config_loader.get("connector_capability_registry")
        self.approval_engine = ApprovalEngine(repo_root)

    def assess_risk(self, connector_proposal: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates risk score and determines if action should be blocked."""
        # This is for specific action-level assessment
        return self._assess_generic(connector_proposal)

    def check_intent_risk(self, intent_class: str) -> Dict[str, Any]:
        """Higher level assessment based on task intent."""
        # For now, map intent to a pseudo-proposal
        pseudo_proposal = {"intent": intent_class}
        return self._assess_generic(pseudo_proposal)

    def request_approval(self, proposal: Dict[str, Any], risk_report: Dict[str, Any], run_id: str) -> str:
        """Utility to spawn a ticket in the ApprovalEngine."""
        intent = proposal.get("intent", "unknown")
        ticket = self.approval_engine.create_ticket(
            action_type=f"connector_execution:{intent}",
            risk_class=risk_report.get("risk_class", "high"),
            summary=risk_report.get("reason", "Action blocked by safety policy"),
            run_id=run_id,
            runtime_provider="AgentRuntime",
            persona_id=None,
            approval_policy="connector_risk_policy.yaml",
            proposal=proposal
        )
        return ticket.id

    def _assess_generic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        report = {
            "risk_score": 0.0,
            "action": "pass",
            "reason": "minimal_risk_defaults",
            "gates_required": [],
            "risk_class": "low"
        }

        # Simplified scoring logic based on intention
        intent = data.get("intent", "analysis")
        if intent in ["infrastructure", "write", "delete", "deployment"]:
            report["risk_score"] = 0.95
            # OPTIMAL SOLUTION: use pending_approval instead of hard block
            report["action"] = "pending_approval"
            report["risk_class"] = "critical"
            report["reason"] = f"Intent '{intent}' requires explicit human-in-the-loop approval due to safety policies."
            report["gates_required"] = ["human_in_the_loop", "security_audit"]
        elif intent in ["code_edit", "git_push"]:
            report["risk_score"] = 0.6
            report["action"] = "warn"
            report["risk_class"] = "medium"
            report["reason"] = "Intent requires moderate safety gates."
            report["gates_required"] = ["syntax_check"]

        return report
