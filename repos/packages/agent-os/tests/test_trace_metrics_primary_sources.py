from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from trace_metrics_materializer import materialize_metrics


class TestTraceMetricsPrimarySources(unittest.TestCase):
    """Test that metrics materializer uses primary event sources instead of fallback."""

    def setUp(self) -> None:
        self.trace_fd, self.trace_path = tempfile.mkstemp(suffix=".jsonl")

    def tearDown(self) -> None:
        os.close(self.trace_fd)
        Path(self.trace_path).unlink(missing_ok=True)

    def _write_trace_events(self, events: list[dict]) -> None:
        with open(self.trace_path, "w", encoding="utf-8") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

    def test_pass_rate_uses_verification_result_as_primary_source(self) -> None:
        """Test that pass_rate KPI uses verification_result events as primary source."""
        events = [
            {
                "ts": "2024-01-01T00:00:00+00:00",
                "run_id": "run-1",
                "event_type": "verification_result",
                "level": "info",
                "component": "verifier",
                "status": "ok",
                "data": {"verification_status": "pass"},
            },
            {
                "ts": "2024-01-01T00:01:00+00:00",
                "run_id": "run-2",
                "event_type": "verification_result",
                "level": "info",
                "component": "verifier",
                "status": "ok",
                "data": {"verification_status": "pass"},
            },
            {
                "ts": "2024-01-01T00:02:00+00:00",
                "run_id": "run-3",
                "event_type": "verification_result",
                "level": "info",
                "component": "verifier",
                "status": "error",
                "data": {"verification_status": "fail"},
            },
        ]
        
        self._write_trace_events(events)
        result = materialize_metrics(Path(self.trace_path), allow_legacy=False, include_dimensions=False)
        
        self.assertEqual(result["status"], "ok")
        pass_rate = result["kpis"]["pass_rate"]
        
        # Verify primary source is used
        self.assertEqual(pass_rate["source"], "verification_result")
        self.assertEqual(pass_rate["numerator"], 2)
        self.assertEqual(pass_rate["denominator"], 3)
        self.assertAlmostEqual(pass_rate["value"], 0.6667, places=3)

    def test_tool_success_rate_uses_tool_call_as_primary_source(self) -> None:
        """Test that tool_success_rate KPI uses tool_call events as primary source."""
        events = [
            {
                "ts": "2024-01-01T00:00:00+00:00",
                "run_id": "run-1",
                "event_type": "tool_call",
                "level": "info",
                "component": "tool",
                "tool_name": "echo",
                "status": "ok",
                "duration_ms": 10,
                "data": {},
            },
            {
                "ts": "2024-01-01T00:01:00+00:00",
                "run_id": "run-1",
                "event_type": "tool_call",
                "level": "info",
                "component": "tool",
                "tool_name": "grep",
                "status": "ok",
                "duration_ms": 20,
                "data": {},
            },
            {
                "ts": "2024-01-01T00:02:00+00:00",
                "run_id": "run-2",
                "event_type": "tool_call",
                "level": "info",
                "component": "tool",
                "tool_name": "sed",
                "status": "error",
                "duration_ms": 5,
                "data": {},
            },
        ]
        
        self._write_trace_events(events)
        result = materialize_metrics(Path(self.trace_path), allow_legacy=False, include_dimensions=False)
        
        self.assertEqual(result["status"], "ok")
        tool_rate = result["kpis"]["tool_success_rate"]
        
        # Verify primary source is used
        self.assertEqual(tool_rate["source"], "tool_call")
        self.assertEqual(tool_rate["numerator"], 2)
        self.assertEqual(tool_rate["denominator"], 3)
        self.assertAlmostEqual(tool_rate["value"], 0.6667, places=3)

    def test_fallback_used_when_primary_events_missing(self) -> None:
        """Test that fallback sources are used when primary events are not available."""
        events = [
            {
                "ts": "2024-01-01T00:00:00+00:00",
                "run_id": "run-1",
                "event_type": "task_run_summary",
                "level": "info",
                "component": "agent",
                "status": "completed",
                "data": {
                    "tool_calls_total": 5,
                    "tool_calls_success": 4,
                },
            },
        ]
        
        self._write_trace_events(events)
        result = materialize_metrics(Path(self.trace_path), allow_legacy=False, include_dimensions=False)
        
        self.assertEqual(result["status"], "ok")
        
        # pass_rate should use task_run_summary fallback
        pass_rate = result["kpis"]["pass_rate"]
        self.assertEqual(pass_rate["source"], "task_run_summary_fallback")
        
        # tool_success_rate should use task_run_summary fallback
        tool_rate = result["kpis"]["tool_success_rate"]
        self.assertEqual(tool_rate["source"], "task_run_summary_fallback")
        self.assertEqual(tool_rate["numerator"], 4)
        self.assertEqual(tool_rate["denominator"], 5)

    def test_primary_sources_preferred_over_fallback(self) -> None:
        """Test that primary sources are preferred even when fallback data exists."""
        events = [
            # Primary verification_result events
            {
                "ts": "2024-01-01T00:00:00+00:00",
                "run_id": "run-1",
                "event_type": "verification_result",
                "level": "info",
                "component": "verifier",
                "status": "ok",
                "data": {},
            },
            # Primary tool_call events
            {
                "ts": "2024-01-01T00:01:00+00:00",
                "run_id": "run-1",
                "event_type": "tool_call",
                "level": "info",
                "component": "tool",
                "tool_name": "test",
                "status": "ok",
                "duration_ms": 10,
                "data": {},
            },
            # Fallback task_run_summary with different counts
            {
                "ts": "2024-01-01T00:02:00+00:00",
                "run_id": "run-1",
                "event_type": "task_run_summary",
                "level": "info",
                "component": "agent",
                "status": "completed",
                "data": {
                    "tool_calls_total": 100,  # Should be ignored
                    "tool_calls_success": 50,  # Should be ignored
                },
            },
        ]
        
        self._write_trace_events(events)
        result = materialize_metrics(Path(self.trace_path), allow_legacy=False, include_dimensions=False)
        
        self.assertEqual(result["status"], "ok")
        
        # Verify primary sources are used
        pass_rate = result["kpis"]["pass_rate"]
        self.assertEqual(pass_rate["source"], "verification_result")
        self.assertEqual(pass_rate["denominator"], 1)  # From verification_result, not task_run_summary
        
        tool_rate = result["kpis"]["tool_success_rate"]
        self.assertEqual(tool_rate["source"], "tool_call")
        self.assertEqual(tool_rate["denominator"], 1)  # From tool_call, not task_run_summary

    def test_complete_run_with_all_primary_events(self) -> None:
        """Test a complete run with all primary event types."""
        run_id = "complete-run-001"
        events = [
            {
                "ts": "2024-01-01T00:00:00+00:00",
                "run_id": run_id,
                "event_type": "route_decision",
                "level": "info",
                "component": "router",
                "status": "ok",
                "task_type": "T2",
                "complexity": "C2",
                "data": {},
            },
            {
                "ts": "2024-01-01T00:00:01+00:00",
                "run_id": run_id,
                "event_type": "agent_run_started",
                "level": "info",
                "component": "agent",
                "status": "ok",
                "data": {},
            },
            {
                "ts": "2024-01-01T00:00:02+00:00",
                "run_id": run_id,
                "event_type": "tool_call",
                "level": "info",
                "component": "tool",
                "tool_name": "echo",
                "status": "ok",
                "duration_ms": 10,
                "data": {},
            },
            {
                "ts": "2024-01-01T00:00:03+00:00",
                "run_id": run_id,
                "event_type": "verification_result",
                "level": "info",
                "component": "verifier",
                "status": "ok",
                "data": {"verification_status": "not-run"},
            },
            {
                "ts": "2024-01-01T00:00:04+00:00",
                "run_id": run_id,
                "event_type": "agent_run_completed",
                "level": "info",
                "component": "agent",
                "status": "completed",
                "duration_ms": 4000,
                "data": {},
            },
            {
                "ts": "2024-01-01T00:00:05+00:00",
                "run_id": run_id,
                "event_type": "task_run_summary",
                "level": "info",
                "component": "agent",
                "status": "completed",
                "task_type": "T2",
                "complexity": "C2",
                "data": {
                    "tool_calls_total": 1,
                    "tool_calls_success": 1,
                    "verification_status": "not-run",
                },
            },
        ]
        
        self._write_trace_events(events)
        result = materialize_metrics(Path(self.trace_path), allow_legacy=False, include_dimensions=False)
        
        self.assertEqual(result["status"], "ok")
        
        # Verify all event types are counted
        event_counts = result["event_counts"]
        self.assertEqual(event_counts["route_decision"], 1)
        self.assertEqual(event_counts["agent_run_started"], 1)
        self.assertEqual(event_counts["tool_call"], 1)
        self.assertEqual(event_counts["verification_result"], 1)
        self.assertEqual(event_counts["agent_run_completed"], 1)
        self.assertEqual(event_counts["task_run_summary"], 1)
        
        # Verify primary sources are used
        self.assertEqual(result["kpis"]["pass_rate"]["source"], "verification_result")
        self.assertEqual(result["kpis"]["tool_success_rate"]["source"], "tool_call")


if __name__ == "__main__":
    unittest.main()
