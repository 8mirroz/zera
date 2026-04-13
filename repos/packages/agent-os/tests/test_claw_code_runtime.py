from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.agent_runtime import AgentRuntime
from agent_os.contracts import AgentInput


class TestClawCodeRuntime(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _write_runtime_config(self, repo: Path, profile: dict | None = None) -> None:
        self._write_json(
            repo / "configs/tooling/runtime_providers.json",
            {
                "default_provider": "agent_os_python",
                "providers": {
                    "agent_os_python": {"enabled": True, "fallback_chain": []},
                    "claw_code": {
                        "enabled": False,
                        "env_flag": "ENABLE_CLAW_CODE",
                        "fallback_chain": ["agent_os_python"],
                        "capabilities": ["local_execution", "tool_execution", "recovery"],
                        "autonomy_level": "bounded_initiative",
                        "approval_gates": ["destructive", "external"],
                        "profiles": {"claw-local": profile or {}},
                    },
                },
                "routing_overrides": [],
            },
        )

    def test_claw_code_runtime_executes_health_probe_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_runtime_config(repo)

            os.environ["ENABLE_CLAW_CODE"] = "true"
            os.environ["CLAW_CODE_BIN"] = "echo"
            try:
                output = AgentRuntime(repo_root=repo).run(
                    AgentInput(
                        run_id="run-claw-health",
                        objective="test",
                        plan_steps=["probe"],
                        route_decision={
                            "task_type": "T3",
                            "complexity": "C3",
                            "runtime_provider": "claw_code",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_CLAW_CODE", None)
                os.environ.pop("CLAW_CODE_BIN", None)

            self.assertEqual(output.status, "completed")
            self.assertIn("Claw-Code runtime provider executed health probe", output.diff_summary)

    def test_claw_code_runtime_executes_stdio_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            adapter = repo / "adapter.py"
            adapter.write_text(
                "\n".join(
                    [
                        "import json, sys",
                        "payload = json.loads(sys.stdin.read())",
                        "print(json.dumps({",
                        "  'status': 'completed',",
                        "  'diff_summary': 'claw adapter accepted ' + payload['run_id'],",
                        "  'test_report': {'status': 'not-run'},",
                        "  'artifacts': [],",
                        "  'next_action': 'none',",
                        "  'meta': {'adapter': 'test'},",
                        "}))",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            self._write_runtime_config(
                repo,
                {
                    "execution_mode": "stdio_json",
                    "workspace_scope": "workspace_only",
                    "tool_allowlist": ["memory_read"],
                    "network_policy": "local-dev-restricted",
                    "command": ["python3", str(adapter)],
                },
            )
            (repo / "configs/tooling").mkdir(parents=True, exist_ok=True)
            (repo / "configs/tooling/tool_execution_policy.yaml").write_text(
                "allowed_tools:\n  memory_read: read_only\n",
                encoding="utf-8",
            )
            (repo / "configs/tooling/network_policy.yaml").write_text(
                "policies:\n  local-dev-restricted:\n    mode: allowlist\n",
                encoding="utf-8",
            )

            os.environ["ENABLE_CLAW_CODE"] = "true"
            try:
                output = AgentRuntime(repo_root=repo).run(
                    AgentInput(
                        run_id="run-claw-stdio",
                        objective="test",
                        plan_steps=["execute"],
                        route_decision={
                            "task_type": "T3",
                            "complexity": "C3",
                            "runtime_provider": "claw_code",
                            "runtime_profile": "claw-local",
                        },
                    )
                )
            finally:
                os.environ.pop("ENABLE_CLAW_CODE", None)

            self.assertEqual(output.status, "completed")
            self.assertIn("claw adapter accepted run-claw-stdio", output.diff_summary)
            self.assertEqual(output.meta["adapter"], "test")

    def test_claw_code_stdio_failure_emits_recovery_event_before_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            adapter = repo / "bad_adapter.py"
            adapter.write_text("print('not json')\n", encoding="utf-8")
            self._write_runtime_config(
                repo,
                {
                    "execution_mode": "stdio_json",
                    "workspace_scope": "workspace_only",
                    "tool_allowlist": ["memory_read"],
                    "network_policy": "local-dev-restricted",
                    "command": ["python3", str(adapter)],
                },
            )
            (repo / "configs/tooling").mkdir(parents=True, exist_ok=True)
            (repo / "configs/tooling/tool_execution_policy.yaml").write_text(
                "allowed_tools:\n  memory_read: read_only\n",
                encoding="utf-8",
            )
            (repo / "configs/tooling/network_policy.yaml").write_text(
                "policies:\n  local-dev-restricted:\n    mode: allowlist\n",
                encoding="utf-8",
            )

            events: list[tuple[str, dict]] = []
            os.environ["ENABLE_CLAW_CODE"] = "true"
            try:
                with patch("agent_os.agent_runtime.emit_event", side_effect=lambda event_type, payload: events.append((event_type, payload))):
                    output = AgentRuntime(repo_root=repo).run(
                        AgentInput(
                            run_id="run-claw-bad-json",
                            objective="test",
                            plan_steps=["execute"],
                            route_decision={
                                "task_type": "T3",
                                "complexity": "C3",
                                "runtime_provider": "claw_code",
                                "runtime_profile": "claw-local",
                            },
                        )
                    )
            finally:
                os.environ.pop("ENABLE_CLAW_CODE", None)

            self.assertEqual(output.status, "completed")
            event_types = [event_type for event_type, _ in events]
            self.assertIn("runtime_recovery_attempted", event_types)
            self.assertIn("runtime_degraded_mode_entered", event_types)
            self.assertIn("runtime_provider_fallback", event_types)
            self.assertLess(event_types.index("runtime_recovery_attempted"), event_types.index("runtime_provider_fallback"))
            self.assertLess(event_types.index("runtime_degraded_mode_entered"), event_types.index("runtime_provider_fallback"))
            recovery = next(payload for event_type, payload in events if event_type == "runtime_recovery_attempted")
            self.assertEqual(recovery["data"]["failure_type"], "stdio_json_failure")
            self.assertTrue(recovery["data"]["degraded_mode"])


if __name__ == "__main__":
    unittest.main()
