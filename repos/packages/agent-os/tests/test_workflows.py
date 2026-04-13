"""
Workflow Tests — Ralph's Loop + Completion Gates.

Tests Ralph Loop stop conditions (including plateau_min_iterations guard)
and validates completion_gates.yaml contract per complexity tier.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.ralph_loop import RalphLoopConfig, RalphLoopEngine


# ---------------------------------------------------------------------------
# Ralph's Loop stop-condition tests
# ---------------------------------------------------------------------------


class TestRalphLoopHardLimit(unittest.TestCase):
    """Scenario 1: Hard limit stop — max_iterations reached."""

    def test_hard_limit_stops_at_max(self):
        config = RalphLoopConfig(
            max_iterations=7,
            min_iterations=3,
            min_acceptable_score=0.99,  # Unreachable
            min_score_delta=0.001,      # Tiny delta to avoid plateau
            run_id="test-hard-limit",
        )
        engine = RalphLoopEngine(config)

        for i in range(1, 8):
            engine.record_iteration({"id": f"c{i}"}, weighted_total=0.10 + i * 0.05)
            if engine.should_stop():
                break

        self.assertTrue(engine.state.stopped)
        self.assertEqual(engine.state.stop_reason, "max_iterations_reached")
        self.assertEqual(engine.state.iteration, 7)


class TestRalphLoopThreshold(unittest.TestCase):
    """Scenario 2: Threshold stop — score >= min_acceptable_score."""

    def test_threshold_stop_at_iteration_3(self):
        config = RalphLoopConfig(
            max_iterations=7,
            min_iterations=3,
            min_acceptable_score=0.70,
            min_score_delta=0.05,
            run_id="test-threshold",
        )
        engine = RalphLoopEngine(config)

        # Iterations 1-2: below threshold with good delta
        engine.record_iteration({"id": "c1"}, weighted_total=0.40)
        self.assertFalse(engine.should_stop())
        engine.record_iteration({"id": "c2"}, weighted_total=0.55)
        self.assertFalse(engine.should_stop())

        # Iteration 3: above threshold, min_iterations met
        engine.record_iteration({"id": "c3"}, weighted_total=0.85)
        self.assertTrue(engine.should_stop())
        self.assertEqual(engine.state.stop_reason, "threshold_met")


class TestRalphLoopPlateauMinIterations(unittest.TestCase):
    """Scenario 3: Plateau detection with min_iterations guard.

    The existing test shows plateau triggers at iteration 3 (when min_iterations=3).
    This test uses a higher min_iterations to verify the guard works:
    plateau at iteration 4 should NOT stop if min_iterations=5;
    plateau at iteration 5+ SHOULD stop.
    """

    def test_plateau_at_iter4_does_not_stop_with_min5(self):
        """Small delta at iteration 4 should NOT stop when min_iterations=5."""
        config = RalphLoopConfig(
            max_iterations=10,
            min_iterations=5,
            min_acceptable_score=0.99,  # Unreachable
            min_score_delta=0.05,
            run_id="test-plateau-guard",
        )
        engine = RalphLoopEngine(config)

        # Build up with good deltas
        engine.record_iteration({"id": "c1"}, weighted_total=0.40)
        self.assertFalse(engine.should_stop())
        engine.record_iteration({"id": "c2"}, weighted_total=0.50)
        self.assertFalse(engine.should_stop())
        engine.record_iteration({"id": "c3"}, weighted_total=0.60)
        self.assertFalse(engine.should_stop())

        # Iteration 4: small delta but min_iterations=5 not met
        engine.record_iteration({"id": "c4"}, weighted_total=0.61)
        self.assertFalse(engine.should_stop())  # Guard prevents stop

    def test_plateau_at_iter5_stops_with_min5(self):
        """Small delta at iteration 5 SHOULD stop when min_iterations=5."""
        config = RalphLoopConfig(
            max_iterations=10,
            min_iterations=5,
            min_acceptable_score=0.99,  # Unreachable
            min_score_delta=0.05,
            run_id="test-plateau-stop",
        )
        engine = RalphLoopEngine(config)

        engine.record_iteration({"id": "c1"}, weighted_total=0.40)
        self.assertFalse(engine.should_stop())
        engine.record_iteration({"id": "c2"}, weighted_total=0.50)
        self.assertFalse(engine.should_stop())
        engine.record_iteration({"id": "c3"}, weighted_total=0.60)
        self.assertFalse(engine.should_stop())
        engine.record_iteration({"id": "c4"}, weighted_total=0.65)
        self.assertFalse(engine.should_stop())

        # Iteration 5: small delta, min_iterations met → plateau
        engine.record_iteration({"id": "c5"}, weighted_total=0.66)
        self.assertTrue(engine.should_stop())
        self.assertEqual(engine.state.stop_reason, "plateau_detected")


class TestRalphLoopPriorityOrder(unittest.TestCase):
    """Scenario 4: Threshold wins over plateau when both trigger."""

    def test_threshold_wins_over_plateau(self):
        """score>=0.70 AND delta<0.05 at iteration 3 → threshold_met wins."""
        config = RalphLoopConfig(
            max_iterations=7,
            min_iterations=3,
            min_acceptable_score=0.70,
            min_score_delta=0.05,
            run_id="test-priority",
        )
        engine = RalphLoopEngine(config)

        engine.record_iteration({"id": "c1"}, weighted_total=0.68)
        self.assertFalse(engine.should_stop())
        engine.record_iteration({"id": "c2"}, weighted_total=0.69)
        self.assertFalse(engine.should_stop())

        # Iteration 3: score 0.70 (threshold met) AND delta 0.01 (plateau)
        engine.record_iteration({"id": "c3"}, weighted_total=0.70)
        self.assertTrue(engine.should_stop())
        self.assertEqual(engine.state.stop_reason, "threshold_met")


# ---------------------------------------------------------------------------
# Completion Gates tests
# ---------------------------------------------------------------------------


class TestCompletionGates(unittest.TestCase):
    """Validate completion_gates.yaml contract per tier."""

    @classmethod
    def setUpClass(cls):
        gates_path = ROOT / "configs" / "orchestrator" / "completion_gates.yaml"
        with open(gates_path) as f:
            cls.gates = yaml.safe_load(f)["completion_gates"]

    def test_c1_no_blocking_gates(self):
        c1 = self.gates["C1"]
        self.assertFalse(c1.get("require_tests", False))
        self.assertFalse(c1.get("require_retro", False))
        self.assertFalse(c1.get("require_review", False))
        self.assertNotIn("block_completion_until", c1)

    def test_c3_retro_required(self):
        c3 = self.gates["C3"]
        self.assertTrue(c3["require_retro"])
        self.assertEqual(c3["block_completion_until"], "retro_written")

    def test_c4_pattern_extraction_required(self):
        c4 = self.gates["C4"]
        self.assertTrue(c4["require_pattern_extraction"])
        self.assertTrue(c4["harness"]["isolated_worktree_expected"])
        self.assertTrue(c4["harness"]["validation_evidence_required"])
        self.assertTrue(c4["harness"]["review_evidence_required"])
        self.assertIn("pattern_extracted", c4["block_completion_until"])
        self.assertIn("validation_evidence_collected", c4["block_completion_until"])

    def test_c5_council_review_required(self):
        c5 = self.gates["C5"]
        self.assertTrue(c5["require_council_review"])
        self.assertTrue(c5["harness"]["isolated_worktree_expected"])
        self.assertTrue(c5["harness"]["validation_evidence_required"])
        self.assertTrue(c5["harness"]["review_evidence_required"])
        self.assertTrue(c5["harness"]["audit_evidence_required"])
        self.assertEqual(c5["block_completion_until"], "all_gates_passed")


if __name__ == "__main__":
    unittest.main()
