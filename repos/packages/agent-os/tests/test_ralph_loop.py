"""
Tests for Ralph Loop Engine.

Covers:
- Plateau stop condition
- Threshold stop after min_iterations
- Max iterations stop
- Best candidate selection
- Trace Event v2 compatibility
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.ralph_loop import (
    RalphEvent,
    RalphLoopConfig,
    RalphLoopDecision,
    RalphLoopEngine,
    _compute_weighted_score,
)


class TestWeightedScore(unittest.TestCase):
    """Test weighted score computation."""

    def test_weighted_score_computes_correctly(self) -> None:
        weights = {
            "correctness": 0.35,
            "speed": 0.20,
            "code_quality": 0.20,
            "token_efficiency": 0.15,
            "tool_success_rate": 0.10,
        }
        metrics = {
            "correctness": 1.0,
            "speed": 0.5,
            "code_quality": 0.8,
            "token_efficiency": 0.6,
            "tool_success_rate": 1.0,
        }
        # Expected: 1.0*0.35 + 0.5*0.20 + 0.8*0.20 + 0.6*0.15 + 1.0*0.10
        #         = 0.35 + 0.10 + 0.16 + 0.09 + 0.10 = 0.80
        result = _compute_weighted_score(metrics, weights)
        self.assertEqual(result, 0.80)

    def test_weighted_score_handles_missing_metrics(self) -> None:
        weights = {"correctness": 0.5, "speed": 0.5}
        metrics = {"correctness": 1.0}  # speed missing
        result = _compute_weighted_score(metrics, weights)
        # Expected: 1.0*0.5 + 0.0*0.5 = 0.5
        self.assertEqual(result, 0.50)


class TestRalphLoopConfig(unittest.TestCase):
    """Test configuration defaults."""

    def test_default_config_values(self) -> None:
        config = RalphLoopConfig()
        self.assertEqual(config.max_iterations, 7)
        self.assertEqual(config.min_iterations, 3)
        self.assertEqual(config.min_acceptable_score, 0.70)
        self.assertEqual(config.min_score_delta, 0.05)
        self.assertTrue(config.run_id)  # UUID generated


class TestRalphLoopEngine(unittest.TestCase):
    """Test Ralph Loop Engine core functionality."""

    def setUp(self) -> None:
        self.config = RalphLoopConfig(
            max_iterations=7,
            min_iterations=3,
            min_acceptable_score=0.70,
            min_score_delta=0.05,
            run_id="test-run-001",
            task_type="T3",
            complexity="C3",
        )
        self.engine = RalphLoopEngine(self.config)

    def test_single_iteration_records_events(self) -> None:
        """Test that a single iteration produces correct events."""
        candidate = {"id": "cand-1", "code": "print('hello')"}
        metrics = {
            "correctness": 0.8,
            "speed": 0.7,
            "code_quality": 0.9,
            "token_efficiency": 0.6,
            "tool_success_rate": 1.0,
        }

        events = self.engine.record_iteration(candidate, metrics)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, "ralph_iteration_started")
        self.assertEqual(events[1].event_type, "ralph_iteration_scored")

        # Check scored event data
        scored_data = events[1].data
        self.assertEqual(scored_data["iteration"], 1)
        self.assertEqual(scored_data["candidate_id"], "cand-1")
        self.assertIn("weighted_total", scored_data)
        self.assertTrue(scored_data["is_new_best"])

    def test_plateau_stop_condition(self) -> None:
        """Test stop when score improvement is below delta."""
        # Use config where threshold is NOT met (so plateau is the trigger)
        config = RalphLoopConfig(
            max_iterations=7,
            min_iterations=3,
            min_acceptable_score=0.90,  # High threshold (not reached)
            min_score_delta=0.05,
            run_id="test-plateau",
        )
        engine = RalphLoopEngine(config)

        # Iteration 1: score 0.75
        engine.record_iteration({"id": "c1"}, weighted_total=0.75)
        self.assertFalse(engine.should_stop())  # min_iterations not met

        # Iteration 2: score 0.76 (delta = 0.01 < 0.05)
        engine.record_iteration({"id": "c2"}, weighted_total=0.76)
        self.assertFalse(engine.should_stop())  # min_iterations not met

        # Iteration 3: score 0.765 (delta = 0.005 < 0.05, min_iterations met)
        engine.record_iteration({"id": "c3"}, weighted_total=0.765)
        should_stop = engine.should_stop()
        self.assertTrue(should_stop)
        self.assertEqual(engine.state.stop_reason, "plateau_detected")

    def test_threshold_stop_after_min_iterations(self) -> None:
        """Test stop when score exceeds threshold after min_iterations."""
        # Iteration 1: score 0.50 (below threshold)
        self.engine.record_iteration({"id": "c1"}, weighted_total=0.50)
        self.assertFalse(self.engine.should_stop())

        # Iteration 2: score 0.60 (below threshold)
        self.engine.record_iteration({"id": "c2"}, weighted_total=0.60)
        self.assertFalse(self.engine.should_stop())

        # Iteration 3: score 0.85 (above threshold, min_iterations met)
        self.engine.record_iteration({"id": "c3"}, weighted_total=0.85)
        should_stop = self.engine.should_stop()
        self.assertTrue(should_stop)
        self.assertEqual(self.engine.state.stop_reason, "threshold_met")

    def test_max_iterations_stop(self) -> None:
        """Test stop when max_iterations is reached."""
        config = RalphLoopConfig(
            max_iterations=3,
            min_iterations=1,
            min_acceptable_score=0.99,  # Unreachable
            min_score_delta=0.001,
            run_id="test-run-002",
        )
        engine = RalphLoopEngine(config)

        # Iterations 1-2: continue
        engine.record_iteration({"id": "c1"}, weighted_total=0.50)
        self.assertFalse(engine.should_stop())

        engine.record_iteration({"id": "c2"}, weighted_total=0.55)
        self.assertFalse(engine.should_stop())

        # Iteration 3: max reached
        engine.record_iteration({"id": "c3"}, weighted_total=0.60)
        should_stop = engine.should_stop()
        self.assertTrue(should_stop)
        self.assertEqual(engine.state.stop_reason, "max_iterations_reached")

    def test_best_candidate_selection(self) -> None:
        """Test that best candidate is correctly selected."""
        config = RalphLoopConfig(
            max_iterations=10,
            min_iterations=1,
            min_acceptable_score=0.99,  # High threshold to avoid early stop
            min_score_delta=0.001,  # Small delta to avoid plateau
        )
        engine = RalphLoopEngine(config)

        scores = [0.65, 0.80, 0.72, 0.85, 0.78]
        for i, score in enumerate(scores):
            engine.record_iteration(
                {"id": f"c{i+1}", "value": i},
                weighted_total=score,
            )

        decision = engine.finalize()

        self.assertTrue(decision.selected)
        self.assertEqual(decision.best_score, 0.85)
        self.assertEqual(decision.total_iterations, 5)
        self.assertIsNotNone(decision.best_candidate)
        self.assertEqual(decision.best_candidate["id"], "c4")  # Best at index 3

    def test_all_scores_and_improvement_history(self) -> None:
        """Test that all_scores and improvement_history are tracked."""
        config = RalphLoopConfig(
            max_iterations=10,
            min_iterations=1,
            min_acceptable_score=0.99,  # High threshold to avoid early stop
            min_score_delta=0.001,  # Small delta to avoid plateau
        )
        engine = RalphLoopEngine(config)

        scores = [0.60, 0.75, 0.70, 0.85, 0.82]
        for score in scores:
            engine.record_iteration({"id": "cx"}, weighted_total=score)

        # Don't call should_stop() during iterations - finalize directly
        decision = engine.finalize()

        self.assertEqual(decision.all_scores, scores)
        # Improvement history tracks running max
        expected_history = [0.60, 0.75, 0.75, 0.85, 0.85]
        self.assertEqual(decision.improvement_history, expected_history)

    def test_finalize_emits_best_selected_event(self) -> None:
        """Test that finalize emits ralph_best_selected event."""
        self.engine.record_iteration({"id": "best"}, weighted_total=0.90)
        self.engine.should_stop()

        events_before = len(self.engine.get_events())
        decision = self.engine.finalize()
        events_after = len(self.engine.get_events())

        self.assertTrue(decision.selected)
        self.assertEqual(events_after - events_before, 1)  # best_selected event

        best_event = self.engine.get_events()[-1]
        self.assertEqual(best_event.event_type, "ralph_best_selected")
        self.assertEqual(best_event.data["best_score"], 0.90)

    def test_cannot_record_after_stop(self) -> None:
        """Test that recording iteration after stop raises error."""
        self.engine.record_iteration({"id": "c1"}, weighted_total=0.80)
        self.engine.state.stopped = True
        self.engine.state.stop_reason = "test_stop"

        with self.assertRaises(RuntimeError):
            self.engine.record_iteration({"id": "c2"}, weighted_total=0.85)


class TestTraceEventV2Compatibility(unittest.TestCase):
    """Test that events are Trace Event v2 compatible."""

    def test_event_has_required_fields(self) -> None:
        """Test event structure matches Trace Event v2 envelope."""
        config = RalphLoopConfig(run_id="trace-test-001")
        engine = RalphLoopEngine(config)
        engine.record_iteration({"id": "test"}, weighted_total=0.75)

        events = engine.pop_events()
        for event in events:
            event_dict = event.to_dict()

            # Required top-level fields
            self.assertIn("ts", event_dict)
            self.assertIn("run_id", event_dict)
            self.assertIn("event_type", event_dict)
            self.assertIn("level", event_dict)
            self.assertIn("component", event_dict)
            self.assertIn("status", event_dict)
            self.assertIn("data", event_dict)

            # Type checks
            self.assertIsInstance(event_dict["ts"], str)
            self.assertEqual(event_dict["component"], "ralph")
            self.assertEqual(event_dict["run_id"], "trace-test-001")

    def test_ralph_iteration_scored_event_structure(self) -> None:
        """Test ralph_iteration_scored event matches expected schema."""
        config = RalphLoopConfig(run_id="schema-test", task_type="T4", complexity="C4")
        engine = RalphLoopEngine(config)

        metrics = {
            "correctness": 0.9,
            "speed": 0.8,
            "code_quality": 0.85,
            "token_efficiency": 0.7,
            "tool_success_rate": 1.0,
        }
        engine.record_iteration({"id": "cand-xyz", "name": "Test Candidate"}, metrics)

        events = engine.pop_events()
        scored_event = events[1]  # Second event is scored
        event_dict = scored_event.to_dict()

        self.assertEqual(event_dict["event_type"], "ralph_iteration_scored")
        self.assertEqual(event_dict["task_type"], "T4")
        self.assertEqual(event_dict["complexity"], "C4")
        self.assertEqual(event_dict["component"], "ralph")
        self.assertEqual(event_dict["status"], "ok")

        data = event_dict["data"]
        self.assertIn("iteration", data)
        self.assertIn("candidate_id", data)
        self.assertIn("weighted_total", data)
        self.assertIn("metrics", data)
        self.assertIn("is_new_best", data)
        self.assertIn("ralph_loop", data)

        # Check ralph_loop structure (legacy compatibility)
        ralph_loop = data["ralph_loop"]
        self.assertIn("enabled", ralph_loop)
        self.assertIn("iteration", ralph_loop)
        self.assertIn("total_iterations", ralph_loop)
        self.assertIn("score", ralph_loop)
        self.assertIn("selected_as_best", ralph_loop)

    def test_ralph_stop_decision_event_structure(self) -> None:
        """Test ralph_stop_decision event structure."""
        config = RalphLoopConfig(
            max_iterations=1,
            min_iterations=1,
            run_id="stop-test",
        )
        engine = RalphLoopEngine(config)
        engine.record_iteration({"id": "c1"}, weighted_total=0.50)
        engine.should_stop()

        events = engine.pop_events()
        stop_event = events[-1]
        event_dict = stop_event.to_dict()

        self.assertEqual(event_dict["event_type"], "ralph_stop_decision")
        self.assertIn("stop_reason", event_dict["data"])
        self.assertIn("total_iterations", event_dict["data"])
        self.assertIn("best_score", event_dict["data"])

    def test_ralph_best_selected_event_structure(self) -> None:
        """Test ralph_best_selected event structure."""
        config = RalphLoopConfig(run_id="best-test")
        engine = RalphLoopEngine(config)
        engine.record_iteration({"id": "winner", "name": "Champion"}, weighted_total=0.92)
        engine.should_stop()
        engine.finalize()

        events = engine.pop_events()
        best_event = events[-1]
        event_dict = best_event.to_dict()

        self.assertEqual(event_dict["event_type"], "ralph_best_selected")
        self.assertEqual(event_dict["component"], "ralph")

        data = event_dict["data"]
        self.assertIn("best_iteration", data)
        self.assertIn("candidate_id", data)
        self.assertEqual(data["candidate_id"], "winner")
        self.assertEqual(data["best_score"], 0.92)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_zero_iterations(self) -> None:
        """Test finalize with no iterations."""
        engine = RalphLoopEngine(RalphLoopConfig())
        decision = engine.finalize()

        self.assertFalse(decision.selected)
        self.assertIsNone(decision.best_candidate)
        self.assertEqual(decision.best_score, 0.0)
        self.assertEqual(decision.total_iterations, 0)

    def test_single_candidate(self) -> None:
        """Test with only one candidate."""
        config = RalphLoopConfig(max_iterations=1, min_iterations=1)
        engine = RalphLoopEngine(config)
        engine.record_iteration({"id": "only"}, weighted_total=0.60)
        engine.should_stop()
        decision = engine.finalize()

        self.assertTrue(decision.selected)
        self.assertEqual(decision.best_candidate["id"], "only")
        self.assertEqual(decision.best_score, 0.60)

    def test_all_scores_zero(self) -> None:
        """Test when all scores are zero."""
        config = RalphLoopConfig(
            max_iterations=3,
            min_iterations=1,
            min_acceptable_score=0.99,  # High threshold
            min_score_delta=0.0,  # Disable plateau detection for this test
        )
        engine = RalphLoopEngine(config)

        for i in range(3):
            engine.record_iteration({"id": f"c{i}"}, weighted_total=0.0)

        # Should stop at max_iterations
        self.assertTrue(engine.should_stop())
        self.assertEqual(engine.state.stop_reason, "max_iterations_reached")

        decision = engine.finalize()
        self.assertTrue(decision.selected)
        self.assertEqual(decision.best_score, 0.0)
        self.assertEqual(decision.all_scores, [0.0, 0.0, 0.0])

    def test_perfect_score(self) -> None:
        """Test with perfect score (1.0)."""
        config = RalphLoopConfig(
            max_iterations=7,
            min_iterations=1,  # Allow stop after 1 iteration
            min_acceptable_score=0.70,
        )
        engine = RalphLoopEngine(config)
        engine.record_iteration({"id": "perfect"}, weighted_total=1.0)
        should_stop = engine.should_stop()

        self.assertTrue(should_stop)
        self.assertEqual(engine.state.stop_reason, "threshold_met")

        decision = engine.finalize()
        self.assertEqual(decision.best_score, 1.0)


if __name__ == "__main__":
    unittest.main()
