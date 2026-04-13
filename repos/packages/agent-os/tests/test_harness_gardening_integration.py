from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from agent_os.agent_runtime import AgentRuntime
from agent_os.background_scheduler import BackgroundJobQueue
from agent_os.contracts import AgentInput
import swarmctl


class TestHarnessGardeningIntegration(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _read_trace(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_runtime_enqueue_and_daemon_execute_harness_gardening(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace_file = repo / "logs" / "agent_traces.jsonl"

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
                        "worker-maint-local": {
                            "channel": "edge",
                            "persona_id": "agent-os",
                            "persona_version": "agent-os-v1",
                            "memory_policy": "maintenance-curated-v1",
                            "autonomy_mode": "bounded_initiative",
                            "approval_policy": "operator-standard",
                            "background_profile": "worker-maintenance",
                            "scheduler_profile": "local-dev",
                            "budget_profile": "operator-standard",
                            "network_policy": "local-dev-restricted",
                            "workspace_scope": "workspace_only",
                            "tool_allowlist": ["memory_read", "background_queue"],
                            "execution_mode": "stdio_json",
                            "timeout_seconds": 10,
                            "command": [
                                "python3",
                                str(ROOT / "repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py"),
                                "--profile",
                                "worker-maint-local",
                            ],
                        }
                    }
                },
            )
            tooling = repo / "configs/tooling"
            tooling.mkdir(parents=True, exist_ok=True)
            (tooling / "background_jobs.yaml").write_text(
                "\n".join(
                    [
                        "scheduler_profiles:",
                        "  local-dev:",
                        "    cadence_policy: debug",
                        "jobs:",
                        "  harness_gardening:",
                        "    cadence_minutes: 60",
                        "    retry_limit: 1",
                        "    concurrency_limit: 1",
                        "    quiet_hours: \"00:00-00:00\"",
                        "    stop_condition: manual_stop",
                        "    escalation_rule: queue_review",
                        "    user_suppressible: false",
                        "    daily_cap: 1",
                        "    staleness_minutes: 1440",
                        "    budget_profile: \"operator-standard\"",
                        "    mode: diagnostic_only",
                    ]
                )
                + "\n",
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
            (tooling / "tool_execution_policy.yaml").write_text(
                "allowed_tools:\n  memory_read: read_only\n  background_queue: workspace_only\n",
                encoding="utf-8",
            )
            (tooling / "network_policy.yaml").write_text(
                "policies:\n  local-dev-restricted:\n    mode: allowlist\n    allow_hosts:\n      - localhost\n",
                encoding="utf-8",
            )
            (tooling / "budget_policy.yaml").write_text(
                "profiles:\n  operator-standard:\n    max_recursive_depth: \"4\"\n",
                encoding="utf-8",
            )

            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            prev_trace = os.environ.get("AGENT_OS_TRACE_FILE")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            try:
                output = AgentRuntime(repo_root=repo).run(
                    AgentInput(
                        run_id="run-maint-harness",
                        objective="harden routing and observability evidence",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T4",
                            "complexity": "C4",
                            "runtime_provider": "zeroclaw",
                            "runtime_profile": "worker-maint-local",
                            "persona_id": "agent-os",
                            "proof_required": True,
                        },
                    )
                )
                self.assertEqual(output.status, "completed")

                queue = BackgroundJobQueue(repo)
                queue_payload = json.loads(queue.queue_path.read_text(encoding="utf-8"))
                self.assertEqual(len(queue_payload.get("queued", [])), 1)
                queued = queue_payload["queued"][0]
                self.assertEqual(queued["job_type"], "harness_gardening")
                self.assertIn("read-only harness gardening sweep", queued["objective"])

                runtime_events = self._read_trace(trace_file)
                scheduled = [
                    row
                    for row in runtime_events
                    if row.get("event_type") == "background_job_started"
                    and row.get("background_job_type") == "harness_gardening"
                ]
                accepted = [
                    row
                    for row in runtime_events
                    if row.get("event_type") == "background_job_completed"
                    and row.get("background_job_type") == "harness_gardening"
                    and "accepted into scheduler shadow queue" in str(row.get("message") or "")
                ]
                self.assertEqual(len(scheduled), 1)
                self.assertEqual(len(accepted), 1)

                fake_report = {
                    "status": "ok",
                    "task": queued["objective"],
                    "candidate_count": 0,
                    "candidates": [],
                    "job_config": {"mode": "diagnostic_only"},
                    "inputs": {"harness_report": {"status": "ok"}},
                }
                with patch.object(swarmctl, "_refresh_benchmark_latest", return_value={"status": "ok", "exit_code": 0}), patch.object(
                    swarmctl, "_harness_gardening_report_payload", return_value=fake_report
                ):
                    code = swarmctl.cmd_background_daemon(type("Args", (), {"limit": 10})())
                self.assertEqual(code, 0)

                queue_payload = json.loads(queue.queue_path.read_text(encoding="utf-8"))
                self.assertEqual(len(queue_payload.get("queued", [])), 0)
                self.assertEqual(len(queue_payload.get("completed", [])), 1)
                completed = queue_payload["completed"][0]
                self.assertEqual(completed["job_type"], "harness_gardening")
                self.assertEqual(completed["result"]["status"], "completed")

                snapshot_path = repo / "explore/reports/harness_gardening_latest.json"
                self.assertTrue(snapshot_path.exists())
                snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                self.assertEqual(snapshot["status"], "ok")
                self.assertEqual(snapshot["candidate_count"], 0)

                all_events = self._read_trace(trace_file)
                self.assertTrue(any(row.get("event_type") == "harness_validation_started" for row in all_events))
                self.assertTrue(any(row.get("event_type") == "harness_evidence_collected" for row in all_events))
                self.assertTrue(any(row.get("event_type") == "harness_validation_completed" for row in all_events))
                self.assertTrue(
                    any(
                        row.get("event_type") == "background_job_completed"
                        and row.get("background_job_type") == "harness_gardening"
                        and "Background daemon completed job" in str(row.get("message") or "")
                        for row in all_events
                    )
                )
            finally:
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo
                if prev_trace is None:
                    os.environ.pop("AGENT_OS_TRACE_FILE", None)
                else:
                    os.environ["AGENT_OS_TRACE_FILE"] = prev_trace


if __name__ == "__main__":
    unittest.main()
