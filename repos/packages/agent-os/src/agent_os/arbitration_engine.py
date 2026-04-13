from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_loader import ModularConfigLoader

logger = logging.getLogger(__name__)

class ArbitrationEngine:
    """Orchestrates lane selection based on complex arbitration rules."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.config_loader = ModularConfigLoader(str(repo_root))
        self._rules = self.config_loader.get("routing_arbitration_rules")

    def resolve_decision(self, intent_profile: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates the target lane and selection reason."""
        decision = {
            "lane": "standard",
            "reason": "default_standard_lane",
            "escalation_path": []
        }

        # 1. Check for overrides in arbitration rules
        overrides = self._rules.get("overrides", [])
        for rule in overrides:
            if self._evaluate_condition(rule.get("condition", "False"), {**intent_profile, **context}):
                decision["lane"] = rule.get("lane")
                decision["reason"] = f"override_rule_{rule.get('name', 'unnamed')}"
                return decision

        # 2. Apply strategy priority
        strategy = self._rules.get("strategy_priority", ["fast", "quality", "swarm"])
        # Logic to pick lane based on intent + context score
        # For now, we use a simple heuristic if no override matched
        return decision

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluates a rule condition against the current context.
        Supports simple clauses and OR combinations.
        """
        try:
            # Tokenize and evaluate simple comparison clauses
            # Pattern: property_name > value
            def eval_clause(clause: str) -> bool:
                clause = clause.strip()
                match = re.search(r"(\w+)\s*([<>=!]+)\s*([\d\.]+)", clause)
                if not match:
                    return False
                
                key, op, val = match.groups()
                # Use property_name + "_score" mapping if needed (intent profiles use ambiguity, novelty etc)
                # But rules might use ambiguity_score
                ctx_key = key
                if key not in context and key.endswith("_score"):
                    ctx_key = key[:-6]
                
                left_val = float(context.get(ctx_key, 0.0))
                right_val = float(val)
                
                if op == ">": return left_val > right_val
                if op == "<": return left_val < right_val
                if op == ">=": return left_val >= right_val
                if op == "<=": return left_val <= right_val
                if op == "==": return left_val == right_val
                return False

            if " OR " in condition:
                return any(eval_clause(c) for c in condition.split(" OR "))
            if " AND " in condition:
                return all(eval_clause(c) for c in condition.split(" AND "))
            
            return eval_clause(condition)

        except Exception as exc:
            logger.error("Failed to evaluate arbitration condition '%s': %s", condition, exc)
            return False
