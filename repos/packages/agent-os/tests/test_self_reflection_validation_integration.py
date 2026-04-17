from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.agent_runtime import AgentRuntime
from agent_os.approval_engine import ApprovalEngine
from agent_os.contracts import AgentInput


class TestSelfReflectionValidationIntegration(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _write_common_configs(self, repo: Path, *, command: list[str]) -> None:
        self._write_json(
            repo / "configs/tooling/runtime_providers.json",
            {
                "default_provider": "agent_os_python",
                "providers": {
                    "agent_os_python": {"enabled": True, "fallback_chain": []},
                    "zeroclaw": {
                        "enabled": False,
                        "env_flag": "ENABLE_ZEROCLAW_ADAPTER",
                        "fallback_chain": ["agent_os_python"],
                        "capabilities": ["local_execution", "background_jobs"],
                        "autonomy_level": "bounded_initiative",
                        "background_jobs_supported": True,
                        "approval_gates": ["external"],
                        "resource_limits": {"timeout_seconds": 15},
                        "network_policy": "profile_defined",
                        "max_chain_length": 4,
                        "max_cost_usd_per_run": 0.02,
                        "stop_conditions": ["user_stop", "loop_stop"],
                    },
                },
                "routing_overrides": [],
            },
        )
        self._write_json(
            repo / "configs/tooling/zeroclaw_profiles.json",
            {
                "profiles": {
                    "zera-edge-local": {
                        "channel": "edge",
                        "persona_id": "zera-v1",
                        "persona_version": "zera-v1",
                        "memory_policy": "companion-curated-v1",
                        "autonomy_mode": "bounded_initiative",
                        "approval_policy": "zera-standard",
                        "background_profile": "zera-companion",
                        "scheduler_profile": "local-dev",
                        "budget_profile": "zera-standard",
                        "network_policy": "local-dev-restricted",
                        "workspace_scope": "workspace_only",
                        "tool_allowlist": ["memory_read", "memory_write", "background_queue", "goal_stack"],
                        "execution_mode": "stdio_json",
                        "timeout_seconds": 10,
                        "command": command,
                    }
                }
            },
        )
        tooling = repo / "configs/tooling"
        tooling.mkdir(parents=True, exist_ok=True)
        (tooling / "self_reflection_schema.json").write_text(
            (ROOT / "configs/tooling/self_reflection_schema.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (tooling / "reflection_agent_system.md").write_text(
            (ROOT / "configs/tooling/reflection_agent_system.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (tooling / "autonomy_policy.yaml").write_text(
            "\n".join(
                [
                    "policy_name: \"test-policy\"",
                    "default_action_class: always_allowed",
                    "action_classes:",
                    "  always_allowed:",
                    "    blocked: false",
                    "    requires_approval: false",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (tooling / "background_jobs.yaml").write_text("scheduler_profiles:\n  local-dev:\n    cadence_policy: debug\njobs:\n", encoding="utf-8")
        (tooling / "tool_execution_policy.yaml").write_text("allowed_tools:\n  memory_read: read_only\n  memory_write: workspace_only\n  background_queue: workspace_only\n  goal_stack: workspace_only\n", encoding="utf-8")
        (tooling / "network_policy.yaml").write_text("policies:\n  local-dev-restricted:\n    mode: allowlist\n    allow_hosts:\n      - localhost\n", encoding="utf-8")
        (tooling / "budget_policy.yaml").write_text("profiles:\n  zera-standard:\n    max_recursive_depth: \"4\"\n", encoding="utf-8")
        self._write_json(tooling / "persona_eval_suite.json", {"thresholds": {"overall_min": 0.7}})

    def _read_trace_events(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_regular_run_does_not_emit_self_reflection_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace_file = repo / "logs/trace.jsonl"
            self._write_common_configs(
                repo,
                command=[
                    "python3",
                    str(ROOT / "repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py"),
                    "--profile",
                    "zera-edge-local",
                ],
            )

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                output = AgentRuntime(repo_root=repo).run(
                    AgentInput(
                        run_id="run-valid-reflection",
                        objective="help me organize next week",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C2",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "zera-edge-local",
                            "persona_id": "zera-v1",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
                os.environ.pop("AGENT_OS_TRACE_FILE", None)

            self.assertEqual(output.status, "completed")
            events = self._read_trace_events(trace_file)
            reflection_events = [row for row in events if row.get("event_type") == "self_reflection_written"]
            self.assertEqual(len(reflection_events), 0)
            invalid_events = [row for row in events if row.get("event_type") == "self_reflection_invalid"]
            self.assertEqual(len(invalid_events), 0)

    def test_review_required_self_reflection_emits_written_event_and_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace_file = repo / "logs/trace.jsonl"
            self._write_common_configs(
                repo,
                command=[
                    "python3",
                    str(ROOT / "repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py"),
                    "--profile",
                    "zera-edge-local",
                ],
            )

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                output = AgentRuntime(repo_root=repo).run(
                    AgentInput(
                        run_id="run-review-required-reflection",
                        objective="write operational self-reflection",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C2",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "zera-edge-local",
                            "persona_id": "zera-v1",
                            "background_job_type": "self_reflection",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
                os.environ.pop("AGENT_OS_TRACE_FILE", None)

            self.assertEqual(output.status, "completed")
            events = self._read_trace_events(trace_file)
            reflection_events = [row for row in events if row.get("event_type") == "self_reflection_written"]
            self.assertEqual(len(reflection_events), 1)
            self.assertEqual(reflection_events[0]["data"]["decision"], "review_required")
            approval_events = [row for row in events if row.get("event_type") == "approval_gate_triggered"]
            self.assertEqual(len(approval_events), 1)
            tickets = ApprovalEngine(repo).list_tickets(status="pending")
            self.assertEqual(len(tickets), 1)
            self.assertEqual(tickets[0].action_type, "request_operator_review")

    def test_invalid_self_reflection_emits_invalid_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace_file = repo / "logs/trace.jsonl"
            invalid_adapter = repo / "invalid_reflection_adapter.py"
            invalid_adapter.write_text(
                "\n".join(
                    [
                        "import json, sys",
                        "payload = json.loads(sys.stdin.read() or '{}')",
                        "print(json.dumps({",
                        "  'status': 'completed',",
                        "  'diff_summary': 'invalid reflection emitted',",
                        "  'test_report': {'status': 'not-run', 'details': 'test adapter'},",
                        "  'artifacts': [],",
                        "  'next_action': 'none',",
                        "  'meta': {",
                        "    'selected_mode': 'plan',",
                        "    'self_reflection': {'summary': 'too short'},",
                        "    'initiative_proposals': []",
                        "  }",
                        "}))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self._write_common_configs(
                repo,
                command=["python3", str(invalid_adapter), "--profile", "zera-edge-local"],
            )

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                output = AgentRuntime(repo_root=repo).run(
                    AgentInput(
                        run_id="run-invalid-reflection",
                        objective="summarize my day",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C2",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "zera-edge-local",
                            "persona_id": "zera-v1",
                            "background_job_type": "self_reflection",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
                os.environ.pop("AGENT_OS_TRACE_FILE", None)

            self.assertEqual(output.status, "completed")
            events = self._read_trace_events(trace_file)
            reflection_events = [row for row in events if row.get("event_type") == "self_reflection_written"]
            self.assertEqual(len(reflection_events), 0)
            invalid_events = [row for row in events if row.get("event_type") == "self_reflection_invalid"]
            self.assertGreaterEqual(len(invalid_events), 1)
            self.assertIn("Self-reflection rejected by reflection policy", str(invalid_events[0].get("message") or ""))

    def test_auto_apply_memory_tag_writes_memory_store(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace_file = repo / "logs/trace.jsonl"
            auto_apply_adapter = repo / "auto_apply_reflection_adapter.py"
            auto_apply_adapter.write_text(
                "\n".join(
                    [
                        "import json, sys",
                        "json.loads(sys.stdin.read() or '{}')",
                        "print(json.dumps({",
                        "  'status': 'completed',",
                        "  'diff_summary': 'auto apply reflection emitted',",
                        "  'test_report': {'status': 'not-run', 'details': 'test adapter'},",
                        "  'artifacts': [],",
                        "  'next_action': 'none',",
                        "  'meta': {",
                        "    'selected_mode': 'plan',",
                        "    'self_reflection': {",
                        "      'summary': 'Observed recurring preference for concise memory tags in short planning sessions.',",
                        "      'improvement_area': 'memory',",
                        "      'problem_statement': 'Short planning sessions repeatedly surface the same local preference and benefit from lightweight memory capture.',",
                        "      'root_cause_hypothesis': 'The runtime currently discards a bounded local preference that is stable enough for short-term reuse.',",
                        "      'proposed_change': 'Write a local memory tag that keeps the preference available for the next planning session only.',",
                        "      'expected_benefit': 'Reduce repeated clarification turns in similar planning contexts.',",
                        "      'risk_assessment': {'risk_level': 'low', 'main_risks': ['Memory tag may expire before the next similar session.'], 'safety_impact': 'none'},",
                        "      'bounded_action': {'action_type': 'propose_memory_tag', 'target': 'planning.short_session.preference', 'limit': 'Write a short-lived working-memory tag only.'},",
                        "      'confidence': 0.82,",
                        "      'evidence_refs': ['trace:planning-session-1'],",
                        "      'scope': 'local',",
                        "      'success_criteria': ['A working-memory tag is stored for the next related session.']",
                        "    },",
                        "    'initiative_proposals': []",
                        "  }",
                        "}))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self._write_common_configs(
                repo,
                command=["python3", str(auto_apply_adapter), "--profile", "zera-edge-local"],
            )

            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                output = AgentRuntime(repo_root=repo).run(
                    AgentInput(
                        run_id="run-auto-apply-memory-tag",
                        objective="write operational self-reflection",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T7",
                            "complexity": "C2",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "zera-edge-local",
                            "persona_id": "zera-v1",
                            "background_job_type": "self_reflection",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
                os.environ.pop("AGENT_OS_TRACE_FILE", None)

            self.assertEqual(output.status, "completed")
            events = self._read_trace_events(trace_file)
            reflection_events = [row for row in events if row.get("event_type") == "self_reflection_written"]
            self.assertEqual(len(reflection_events), 1)
            self.assertEqual(reflection_events[0]["data"]["decision"], "auto_apply_memory_tag")
            approval_events = [row for row in events if row.get("event_type") == "approval_gate_triggered"]
            self.assertEqual(len(approval_events), 0)
            memory_file = repo / ".agents/memory/memory.jsonl"
            self.assertTrue(memory_file.exists())
            rows = [json.loads(line) for line in memory_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            reflection_rows = [row for row in rows if str(row.get("key") or "").startswith("reflection:run-auto-apply-memory-tag:")]
            self.assertEqual(len(reflection_rows), 1)


if __name__ == "__main__":
    unittest.main()
