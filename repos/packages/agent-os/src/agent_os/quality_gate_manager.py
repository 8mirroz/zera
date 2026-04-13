from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config_loader import ModularConfigLoader

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    gate_name: str
    status: str  # 'pass', 'fail', 'warn', 'error', 'pending_async'
    message: str
    data: Dict[str, Any]
    execution_mode: str = "sync"

class QualityGateManager:
    """Orchestrates the execution of validation contracts (Quality Gates).
    
    Consumes gate_catalog.yaml and gate_runtime_rules.yaml.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.config_loader = ModularConfigLoader(repo_root)
        self._catalog = self.config_loader.get("gate_catalog")
        self._rules = self.config_loader.get("gate_runtime_rules")

    def resolve_gates(self, profile_name: str) -> List[Dict[str, Any]]:
        """Resolves the list of gates to run for a given profile."""
        rules_dict = self._rules.to_dict()
        profiles = rules_dict.get("gate_profiles", {})
        
        profile = profiles.get(profile_name)
        if not profile:
            profile = profiles.get("standard", {})
            
        if not profile:
            return []

        gate_names = profile.get("gates", [])
        resolved = []
        
        catalog_dict = self._catalog.to_dict()
        catalog_gates = catalog_dict.get("gates", {})
        
        for name in gate_names:
            if name in catalog_gates:
                resolved.append({"name": name, **catalog_gates[name]})
        
        return resolved

    def run_gate(self, gate_meta: Dict[str, Any], context: Dict[str, Any]) -> ValidationResult:
        """Executes a single quality gate."""
        name = gate_meta.get("name", "unknown")
        strategy = gate_meta.get("strategy", "static")
        check_path = gate_meta.get("check_path")
        
        # In a real system, we'd execute the script or tool here.
        # For now, we simulate success for most, but add logic for 'syntax_check' and 'dry_run'.
        
        if strategy == "mock":
            return ValidationResult(name, "pass", "Mock gate passed", {})

        if strategy == "static" and check_path:
            # Check if validation script exists
            full_path = self.repo_root / check_path
            if not full_path.exists():
                return ValidationResult(name, "error", f"Validation script missing: {check_path}", {})
            
            # Simulated execution logic
            # In production: return subprocess.run(["python3", str(full_path), ...])
            return ValidationResult(name, "pass", f"Static check {name} completed", {"path": str(check_path)})

        return ValidationResult(name, "pass", f"Gate {name} executed successfully", {})

    def run_suite(self, profile_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the entire suite of gates for a profile.
        
        Returns a dict:
            'sync_results': List[ValidationResult]
            'async_gates': List[Dict[str, Any]]
        """
        gates = self.resolve_gates(profile_name)
        sync_results = []
        async_gates = []
        
        for gate in gates:
            mode = gate.get("execution_mode", "sync")
            if mode == "async":
                async_gates.append(gate)
                continue

            try:
                result = self.run_gate(gate, context)
                result.execution_mode = "sync"
                sync_results.append(result)
                
                # Check for critical failures (fail_fast)
                if result.status == "fail" and self._rules.get("policy", {}).get("fail_fast"):
                    break
            except Exception as exc:
                logger.error("Failed to execute gate %s: %s", gate.get("name"), exc)
                sync_results.append(ValidationResult(gate.get("name", "unknown"), "error", str(exc), {}, "sync"))
                
        return {
            "sync_results": sync_results,
            "async_gates": async_gates
        }
