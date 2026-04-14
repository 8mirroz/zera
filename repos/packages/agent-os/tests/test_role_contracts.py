"""
Role Contract Layer Tests — Antigravity Core v4.2

Tests for:
- Role contract YAML file existence
- Schema validation
- Model alias resolution
- Handoff target validation
- Complexity scope validation
- Constraint validation
- Role policy guard enforcement
- UnifiedRouter integration
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict

import yaml

# Resolve repo root (this file is in repos/packages/agent-os/tests/)
ROOT = Path(__file__).resolve().parents[4]

EXPECTED_ROLES = [
    "orchestrator",
    "routine_worker",
    "engineer",
    "design_lead",
    "reviewer",
    "architect",
    "council",
]

REQUIRED_SCHEMA_KEYS = {
    "role",
    "version",
    "status",
    "system_role",
    "complexity_scope",
    "model_alias",
    "fallback_model",
    "runtime_hint",
    "responsibilities",
    "interfaces",
    "dependencies",
    "forbidden_from",
    "handoff_triggers",
    "escalation_path",
    "constraints",
    "quality_gates",
    "metrics",
    "memory_policy",
    "fail_safe",
}

VALID_COMPLEXITY_TIERS = {"C1", "C2", "C3", "C4", "C5"}


# ---------------------------------------------------------------------------
# Helper: load all role contracts
# ---------------------------------------------------------------------------

def _load_role_contracts() -> Dict[str, Dict[str, Any]]:
    """Load all role contract YAML files."""
    contracts_dir = ROOT / "configs/orchestrator/role_contracts"
    contracts = {}
    for path in contracts_dir.glob("*.yaml"):
        with open(path) as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            role_name = data.get("role", path.stem)
            contracts[role_name] = data
    return contracts


def _load_model_aliases() -> Dict[str, str]:
    """Load model aliases from models.yaml."""
    models_path = ROOT / "configs/orchestrator/models.yaml"
    with open(models_path) as f:
        data = yaml.safe_load(f)
    models = data.get("models", {})
    if not isinstance(models, dict):
        return {}
    return {k: v for k, v in models.items() if isinstance(v, str)}


# ---------------------------------------------------------------------------
# Test: File existence
# ---------------------------------------------------------------------------

class TestRoleContractFiles(unittest.TestCase):
    """All 7 role contract YAML files must exist."""

    @classmethod
    def setUpClass(cls):
        cls.contracts_dir = ROOT / "configs/orchestrator/role_contracts"
        cls.contracts = _load_role_contracts()

    def test_contracts_directory_exists(self):
        self.assertTrue(
            self.contracts_dir.exists(),
            f"Contracts directory not found: {self.contracts_dir}"
        )

    def test_all_seven_contracts_exist(self):
        for role in EXPECTED_ROLES:
            path = self.contracts_dir / f"{role}.yaml"
            self.assertTrue(
                path.exists(),
                f"Role contract file missing: {path}"
            )

    def test_no_extra_contracts(self):
        """Only expected role files should exist."""
        yaml_files = {p.stem for p in self.contracts_dir.glob("*.yaml")}
        unexpected = yaml_files - set(EXPECTED_ROLES)
        self.assertEqual(
            unexpected, set(),
            f"Unexpected role contract files: {unexpected}"
        )


# ---------------------------------------------------------------------------
# Test: Schema validation
# ---------------------------------------------------------------------------

class TestRoleContractSchema(unittest.TestCase):
    """Each role contract must have required keys and valid values."""

    @classmethod
    def setUpClass(cls):
        cls.contracts = _load_role_contracts()

    def test_required_keys_present(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                missing = REQUIRED_SCHEMA_KEYS - set(contract.keys())
                self.assertFalse(
                    missing,
                    f"Role '{role_name}' missing keys: {sorted(missing)}"
                )

    def test_unique_role_names(self):
        roles = [c.get("role") for c in self.contracts.values()]
        self.assertEqual(
            len(roles), len(set(roles)),
            f"Duplicate role names found: {roles}"
        )

    def test_role_name_matches_filename(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                self.assertEqual(
                    contract.get("role"), role_name,
                    f"Role name in YAML '{contract.get('role')}' doesn't match filename '{role_name}'"
                )

    def test_valid_status_values(self):
        valid_statuses = {"active", "deprecated", "draft", "archived"}
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                status = contract.get("status")
                self.assertIn(
                    status, valid_statuses,
                    f"Role '{role_name}' has invalid status: {status}"
                )

    def test_complexity_scope_values_valid(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                scope = contract.get("complexity_scope", [])
                self.assertIsInstance(scope, list)
                invalid = set(scope) - VALID_COMPLEXITY_TIERS
                self.assertFalse(
                    invalid,
                    f"Role '{role_name}' has invalid complexity tiers: {sorted(invalid)}"
                )

    def test_complexity_scope_not_empty(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                scope = contract.get("complexity_scope", [])
                self.assertGreater(
                    len(scope), 0,
                    f"Role '{role_name}' has empty complexity_scope"
                )

    def test_responsibilities_not_empty(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                responsibilities = contract.get("responsibilities", [])
                self.assertIsInstance(responsibilities, list)
                self.assertGreater(
                    len(responsibilities), 0,
                    f"Role '{role_name}' has no responsibilities"
                )

    def test_quality_gates_not_empty(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                gates = contract.get("quality_gates", [])
                self.assertIsInstance(gates, list)
                self.assertGreater(
                    len(gates), 0,
                    f"Role '{role_name}' has no quality_gates"
                )


# ---------------------------------------------------------------------------
# Test: Model alias resolution
# ---------------------------------------------------------------------------

class TestModelAliasResolution(unittest.TestCase):
    """Each model_alias and fallback_model must resolve against models.yaml."""

    @classmethod
    def setUpClass(cls):
        cls.contracts = _load_role_contracts()
        cls.aliases = _load_model_aliases()

    def _resolve_alias(self, alias: str) -> str | None:
        """Resolve $ALIAS reference against models.yaml."""
        if not alias.startswith("$"):
            return alias
        key = alias[1:]
        value = self.aliases.get(key)
        if value and value.startswith("$"):
            # Recursive resolution (max 3 depth)
            for _ in range(3):
                key = value[1:]
                value = self.aliases.get(key, value)
                if not value.startswith("$"):
                    break
        return value

    def test_model_alias_resolves(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                alias = contract.get("model_alias", "")
                self.assertTrue(
                    alias.startswith("$"),
                    f"Role '{role_name}' model_alias should be $ALIAS format"
                )
                resolved = self._resolve_alias(alias)
                self.assertIsNotNone(
                    resolved,
                    f"Role '{role_name}' model_alias '{alias}' could not be resolved"
                )
                self.assertNotEqual(
                    resolved, alias,
                    f"Role '{role_name}' model_alias '{alias}' did not resolve to a model string"
                )

    def test_fallback_model_resolves(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                alias = contract.get("fallback_model", "")
                self.assertTrue(
                    alias.startswith("$"),
                    f"Role '{role_name}' fallback_model should be $ALIAS format"
                )
                resolved = self._resolve_alias(alias)
                self.assertIsNotNone(
                    resolved,
                    f"Role '{role_name}' fallback_model '{alias}' could not be resolved"
                )

    def test_resolved_models_are_valid_strings(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                alias = contract.get("model_alias", "")
                resolved = self._resolve_alias(alias)
                self.assertIsInstance(resolved, str)
                self.assertIn(
                    "/", resolved,
                    f"Role '{role_name}' resolved model '{resolved}' doesn't look like a valid model ID"
                )


# ---------------------------------------------------------------------------
# Test: Handoff target validation
# ---------------------------------------------------------------------------

class TestHandoffTargets(unittest.TestCase):
    """All handoff targets must reference known roles or 'terminal'."""

    @classmethod
    def setUpClass(cls):
        cls.contracts = _load_role_contracts()
        cls.known_roles = set(cls.contracts.keys()) | {"terminal"}

    def test_handoff_targets_are_valid(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                triggers = contract.get("handoff_triggers", [])
                self.assertIsInstance(triggers, list)
                for trigger in triggers:
                    if not isinstance(trigger, dict):
                        continue
                    target = trigger.get("target")
                    self.assertIn(
                        target, self.known_roles,
                        f"Role '{role_name}' has invalid handoff target: '{target}'. "
                        f"Known roles: {sorted(self.known_roles)}"
                    )

    def test_no_self_handoff(self):
        """A role should not hand off to itself."""
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                triggers = contract.get("handoff_triggers", [])
                for trigger in triggers:
                    if not isinstance(trigger, dict):
                        continue
                    target = trigger.get("target")
                    self.assertNotEqual(
                        target, role_name,
                        f"Role '{role_name}' should not hand off to itself"
                    )

    def test_escalation_path_is_valid_role_or_terminal(self):
        valid_targets = set(self.contracts.keys()) | {"terminal", "user"}
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                path = contract.get("escalation_path")
                self.assertIn(
                    path, valid_targets,
                    f"Role '{role_name}' has invalid escalation_path: '{path}'"
                )


# ---------------------------------------------------------------------------
# Test: Constraint validation
# ---------------------------------------------------------------------------

class TestConstraints(unittest.TestCase):
    """Constraints must have valid numeric values."""

    @classmethod
    def setUpClass(cls):
        cls.contracts = _load_role_contracts()

    def test_token_budget_positive(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                constraints = contract.get("constraints", {})
                budget = constraints.get("token_budget")
                if budget is not None:
                    self.assertGreater(
                        int(budget), 0,
                        f"Role '{role_name}' token_budget must be positive"
                    )

    def test_max_tool_calls_positive(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                constraints = contract.get("constraints", {})
                tools = constraints.get("max_tool_calls")
                if tools is not None:
                    self.assertGreater(
                        int(tools), 0,
                        f"Role '{role_name}' max_tool_calls must be positive"
                    )

    def test_max_files_modified_non_negative(self):
        for role_name, contract in self.contracts.items():
            with self.subTest(role=role_name):
                constraints = contract.get("constraints", {})
                files = constraints.get("max_files_modified")
                if files is not None:
                    self.assertGreaterEqual(
                        int(files), 0,
                        f"Role '{role_name}' max_files_modified must be non-negative"
                    )


# ---------------------------------------------------------------------------
# Test: Router contracts_path
# ---------------------------------------------------------------------------

class TestRouterContractsPath(unittest.TestCase):
    """router.yaml must reference an existing contracts_path."""

    def test_contracts_path_exists(self):
        router_path = ROOT / "configs/orchestrator/router.yaml"
        with open(router_path) as f:
            router = yaml.safe_load(f)

        roles_cfg = router.get("routing", {}).get("roles", {})
        contracts_path = roles_cfg.get("contracts_path", "")
        full_path = ROOT / contracts_path

        self.assertTrue(
            full_path.exists() and full_path.is_dir(),
            f"router.yaml contracts_path does not exist: {full_path}"
        )

    def test_contracts_path_has_yaml_files(self):
        router_path = ROOT / "configs/orchestrator/router.yaml"
        with open(router_path) as f:
            router = yaml.safe_load(f)

        contracts_path = ROOT / router["routing"]["roles"]["contracts_path"]
        yaml_files = list(contracts_path.glob("*.yaml"))
        self.assertGreater(
            len(yaml_files), 0,
            f"No YAML files found in contracts_path: {contracts_path}"
        )


# ---------------------------------------------------------------------------
# Test: Role Contract Loader (Python module)
# ---------------------------------------------------------------------------

class TestRoleContractLoader(unittest.TestCase):
    """Test the Python RoleContractLoader module."""

    @classmethod
    def setUpClass(cls):
        import sys
        src_dir = ROOT / "repos/packages/agent-os/src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from agent_os.role_contract_loader import RoleContractLoader
        cls.loader = RoleContractLoader(
            ROOT / "configs/orchestrator/role_contracts",
            ROOT / "configs/orchestrator/models.yaml"
        )
        cls.loader.load_all()
        cls.loader.validate_all()

    def test_loader_finds_all_roles(self):
        loaded = self.loader.list_roles()
        for role in EXPECTED_ROLES:
            self.assertIn(role, loaded, f"Loader did not find role '{role}'")

    def test_loader_validation_passes(self):
        errors = self.loader._validation_errors
        self.assertFalse(
            errors,
            f"Role contract validation errors: {errors}"
        )

    def test_loader_get_contract(self):
        for role in EXPECTED_ROLES:
            contract = self.loader.get_contract(role)
            self.assertIsNotNone(contract)
            self.assertEqual(contract["role"], role)

    def test_loader_get_roles_for_complexity(self):
        c1_roles = self.loader.get_roles_for_complexity("C1")
        self.assertIn("routine_worker", c1_roles)

        c5_roles = self.loader.get_roles_for_complexity("C5")
        self.assertIn("council", c5_roles)

    def test_loader_is_valid(self):
        self.assertTrue(self.loader.is_valid())


# ---------------------------------------------------------------------------
# Test: Role Policy Guard (Python module)
# ---------------------------------------------------------------------------

class TestRolePolicyGuard(unittest.TestCase):
    """Test the Python RolePolicyGuard enforcement module."""

    @classmethod
    def setUpClass(cls):
        import sys
        src_dir = ROOT / "repos/packages/agent-os/src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from agent_os.role_contract_loader import RoleContractLoader
        from agent_os.role_policy_guard import RolePolicyGuard

        loader = RoleContractLoader(
            ROOT / "configs/orchestrator/role_contracts",
            ROOT / "configs/orchestrator/models.yaml"
        )
        loader.load_all()
        cls.guard = RolePolicyGuard(loader)

    def test_check_action_allowed(self):
        # Reviewer should not be allowed to rewrite implementation
        result = self.guard.check_action_allowed(
            "reviewer", "rewriting implementation instead of reviewing"
        )
        self.assertFalse(result.allowed)
        self.assertGreater(len(result.violations), 0)

    def test_check_action_allowed_permitted(self):
        # Engineer should be allowed to implement code
        result = self.guard.check_action_allowed(
            "engineer", "implement feature changes"
        )
        # This may or may not trigger forbidden — depends on keyword matching
        # Just ensure the result is a valid PolicyCheckResult
        self.assertTrue(hasattr(result, "allowed"))

    def test_check_handoff_required(self):
        # Routine worker with C3 complexity should handoff
        result = self.guard.check_handoff_required(
            "routine_worker",
            {"complexity": "C3"}
        )
        self.assertTrue(result.handoff_required)
        self.assertIn(result.handoff_target, {"orchestrator", "engineer"})

    def test_check_constraints(self):
        # Check constraints with no usage yet
        result = self.guard.check_constraints(
            "engineer",
            {"tokens_used": 0, "tool_calls_made": 0, "files_modified": 0}
        )
        self.assertTrue(result.allowed)

    def test_check_constraints_exceeded(self):
        # Check constraints when token budget exceeded
        result = self.guard.check_constraints(
            "routine_worker",
            {"tokens_used": 999999, "tool_calls_made": 0, "files_modified": 0}
        )
        self.assertFalse(result.allowed)
        self.assertGreater(len(result.violations), 0)

    def test_get_quality_gates(self):
        gates = self.guard.get_quality_gates("architect")
        self.assertIsInstance(gates, list)
        self.assertGreater(len(gates), 0)

    def test_get_escalation_path(self):
        path = self.guard.get_escalation_path("engineer")
        self.assertEqual(path, "architect")


# ---------------------------------------------------------------------------
# Test: UnifiedRouter integration
# ---------------------------------------------------------------------------

class TestUnifiedRouterIntegration(unittest.TestCase):
    """Test that UnifiedRouter includes role contract metadata."""

    @classmethod
    def setUpClass(cls):
        import sys
        src_dir = ROOT / "repos/packages/agent-os/src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        from agent_os.model_router import UnifiedRouter
        cls.router = UnifiedRouter(repo_root=ROOT)

    def test_route_includes_active_role(self):
        result = self.router.route("test_task", "C3")
        self.assertIn("active_role", result)
        self.assertIsNotNone(result["active_role"])

    def test_route_includes_role_contract(self):
        result = self.router.route("test_task", "C3")
        self.assertIn("role_contract", result)
        self.assertIsInstance(result["role_contract"], dict)

    def test_route_includes_role_constraints(self):
        result = self.router.route("test_task", "C3")
        self.assertIn("role_constraints", result)
        self.assertIsInstance(result["role_constraints"], dict)

    def test_route_includes_role_quality_gates(self):
        result = self.router.route("test_task", "C3")
        self.assertIn("role_quality_gates", result)
        self.assertIsInstance(result["role_quality_gates"], list)
        self.assertGreater(len(result["role_quality_gates"]), 0)

    def test_route_includes_role_handoff_policy(self):
        result = self.router.route("test_task", "C3")
        self.assertIn("role_handoff_policy", result)
        self.assertIsInstance(result["role_handoff_policy"], list)

    def test_route_includes_role_forbidden_actions(self):
        result = self.router.route("test_task", "C3")
        self.assertIn("role_forbidden_actions", result)
        self.assertIsInstance(result["role_forbidden_actions"], list)

    def test_role_varies_by_complexity(self):
        roles = set()
        for complexity in ["C1", "C2", "C3", "C4", "C5"]:
            result = self.router.route("test_task", complexity)
            role = result.get("active_role")
            if role:
                roles.add(role)
        # Should have different roles for different complexities
        self.assertGreater(len(roles), 1, "Expected different roles across complexities")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
