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

from agent_os.background_scheduler import BackgroundJobQueue
from agent_os.stop_controller import StopController
import swarmctl


class TestSwarmctlBackgroundDaemon(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_background_daemon_drains_queue(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {"enabled": True, "fallback_chain": []},
                        "zeroclaw": {"enabled": False, "env_flag": "ENABLE_ZEROCLAW_ADAPTER", "fallback_chain": ["agent_os_python"]},
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
                            "execution_mode": "stdio_json",
                            "timeout_seconds": 10,
                            "command": [
                                "python3",
                                str(ROOT / "repos/packages/agent-os/scripts/zeroclaw_exec_adapter.py"),
                                "--profile",
                                "zera-edge-local",
                            ],
                        }
                    }
                },
            )
            queue = BackgroundJobQueue(repo)
            queue.enqueue(
                job_type="goal_review",
                objective="review active goals for zera",
                runtime_provider="zeroclaw",
                runtime_profile="zera-edge-local",
                persona_id="zera-v1",
                scheduler_profile="local-dev",
                idempotency_key="test:goal_review:1",
            )
            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            os.environ["ENABLE_ZEROCLAW_ADAPTER"] = "true"
            try:
                code = swarmctl.cmd_background_daemon(type("Args", (), {"limit": 10})())
            finally:
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo
                os.environ.pop("ENABLE_ZEROCLAW_ADAPTER", None)
            self.assertEqual(code, 0)
            payload = json.loads(queue.queue_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload.get("queued", [])), 0)
            self.assertEqual(len(payload.get("completed", [])), 1)

    def test_background_daemon_defers_when_paused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {"default_provider": "agent_os_python", "providers": {"agent_os_python": {"enabled": True, "fallback_chain": []}}, "routing_overrides": []},
            )
            queue = BackgroundJobQueue(repo)
            queue.enqueue(
                job_type="goal_review",
                objective="review active goals for zera",
                runtime_provider="agent_os_python",
                runtime_profile=None,
                persona_id="zera-v1",
                scheduler_profile="local-dev",
                idempotency_key="test:goal_review:paused",
                payload={"job_spec": {"quiet_hours": "00:00-00:00"}},
            )
            queue.pause_for(minutes=15)
            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            try:
                code = swarmctl.cmd_background_daemon(type("Args", (), {"limit": 10})())
            finally:
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo
            self.assertEqual(code, 0)
            payload = json.loads(queue.queue_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload.get("queued", [])), 1)
            self.assertEqual(len(payload.get("completed", [])), 0)

    def test_background_daemon_defers_when_stop_signal_is_active(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {"default_provider": "agent_os_python", "providers": {"agent_os_python": {"enabled": True, "fallback_chain": []}}, "routing_overrides": []},
            )
            queue = BackgroundJobQueue(repo)
            queue.enqueue(
                job_type="goal_review",
                objective="review active goals for zera",
                runtime_provider="agent_os_python",
                runtime_profile=None,
                persona_id="zera-v1",
                scheduler_profile="local-dev",
                idempotency_key="test:goal_review:stopped",
                payload={"job_spec": {"quiet_hours": "00:00-00:00"}},
            )
            StopController(repo).signal(scope="zera-v1", minutes=15)
            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            try:
                code = swarmctl.cmd_background_daemon(type("Args", (), {"limit": 10})())
            finally:
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo
            self.assertEqual(code, 0)
            payload = json.loads(queue.queue_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload.get("queued", [])), 1)
            self.assertEqual(payload["queued"][0]["payload"]["defer_reason"], "stop_signal")

    def test_background_daemon_executes_harness_gardening_locally(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/runtime_providers.json",
                {"default_provider": "agent_os_python", "providers": {"agent_os_python": {"enabled": True, "fallback_chain": []}}, "routing_overrides": []},
            )
            queue = BackgroundJobQueue(repo)
            queue.enqueue(
                job_type="harness_gardening",
                objective="harness validation observability",
                runtime_provider="agent_os_python",
                runtime_profile=None,
                persona_id="agent-os",
                scheduler_profile="local-dev",
                idempotency_key="test:harness_gardening:1",
                payload={"job_spec": {"quiet_hours": "00:00-00:00", "staleness_minutes": 1440}},
            )
            fake_report = {
                "status": "warn",
                "task": "harness validation observability",
                "candidate_count": 1,
                "candidates": [{"id": "missing-doc-refs"}],
                "snapshot_paths": {
                    "latest": str(repo / "explore/reports/harness_gardening_latest.json"),
                    "stamped": str(repo / "explore/reports/harness_gardening_20260408_000000.json"),
                },
            }
            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            try:
                with patch.object(swarmctl, "_refresh_benchmark_latest", return_value={"status": "ok", "exit_code": 0}), patch.object(
                    swarmctl, "_harness_gardening_report_payload", return_value={k: v for k, v in fake_report.items() if k != "snapshot_paths"}
                ), patch.object(
                    swarmctl, "_write_harness_gardening_snapshot", return_value=fake_report["snapshot_paths"]
                ), patch.object(
                    swarmctl.AgentRuntime, "run", side_effect=AssertionError("AgentRuntime.run should not be called for harness_gardening")
                ):
                    code = swarmctl.cmd_background_daemon(type("Args", (), {"limit": 10})())
            finally:
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo
            self.assertEqual(code, 0)
            payload = json.loads(queue.queue_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload.get("queued", [])), 0)
            self.assertEqual(len(payload.get("completed", [])), 1)
            result = payload["completed"][0]["result"]
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["next_action"], "queue_review")
            self.assertEqual(result["report"]["candidate_count"], 1)
            self.assertEqual(result["proof_of_action"]["snapshot_paths"]["latest"], fake_report["snapshot_paths"]["latest"])


if __name__ == "__main__":
    unittest.main()
