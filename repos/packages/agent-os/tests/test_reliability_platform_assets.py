from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import pytest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[4]

ORCHESTRATOR_PATH = ROOT / "scripts" / "reliability_orchestrator.py"
if not ORCHESTRATOR_PATH.exists():
    pytest.skip(f"Script not found: {ORCHESTRATOR_PATH}", allow_module_level=True)

def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ORCHESTRATOR = _load_module("reliability_orchestrator", ROOT / "scripts" / "reliability_orchestrator.py")
VALIDATOR = _load_module("check_reliability_platform", ROOT / "scripts" / "validation" / "check_reliability_platform.py")


class TestReliabilityPlatformAssets(unittest.TestCase):
    def test_contract_files_define_required_profiles_and_suites(self) -> None:
        program = yaml.safe_load((ROOT / "configs" / "tooling" / "test_reliability_program.yaml").read_text(encoding="utf-8"))
        matrix = yaml.safe_load((ROOT / "configs" / "tooling" / "test_suite_matrix.yaml").read_text(encoding="utf-8"))
        debug_map = yaml.safe_load((ROOT / "configs" / "tooling" / "debug_surface_map.yaml").read_text(encoding="utf-8"))

        self.assertTrue({"local_quick", "pre_commit", "ci_required", "nightly", "all_non_benchmark"}.issubset(program["profiles"]))
        self.assertTrue({"unit", "contract", "integration", "smoke", "doctor", "benchmark", "governance", "regression"}.issubset(matrix["suites"]))
        self.assertTrue(
            {
                "syntax_or_parse",
                "contract_violation",
                "routing_logic",
                "governance_boundary",
                "tooling_or_env",
                "integration_surface",
                "benchmark_regression",
                "observability_gap",
                "doc_runtime_drift",
                "flaky_or_nondeterministic",
            }.issubset(debug_map["failure_classes"])
        )

    def test_orchestrator_resolves_pre_commit_profile(self) -> None:
        orch = ORCHESTRATOR.ReliabilityOrchestrator(ROOT)
        plan = orch.profile_plan("pre_commit")
        self.assertEqual([suite["suite"] for suite in plan["suites"]], ["contract", "smoke", "governance"])

    def test_debug_test_resolves_known_swarmctl_target(self) -> None:
        orch = ORCHESTRATOR.ReliabilityOrchestrator(ROOT)
        payload = orch.debug_test("test_swarmctl_runtime_routing.py")
        self.assertEqual(payload["suite"], "unit")
        self.assertEqual(payload["bucket"], "swarmctl-fast")
        self.assertIn("uv run pytest", payload["command"])

    def test_inventory_and_dry_run_emit_expected_artifacts(self) -> None:
        orch = ORCHESTRATOR.ReliabilityOrchestrator(ROOT)
        with tempfile.TemporaryDirectory() as td:
            temp_root = Path(td)
            orch.artifacts_root = temp_root / "outputs" / "reliability"
            orch.events_path = orch.artifacts_root / "events.jsonl"
            orch.latest_dir = orch.artifacts_root / "latest"
            orch.inventory_json = temp_root / "outputs" / "reliability" / "inventory" / "latest_inventory.json"
            orch.inventory_md = temp_root / "outputs" / "reliability" / "inventory" / "latest_inventory.md"

            inventory = orch.write_inventory()
            result = orch.run(["smoke"], dry_run=True, machine_readable=True)

            self.assertGreater(inventory["counts"]["tests"], 0)
            self.assertFalse(any("/.venv/" in path for path in inventory["tests"]))
            self.assertFalse(any(path.startswith("sandbox/") for path in inventory["tests"]))
            self.assertEqual(result["status"], "ok")
            self.assertTrue((orch.inventory_json).exists())
            self.assertTrue((orch.inventory_md).exists())
            self.assertTrue((orch.latest_dir / "suite-manifest.json").exists())
            self.assertTrue((orch.latest_dir / "failure-summary.json").exists())

    def test_validator_accepts_repo_state(self) -> None:
        self.assertTrue(VALIDATOR.validate_configs())
        self.assertTrue(VALIDATOR.validate_make_and_scripts())
        self.assertTrue(VALIDATOR.validate_ci_and_docs())


if __name__ == "__main__":
    unittest.main()
