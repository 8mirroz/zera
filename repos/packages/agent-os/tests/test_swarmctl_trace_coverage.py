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
from agent_os.tool_runner import ToolRunner


class TestSwarmctlTraceCoverage(unittest.TestCase):
    """Test runtime trace coverage with tool_call and verification_result events."""

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

    def test_tool_runner_emits_tool_call_on_success(self) -> None:
        runner = ToolRunner()
        tool_input = ToolInput(tool_name="echo", args=["test"], mode="read", correlation_id="run-123")
        output = runner.run(tool_input)

        self.assertEqual(output.status, "ok")
        events = self._read_trace_events()
        tool_events = [e for e in events if e.get("event_type") == "tool_call"]
        self.assertEqual(len(tool_events), 1)
        
        event = tool_events[0]
        self.assertEqual(event["run_id"], "run-123")
        self.assertEqual(event["tool_name"], "echo")
        self.assertEqual(event["status"], "ok")
        self.assertIn("duration_ms", event)
        self.assertIsInstance(event["duration_ms"], int)
        self.assertGreaterEqual(event["duration_ms"], 0)

    def test_tool_runner_emits_tool_call_on_error(self) -> None:
        runner = ToolRunner()
        tool_input = ToolInput(tool_name="sh", args=["-c", "exit 1"], mode="write", correlation_id="run-456")
        output = runner.run(tool_input)

        self.assertEqual(output.status, "error")
        events = self._read_trace_events()
        tool_events = [e for e in events if e.get("event_type") == "tool_call"]
        self.assertEqual(len(tool_events), 1)
        
        event = tool_events[0]
        self.assertEqual(event["run_id"], "run-456")
        self.assertEqual(event["status"], "error")
        self.assertIn("exit_code", event["data"])

    def test_agent_runtime_emits_verification_result(self) -> None:
        runtime = AgentRuntime()
        agent_input = AgentInput(
            run_id="run-789",
            objective="test objective",
            plan_steps=["route", "execute"],
            route_decision={"primary_model": "test-model"},
        )
        output = runtime.run(agent_input)

        self.assertEqual(output.status, "completed")
        events = self._read_trace_events()
        
        verification_events = [e for e in events if e.get("event_type") == "verification_result"]
        self.assertEqual(len(verification_events), 1)
        
        event = verification_events[0]
        self.assertEqual(event["run_id"], "run-789")
        self.assertEqual(event["status"], "ok")
        self.assertEqual(event["data"]["verification_status"], "not-run")
        self.assertIn("reason", event["data"])

    def test_agent_runtime_emits_complete_event_sequence(self) -> None:
        runtime = AgentRuntime()
        agent_input = AgentInput(
            run_id="run-complete",
            objective="test full sequence",
            plan_steps=["route", "execute", "verify"],
            route_decision={"primary_model": "test-model", "model_tier": "C2"},
        )
        runtime.run(agent_input)

        events = self._read_trace_events()
        event_types = [e.get("event_type") for e in events]
        
        self.assertIn("agent_run_started", event_types)
        self.assertIn("verification_result", event_types)
        self.assertIn("agent_run_completed", event_types)
        
        # Verify all events share the same run_id
        run_ids = {e.get("run_id") for e in events}
        self.assertEqual(run_ids, {"run-complete"})

    def test_agent_run_completed_includes_duration_ms(self) -> None:
        runtime = AgentRuntime()
        agent_input = AgentInput(
            run_id="run-duration",
            objective="test duration",
            plan_steps=["execute"],
            route_decision={},
        )
        runtime.run(agent_input)

        events = self._read_trace_events()
        completed_events = [e for e in events if e.get("event_type") == "agent_run_completed"]
        self.assertEqual(len(completed_events), 1)
        
        event = completed_events[0]
        self.assertIn("duration_ms", event)
        self.assertIsInstance(event["duration_ms"], int)
        self.assertGreaterEqual(event["duration_ms"], 0)

    def test_task_run_summary_includes_tool_and_verification_fields(self) -> None:
        # This test validates the contract shape for task_run_summary
        # In real swarmctl run, these fields would be populated
        expected_fields = {
            "tool_calls_total",
            "tool_calls_success",
            "verification_status",
        }
        
        # Simulate a task_run_summary event structure
        from agent_os.observability import emit_event
        
        emit_event(
            "task_run_summary",
            {
                "run_id": "run-summary-test",
                "component": "agent",
                "status": "completed",
                "task_type": "T2",
                "complexity": "C2",
                "message": "test summary",
                "data": {
                    "tool_calls_total": 3,
                    "tool_calls_success": 2,
                    "verification_status": "not-run",
                },
            },
        )
        
        events = self._read_trace_events()
        summary_events = [e for e in events if e.get("event_type") == "task_run_summary"]
        self.assertEqual(len(summary_events), 1)
        
        event = summary_events[0]
        data = event.get("data", {})
        for field in expected_fields:
            self.assertIn(field, data, f"Missing field: {field}")


if __name__ == "__main__":
    unittest.main()
