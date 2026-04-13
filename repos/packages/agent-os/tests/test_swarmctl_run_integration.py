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

from agent_os.agent_runtime import AgentRuntime
from agent_os.contracts import AgentInput, ToolInput
from agent_os.memory_store import MemoryStore
from agent_os.retriever import Retriever
from agent_os.tool_runner import ToolRunner
from agent_os.observability import emit_event


class TestSwarmctlRunIntegration(unittest.TestCase):
    """Integration test for swarmctl run with complete trace event sequence."""

    def setUp(self) -> None:
        self.trace_fd, self.trace_path = tempfile.mkstemp(suffix=".jsonl")
        os.environ["AGENT_OS_TRACE_FILE"] = self.trace_path

    def tearDown(self) -> None:
        os.close(self.trace_fd)
        Path(self.trace_path).unlink(missing_ok=True)
        if "AGENT_OS_TRACE_FILE" in os.environ:
            del os.environ["AGENT_OS_TRACE_FILE"]

    def _read_trace_events(self) -> list[dict]:
        with open(self.trace_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def test_swarmctl_run_emits_minimum_5_linked_events(self) -> None:
        """Test that swarmctl run flow emits at least 5 linked v2 events with same run_id."""
        run_id = "integration-run-001"
        
        # Simulate swarmctl run flow
        # 1. route_decision
        emit_event(
            "route_decision",
            {
                "run_id": run_id,
                "component": "router",
                "status": "ok",
                "task_type": "T2",
                "complexity": "C2",
                "model_tier": "quality",
                "model": "test-model",
                "message": "Route decision completed",
                "data": {"primary_model": "test-model"},
            },
        )
        
        # 2. agent_run_started + verification_result + agent_run_completed (via AgentRuntime)
        runtime = AgentRuntime()
        agent_input = AgentInput(
            run_id=run_id,
            objective="Fix bug in authentication",
            plan_steps=["route", "execute", "verify", "report"],
            route_decision={"primary_model": "test-model", "model_tier": "quality"},
        )
        output = runtime.run(agent_input)
        
        # 3. tool_call (simulate tool execution)
        runner = ToolRunner()
        tool_input = ToolInput(tool_name="echo", args=["test"], mode="read", correlation_id=run_id)
        runner.run(tool_input)
        
        # 4. task_run_summary
        emit_event(
            "task_run_summary",
            {
                "run_id": run_id,
                "component": "agent",
                "status": "completed",
                "task_type": "T2",
                "complexity": "C2",
                "model_tier": "quality",
                "model": "test-model",
                "message": "swarmctl run completed",
                "data": {
                    "tool_calls_total": 1,
                    "tool_calls_success": 1,
                    "verification_status": "not-run",
                },
            },
        )
        
        # Verify trace events
        events = self._read_trace_events()
        
        # Filter events by run_id
        run_events = [e for e in events if e.get("run_id") == run_id]
        
        # Check minimum 5 events
        self.assertGreaterEqual(len(run_events), 5, f"Expected at least 5 events, got {len(run_events)}")
        
        # Verify required event types
        event_types = {e.get("event_type") for e in run_events}
        required_types = {
            "route_decision",
            "agent_run_started",
            "tool_call",
            "verification_result",
            "task_run_summary",
            "agent_run_completed",
        }
        
        missing_types = required_types - event_types
        self.assertEqual(
            len(missing_types),
            0,
            f"Missing required event types: {missing_types}. Found: {event_types}",
        )
        
        # Verify all events share the same run_id
        run_ids = {e.get("run_id") for e in run_events}
        self.assertEqual(run_ids, {run_id}, "All events must share the same run_id")
        
        # Verify event sequence order (approximate)
        event_type_list = [e.get("event_type") for e in run_events]
        route_idx = event_type_list.index("route_decision")
        started_idx = event_type_list.index("agent_run_started")
        completed_idx = event_type_list.index("agent_run_completed")
        summary_idx = event_type_list.index("task_run_summary")
        
        self.assertLess(route_idx, started_idx, "route_decision should come before agent_run_started")
        self.assertLess(started_idx, completed_idx, "agent_run_started should come before agent_run_completed")
        self.assertLess(completed_idx, summary_idx, "agent_run_completed should come before task_run_summary")

    def test_trace_events_have_v2_schema_fields(self) -> None:
        """Verify all emitted events conform to Trace Event v2 schema."""
        run_id = "schema-validation-run"
        
        runtime = AgentRuntime()
        agent_input = AgentInput(
            run_id=run_id,
            objective="test schema",
            plan_steps=["execute"],
            route_decision={},
        )
        runtime.run(agent_input)
        
        events = self._read_trace_events()
        run_events = [e for e in events if e.get("run_id") == run_id]
        
        # Verify v2 schema required fields
        required_fields = {"ts", "run_id", "event_type", "level", "component", "data"}
        
        for event in run_events:
            for field in required_fields:
                self.assertIn(field, event, f"Event {event.get('event_type')} missing required field: {field}")
            
            # Verify data is a dict
            self.assertIsInstance(event["data"], dict, f"Event {event.get('event_type')} data must be dict")
            
            # Verify level is valid
            self.assertIn(event["level"], {"debug", "info", "warn", "error"}, f"Invalid level: {event['level']}")

    def test_tool_call_events_include_duration_and_status(self) -> None:
        """Verify tool_call events include duration_ms and status fields."""
        run_id = "tool-metrics-run"
        
        runner = ToolRunner()
        
        # Success case
        tool_input = ToolInput(tool_name="echo", args=["success"], mode="read", correlation_id=run_id)
        runner.run(tool_input)
        
        # Error case
        tool_input_err = ToolInput(tool_name="sh", args=["-c", "exit 1"], mode="write", correlation_id=run_id)
        runner.run(tool_input_err)
        
        events = self._read_trace_events()
        tool_events = [e for e in events if e.get("event_type") == "tool_call" and e.get("run_id") == run_id]
        
        self.assertEqual(len(tool_events), 2, "Expected 2 tool_call events")
        
        for event in tool_events:
            self.assertIn("duration_ms", event, "tool_call must include duration_ms")
            self.assertIsInstance(event["duration_ms"], int)
            self.assertGreaterEqual(event["duration_ms"], 0)
            self.assertIn("status", event)
            self.assertIn(event["status"], {"ok", "error"})
            self.assertIn("tool_name", event)

    def test_verification_result_includes_status_and_reason(self) -> None:
        """Verify verification_result event includes status and reason in data."""
        run_id = "verification-test-run"
        
        runtime = AgentRuntime()
        agent_input = AgentInput(
            run_id=run_id,
            objective="test verification",
            plan_steps=["verify"],
            route_decision={},
        )
        runtime.run(agent_input)
        
        events = self._read_trace_events()
        verification_events = [e for e in events if e.get("event_type") == "verification_result" and e.get("run_id") == run_id]
        
        self.assertEqual(len(verification_events), 1, "Expected 1 verification_result event")
        
        event = verification_events[0]
        self.assertEqual(event["status"], "warn")
        self.assertIn("verification_status", event["data"])
        self.assertIn("reason", event["data"])


if __name__ == "__main__":
    unittest.main()
