"""
Config Validation Tests — Parse all YAML/JSON configs, verify structure.

Ensures:
- All orchestrator YAML files parse correctly
- All tooling JSON files parse correctly (excluding .DEPRECATED)
- .DEPRECATED marker files exist for legacy configs
- Template manifest is complete (T1-T7)
- Role contracts have required keys
- Router.yaml has version field and all C1-C5 tiers
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]


class TestYamlConfigsParse(unittest.TestCase):
    """All orchestrator YAML files must parse as valid YAML."""

    def test_orchestrator_yaml_files_parse(self):
        yaml_dir = ROOT / "configs" / "orchestrator"
        yaml_files = list(yaml_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "No YAML files found in orchestrator/")

        for path in yaml_files:
            with self.subTest(file=path.name):
                with open(path) as f:
                    data = yaml.safe_load(f)
                self.assertIsNotNone(data, f"{path.name} parsed as None/empty")

    def test_role_contracts_yaml_parse(self):
        contracts_dir = ROOT / "configs" / "orchestrator" / "role_contracts"
        yaml_files = list(contracts_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "No role contract YAML files found")

        for path in yaml_files:
            with self.subTest(file=path.name):
                with open(path) as f:
                    data = yaml.safe_load(f)
                self.assertIsNotNone(data, f"{path.name} parsed as None/empty")


class TestJsonConfigsParse(unittest.TestCase):
    """All tooling JSON files (excluding .DEPRECATED) must parse."""

    def test_tooling_json_files_parse(self):
        json_dir = ROOT / "configs" / "tooling"
        json_files = [p for p in json_dir.glob("*.json") if ".DEPRECATED" not in p.name]
        self.assertGreater(len(json_files), 0, "No JSON files found in tooling/")

        for path in json_files:
            with self.subTest(file=path.name):
                with open(path) as f:
                    data = json.load(f)
                self.assertIsNotNone(data, f"{path.name} parsed as None/empty")


class TestDeprecatedFilesExist(unittest.TestCase):
    """Legacy .DEPRECATED marker files must exist."""

    def test_model_routing_json_deprecated_exists(self):
        path = ROOT / "configs" / "tooling" / "model_routing.json.DEPRECATED"
        self.assertTrue(path.exists(), "model_routing.json.DEPRECATED not found")


class TestTemplateManifest(unittest.TestCase):
    """All 7 compressed templates T1-T7 must exist."""

    def test_all_seven_templates_exist(self):
        templates_dir = ROOT / ".agent" / "templates" / "compressed"
        for i in range(1, 8):
            with self.subTest(template=f"T{i}"):
                matches = list(templates_dir.glob(f"T{i}_*.md"))
                self.assertGreater(len(matches), 0,
                                   f"No T{i}_*.md template found in compressed/")


class TestRoleContractsStructure(unittest.TestCase):
    """Each role contract must have role, responsibilities, forbidden_from keys."""

    def test_required_keys_present(self):
        contracts_dir = ROOT / "configs" / "orchestrator" / "role_contracts"
        for path in contracts_dir.glob("*.yaml"):
            with self.subTest(file=path.name):
                with open(path) as f:
                    data = yaml.safe_load(f)
                self.assertIn("role", data, f"{path.name} missing 'role'")
                self.assertIn("responsibilities", data, f"{path.name} missing 'responsibilities'")
                self.assertIn("forbidden_from", data, f"{path.name} missing 'forbidden_from'")


class TestRouterYamlStructure(unittest.TestCase):
    """Router.yaml must have version field and all C1-C5 tiers."""

    @classmethod
    def setUpClass(cls):
        router_path = ROOT / "configs" / "orchestrator" / "router.yaml"
        with open(router_path) as f:
            cls.config = yaml.safe_load(f)

    def test_version_field_exists(self):
        self.assertIn("version", self.config)

    def test_all_tiers_defined(self):
        tiers = self.config["routing"]["tiers"]
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            with self.subTest(tier=tier):
                self.assertIn(tier, tiers, f"Tier {tier} not defined in router.yaml")


class TestHarnessConfigs(unittest.TestCase):
    """Harness Engineering v1 config contracts."""

    def test_harness_map_exists(self):
        path = ROOT / "docs" / "ki" / "AGENT_HARNESS_MAP.md"
        self.assertTrue(path.exists(), "AGENT_HARNESS_MAP.md must be the repo-local harness map")

    def test_evaluation_harness_scenarios_present(self):
        path = ROOT / "configs" / "tooling" / "evaluation-harness.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        scenarios = set(data.get("scenario_coverage", []))
        for scenario in [
            "context_map_retrieval",
            "doc_staleness_detection",
            "worktree_validation_evidence",
            "harness_gardening_candidate",
        ]:
            with self.subTest(scenario=scenario):
                self.assertIn(scenario, scenarios)

    def test_background_jobs_include_harness_gardening(self):
        path = ROOT / "configs" / "tooling" / "background_jobs.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        jobs = data.get("jobs", {})
        self.assertIn("harness_gardening", jobs)
        self.assertEqual(jobs["harness_gardening"]["escalation_rule"], "queue_review")

    def test_benchmark_suite_includes_harness_cases(self):
        path = ROOT / "configs" / "tooling" / "benchmark_suite.json"
        with open(path) as f:
            data = json.load(f)
        case_ids = {row.get("id") for row in data.get("test_cases", [])}
        for case_id in [
            "bench-context-map-retrieval",
            "bench-doc-staleness-detection",
            "bench-worktree-validation-evidence",
            "bench-harness-gardening-candidate",
        ]:
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, case_ids)


if __name__ == "__main__":
    unittest.main()
