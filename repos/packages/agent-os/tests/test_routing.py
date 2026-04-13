"""
Routing Determinism Tests — T1-T7 × C1-C5 matrix.

Tests that UnifiedRouter produces deterministic, valid routing results
for all 35 task_type × complexity combinations, plus escalation logic.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.model_router import UnifiedRouter

TASK_TYPES = ["T1", "T2", "T3", "T4", "T5", "T6", "T7"]
COMPLEXITIES = ["C1", "C2", "C3", "C4", "C5"]

# Expected tier mapping — model_tier values returned by UnifiedRouter
EXPECTED_TIERS = {
    "C1": "worker",
    "C2": "worker",
    "C3": "specialist",
    "C4": "specialist",
    "C5": "specialist",
}


class TestRoutingDeterminism(unittest.TestCase):
    """Test that routing is deterministic for all T×C combinations."""

    @classmethod
    def setUpClass(cls):
        cls.router = UnifiedRouter(repo_root=ROOT)

    def test_all_35_combinations_deterministic(self):
        """Route twice for each T×C pair → identical results."""
        for task_type in TASK_TYPES:
            for complexity in COMPLEXITIES:
                with self.subTest(task_type=task_type, complexity=complexity):
                    result1 = self.router.route(task_type, complexity)
                    result2 = self.router.route(task_type, complexity)
                    self.assertEqual(result1, result2,
                                     f"Non-deterministic routing for {task_type}/{complexity}")

    def test_all_35_combinations_have_primary_model(self):
        """Every routing result must have a non-empty primary_model."""
        for task_type in TASK_TYPES:
            for complexity in COMPLEXITIES:
                with self.subTest(task_type=task_type, complexity=complexity):
                    result = self.router.route(task_type, complexity)
                    self.assertIn("primary_model", result)
                    self.assertTrue(result["primary_model"],
                                    f"Empty primary_model for {task_type}/{complexity}")

    def test_model_tier_matches_router_yaml(self):
        """model_tier in route result should match expected tier from router.yaml."""
        for task_type in TASK_TYPES:
            for complexity in COMPLEXITIES:
                with self.subTest(task_type=task_type, complexity=complexity):
                    result = self.router.route(task_type, complexity)
                    self.assertIn("model_tier", result)
                    expected = EXPECTED_TIERS[complexity]
                    self.assertEqual(result["model_tier"], expected,
                                     f"Tier mismatch for {task_type}/{complexity}: "
                                     f"got {result['model_tier']}, expected {expected}")


class TestEscalation(unittest.TestCase):
    """Test tier escalation logic."""

    @classmethod
    def setUpClass(cls):
        cls.router = UnifiedRouter(repo_root=ROOT)

    def test_c1_escalates_to_c2(self):
        """C1 + failure → C2 (1 step)."""
        result = self.router.escalate("C1", "failure")
        self.assertEqual(result["escalated_tier"], "C2")

    def test_c3_escalates_to_c4(self):
        """C3 + failure → C4 (1 step)."""
        result = self.router.escalate("C3", "failure")
        self.assertEqual(result["escalated_tier"], "C4")

    def test_c4_escalates_to_c5(self):
        """C4 + failure → C5."""
        result = self.router.escalate("C4", "failure")
        self.assertEqual(result["escalated_tier"], "C5")

    def test_c5_stays_at_c5(self):
        """C5 + failure → C5 (cannot escalate further)."""
        result = self.router.escalate("C5", "failure")
        self.assertEqual(result["escalated_tier"], "C5")

    def test_escalation_preserves_reason(self):
        """Escalation result includes the original reason."""
        result = self.router.escalate("C2", "timeout")
        self.assertEqual(result["escalation_reason"], "timeout")
        self.assertEqual(result["original_tier"], "C2")


if __name__ == "__main__":
    unittest.main()
