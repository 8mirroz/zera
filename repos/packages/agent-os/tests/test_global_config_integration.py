"""Tests for global config integration:
- WorkflowRouter + observability emit_workflow_event
- RiskClassifier connector registry integration
- configs/global/ YAML files parse correctly
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.workflow_router import WorkflowRouter
from agent_os.risk_classifier import RiskClassifier
from agent_os.observability import emit_workflow_event


class TestGlobalConfigsParse(unittest.TestCase):
    """All configs/global/ YAML files must parse as valid YAML."""

    def test_global_yaml_files_parse(self):
        global_dir = ROOT / "configs" / "global"
        yaml_files = list(global_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "No YAML files in configs/global/")
        for path in yaml_files:
            with self.subTest(file=path.name):
                with open(path) as f:
                    data = yaml.safe_load(f)
                self.assertIsNotNone(data, f"{path.name} parsed as None")

    def test_vertical_packs_parse(self):
        packs_dir = ROOT / "configs" / "vertical_packs"
        yaml_files = list(packs_dir.glob("*.yaml"))
        self.assertGreater(len(yaml_files), 0, "No YAML files in configs/vertical_packs/")
        for path in yaml_files:
            with self.subTest(file=path.name):
                with open(path) as f:
                    data = yaml.safe_load(f)
                self.assertIsNotNone(data)

    def test_memory_policy_has_layers(self):
        path = ROOT / "configs" / "global" / "memory_policy.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        self.assertIn("memory_layers", data)
        layers = data["memory_layers"]
        for scope in ("session", "project", "workspace", "user_preferences"):
            with self.subTest(scope=scope):
                self.assertIn(scope, layers)

    def test_workflow_graphs_has_workflows(self):
        path = ROOT / "configs" / "global" / "workflow_graphs.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        self.assertIn("workflows", data)
        wfs = data["workflows"]
        for name in ("deep_research", "codegen", "spreadsheet_build", "estimator_build"):
            with self.subTest(workflow=name):
                self.assertIn(name, wfs)
                self.assertIn("steps", wfs[name])
                self.assertIn("quality_gates", wfs[name])

    def test_connectors_registry_has_required_connectors(self):
        path = ROOT / "configs" / "global" / "connectors_registry.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        connectors = data.get("connectors", {})
        for name in ("notion", "google_drive", "github", "gmail", "calendar"):
            with self.subTest(connector=name):
                self.assertIn(name, connectors)
                self.assertIn("risk_level", connectors[name])

    def test_region_profiles_has_required_profiles(self):
        path = ROOT / "configs" / "global" / "region_profiles.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        profiles = data.get("profiles", {})
        for name in ("global_west", "russia_adapted", "privacy_first"):
            with self.subTest(profile=name):
                self.assertIn(name, profiles)

    def test_vertical_packs_have_required_fields(self):
        packs_dir = ROOT / "configs" / "vertical_packs"
        for path in packs_dir.glob("*.yaml"):
            with self.subTest(pack=path.name):
                with open(path) as f:
                    data = yaml.safe_load(f)
                self.assertIn("pack", data)
                self.assertIn("workflows", data)
                self.assertIn("quality_gates", data)


class TestRiskClassifierConnectorIntegration(unittest.TestCase):
    """RiskClassifier should use connectors_registry.yaml risk levels."""

    @classmethod
    def setUpClass(cls):
        cls.classifier = RiskClassifier(repo_root=ROOT)

    def test_github_action_elevated_risk(self):
        """github has risk_level: high in registry → should elevate classification."""
        result = self.classifier.classify("github_push")
        self.assertIn("connector risk: high", result.reason)

    def test_gmail_action_elevated_risk(self):
        result = self.classifier.classify("gmail_send")
        self.assertIn("connector risk", result.reason)

    def test_notion_action_medium_risk(self):
        result = self.classifier.classify("notion_write")
        self.assertIn("connector risk: medium", result.reason)

    def test_unknown_action_no_connector_risk(self):
        result = self.classifier.classify("internal_compute")
        self.assertNotIn("connector risk", result.reason)

    def test_classifier_without_repo_root_still_works(self):
        """Backward compat: RiskClassifier() without repo_root."""
        c = RiskClassifier()
        result = c.classify("delete_file")
        self.assertEqual(result.risk_class, "destructive")

    def test_financial_action_still_classified(self):
        result = self.classifier.classify("payment_process")
        self.assertEqual(result.risk_class, "financial")


class TestObservabilityWorkflowEvent(unittest.TestCase):
    """emit_workflow_event writes correct fields to trace log."""

    def test_emit_workflow_event_writes_to_log(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = str(Path(tmpdir) / "traces.jsonl")
            os.environ["AGENT_OS_TRACE_FILE"] = trace_file
            try:
                emit_workflow_event(
                    "deep_research",
                    "completed",
                    duration_ms=1234.5,
                    token_cost=0.042,
                    tool_calls=7,
                    quality_gate_failures=0,
                    retry_count=1,
                    memory_hit_rate=0.75,
                    region_profile_used="global_west",
                )
                with open(trace_file) as f:
                    row = json.loads(f.readline())
                self.assertEqual(row["event_type"], "workflow_completed")
                self.assertEqual(row["workflow_name"], "deep_research")
                self.assertEqual(row["status"], "completed")
                self.assertEqual(row["duration_ms"], 1234.5)
                self.assertEqual(row["token_cost"], 0.042)
                self.assertEqual(row["tool_calls"], 7)
                self.assertEqual(row["quality_gate_failures"], 0)
                self.assertEqual(row["retry_count"], 1)
                self.assertEqual(row["memory_hit_rate"], 0.75)
                self.assertEqual(row["region_profile_used"], "global_west")
                self.assertEqual(row["component"], "workflow")
            finally:
                del os.environ["AGENT_OS_TRACE_FILE"]

    def test_emit_workflow_event_has_timestamp(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = str(Path(tmpdir) / "traces.jsonl")
            os.environ["AGENT_OS_TRACE_FILE"] = trace_file
            try:
                emit_workflow_event("codegen", "started")
                with open(trace_file) as f:
                    row = json.loads(f.readline())
                self.assertIn("ts", row)
                self.assertIn("run_id", row)
            finally:
                del os.environ["AGENT_OS_TRACE_FILE"]


class TestWorkflowRouterQualityGateIntegration(unittest.TestCase):
    """WorkflowRouter quality_gates should match quality_gates.yaml definitions."""

    @classmethod
    def setUpClass(cls):
        cls.router = WorkflowRouter(repo_root=ROOT)

    def test_deep_research_gates_include_factual_verification(self):
        result = self.router.route("deep_research", "C3")
        self.assertIn("factual_verification", result["quality_gates"])

    def test_codegen_gates_include_lint_check(self):
        result = self.router.route("codegen", "C2")
        gates = result["quality_gates"]
        gates_str = str(gates)  # handles both list and inline-string from parse_simple_yaml
        self.assertIn("compile_or_lint_check", gates_str)

    def test_spreadsheet_gates_include_formula_integrity(self):
        result = self.router.route("spreadsheet_build", "C2")
        self.assertIn("formula_integrity", result["quality_gates"])

    def test_estimator_gates_include_item_traceability(self):
        result = self.router.route("estimator_build", "C3")
        self.assertIn("item_traceability", result["quality_gates"])


if __name__ == "__main__":
    unittest.main()
