from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_loader import ModularConfigLoader

logger = logging.getLogger(__name__)

class PlatformController:
    """Executable logic for Platform Mode Switching and Autonomy Control.
    
    Consumes platform_arbitration_rules.yaml and implements mode selector logic.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.config_loader = ModularConfigLoader(repo_root)
        self._rules = self.config_loader.get("platform_arbitration_rules")

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Simple expression evaluator compatible with platform rules.
        
        Supports:
        - "intent_class in [class1, class2]"
        - "task_tags contains [tag1]"
        - "complexity > C2"
        """
        try:
            cond = condition.lower()
            
            # Pattern: var in [a, b, c]
            if " in [" in cond:
                var_name, list_str = cond.split(" in [")
                targets = [s.strip() for s in list_str.rstrip("]").split(",")]
                actual_val = str(context.get(var_name.strip(), "")).lower()
                return actual_val in targets

            # Pattern: task_tags contains [tag1]
            if "contains [" in cond:
                parts = cond.split("contains [")
                tag_str = parts[1].rstrip("]").replace(" ", "")
                required_tags = tag_str.split(",")
                actual_tags = [t.lower() for t in context.get("task_tags", [])]
                return any(tag in actual_tags for tag in required_tags)

            # Pattern: var > value / var == value
            for op in [">=", "<=", ">", "<", "=="]:
                if op in cond:
                    var_name, val_str = [s.strip() for s in cond.split(op)]
                    actual_val = context.get(var_name)
                    if actual_val is None:
                        return False
                    
                    # Special handling for complexity (C1 < C2 < C3 ...)
                    if var_name == "complexity":
                        try:
                            actual_tier = int(str(actual_val).lstrip("C") or "0")
                            threshold_tier = int(val_str.lstrip("c") or "0")
                            if op == ">": return actual_tier > threshold_tier
                            if op == ">=": return actual_tier >= threshold_tier
                            if op == "<": return actual_tier < threshold_tier
                            if op == "<=": return actual_tier <= threshold_tier
                            if op == "==": return actual_tier == threshold_tier
                        except ValueError: pass

                    try:
                        threshold = float(val_str)
                        actual_val = float(actual_val)
                        if op == ">": return actual_val > threshold
                        if op == ">=": return actual_val >= threshold
                        if op == "<": return actual_val < threshold
                        if op == "<=": return actual_val <= threshold
                        if op == "==": return actual_val == threshold
                    except ValueError:
                        if op == "==": return str(actual_val).lower() == val_str.lower()
                        return False

        except Exception as exc:
            logger.debug("PlatformController skip condition '%s': %s", condition, exc)
        return False

    def resolve_mode(self, context: Dict[str, Any]) -> str:
        """Determines the active platform mode based on rules and context.
        
        Context should include:
        - intent_class (e.g., 'codegen', 'analysis')
        - complexity (e.g., 'C1', 'C3')
        - task_tags
        - user_mentions_direct_mode
        """
        logic = self._rules.get("arbitration_logic", {})
        overrides = logic.get("mode_selection_overrides", [])
        
        # 1. Check User Preference (highest priority in rules)
        user_pref = context.get("user_mentions_direct_mode")
        if user_pref and user_pref in ["consumer", "pro"]:
            return user_pref

        # 2. Check Overrides
        for rule in overrides:
            if self._evaluate_condition(rule.get("if", ""), context):
                action = rule.get("action", "")
                if action.startswith("force_mode:"):
                    return action.split(":")[1].strip()
                if action == "apply_user_preference":
                    if user_pref: return user_pref

        # 3. Default to fallback
        return self._rules.get("fallback_logic", {}).get("default_mode", "hybrid")
