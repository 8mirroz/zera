"""Tests for WorkflowRouter — workflow-first routing layer.

Covers:
- Workflow match by name and intent_class
- Fallback to UnifiedRouter when no workflow matches
- Complexity floor enforcement
- Region profile constraints
- list_workflows / get_workflow accessors
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.workflow_router import WorkflowRouter


class TestWorkflowRouterMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = WorkflowRouter(repo_root=ROOT)

    def test_deep_research_matched_by_name(self):
        result = self.router.route("deep_research", "C2")
        self.assertEqual(result["workflow_name"], "deep_research")
        self.assertEqual(result["routing_source"], "workflow_first")

    def test_deep_research_has_steps(self):
        result = self.router.route("deep_research", "C3")
        self.assertIsInstance(result["workflow_steps"], list)
        self.assertGreater(len(result["workflow_steps"]), 0)

    def test_deep_research_has_quality_gates(self):
        result = self.router.route("deep_research", "C3")
        gates = result["quality_gates"]
        # parse_simple_yaml may return inline list as string — normalize
        if isinstance(gates, str):
            gates = [g.strip().strip("[]") for g in gates.split(",")]
        self.assertGreater(len(gates), 0)

    def test_deep_research_has_memory_scope(self):
        result = self.router.route("deep_research", "C3")
        self.assertEqual(result["memory_scope"], "project")

    def test_codegen_matched(self):
        result = self.router.route("codegen", "C2")
        self.assertEqual(result["workflow_name"], "codegen")

    def test_spreadsheet_build_matched(self):
        result = self.router.route("spreadsheet_build", "C2")
        self.assertEqual(result["workflow_name"], "spreadsheet_build")

    def test_estimator_build_matched(self):
        result = self.router.route("estimator_build", "C2")
        self.assertEqual(result["workflow_name"], "estimator_build")

    def test_unknown_intent_falls_back_to_unified(self):
        result = self.router.route("T3", "C2")
        self.assertEqual(result["routing_source"], "unified_fallback")
        self.assertIsNone(result["workflow_name"])
        self.assertIn("primary_model", result)

    def test_fallback_still_has_primary_model(self):
        result = self.router.route("T1", "C1")
        self.assertTrue(result["primary_model"])


class TestWorkflowRouterComplexityFloor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = WorkflowRouter(repo_root=ROOT)

    def test_deep_research_floor_c3_applied_when_c1_requested(self):
        """deep_research has complexity_floor: C3 — C1 request should be bumped."""
        result = self.router.route("deep_research", "C1")
        self.assertEqual(result["complexity"], "C3")
        self.assertTrue(result.get("complexity_floor_applied"))

    def test_deep_research_c4_not_downgraded(self):
        """C4 >= floor C3 — no floor applied."""
        result = self.router.route("deep_research", "C4")
        self.assertEqual(result["complexity"], "C4")
        self.assertFalse(result.get("complexity_floor_applied", False))

    def test_codegen_floor_c2_applied_when_c1_requested(self):
        result = self.router.route("codegen", "C1")
        self.assertEqual(result["complexity"], "C2")
        self.assertTrue(result.get("complexity_floor_applied"))


class TestWorkflowRouterRegionProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = WorkflowRouter(repo_root=ROOT)

    def test_global_west_no_fallback(self):
        result = self.router.route(
            "deep_research", "C3",
            context={"region_profile": "global_west"}
        )
        self.assertFalse(result.get("region_fallback_applied", False))
        self.assertEqual(result.get("region_profile"), "global_west")

    def test_region_profile_stored_in_result(self):
        result = self.router.route(
            "codegen", "C2",
            context={"region_profile": "russia_adapted"}
        )
        self.assertEqual(result.get("region_profile"), "russia_adapted")


class TestWorkflowRouterAccessors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = WorkflowRouter(repo_root=ROOT)

    def test_list_workflows_returns_known_names(self):
        names = self.router.list_workflows()
        self.assertIn("deep_research", names)
        self.assertIn("codegen", names)
        self.assertIn("spreadsheet_build", names)
        self.assertIn("estimator_build", names)

    def test_get_workflow_returns_dict(self):
        wf = self.router.get_workflow("deep_research")
        self.assertIsInstance(wf, dict)
        self.assertIn("steps", wf)

    def test_get_workflow_unknown_returns_none(self):
        self.assertIsNone(self.router.get_workflow("nonexistent_workflow_xyz"))


class TestWorkflowRouterDeterminism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = WorkflowRouter(repo_root=ROOT)

    def test_same_input_same_output(self):
        r1 = self.router.route("deep_research", "C3")
        r2 = self.router.route("deep_research", "C3")
        self.assertEqual(r1, r2)

    def test_all_known_workflows_route_without_error(self):
        for name in self.router.list_workflows():
            with self.subTest(workflow=name):
                result = self.router.route(name, "C3")
                self.assertIn("primary_model", result)
                self.assertEqual(result["workflow_name"], name)


if __name__ == "__main__":
    unittest.main()
