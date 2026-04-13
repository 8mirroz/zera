from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import swarmctl


class TestSwarmctlSwarm(unittest.TestCase):
    def _write(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _repo(self) -> tempfile.TemporaryDirectory[str]:
        td = tempfile.TemporaryDirectory()
        repo = Path(td.name)
        self._write(
            repo / "configs/registry/workflows/path-swarm.yaml",
            """
id: swarm-path-to-completion
name: Swarm Path (C4-C5)
version: 1.1.0
entry_agent: core-orchestrator
handoff_skill: dynamic-handoff
iteration_skill: ralph-loop-execute
knowledge_policy:
  pre_search: true
  writeback: true
stages:
  - id: plan
    agent: architecture-systems-architect
  - id: sprint
    agent: execution-builder
completion_criteria:
  - "All components are integrated"
""".strip()
            + "\n",
        )
        self._write(
            repo / "configs/orchestrator/lane_events.yaml",
            """
version: "2026-04-08"
feature_flag: "ENABLE_SWARM_V2"
storage: ".agent/swarm/events/{task_id}.jsonl"
event_types:
  - Started
  - Failed
  - Finished
  - CollisionDetected
payload_required_fields:
  - lane_id
  - task_id
  - event_type
  - payload
  - ts
""".strip()
            + "\n",
        )
        self._write(
            repo / "configs/orchestrator/swarm_recovery.yaml",
            """
version: "2026-04-08"
feature_flag: "ENABLE_SWARM_V2"
failure_type_mapping:
  compile: compile_failure
  test: test_failure
policy:
  max_auto_recovery_attempts: 1
  fallback_after_failed_recovery: true
""".strip()
            + "\n",
        )
        self._write(
            repo / "configs/orchestrator/router.yaml",
            """
routing:
  tiers:
    C4:
      name: "Complex"
      workflow: "configs/registry/workflows/path-swarm.yaml"
      ralph_loop:
        enabled: true
        iterations: 5
  handoff_safeguards:
    max_chain_depth: 2
    forbid_cycles: true
    require_contract: true
    contract_schema: "configs/registry/schemas/task.schema.yaml"
""".strip()
            + "\n",
        )
        self._write(
            repo / "configs/tooling/runtime_providers.json",
            json.dumps(
                {
                    "default_provider": "agent_os_python",
                    "providers": {
                        "agent_os_python": {
                            "enabled": True,
                            "fallback_chain": [],
                            "capabilities": ["local_execution"],
                            "background_jobs_supported": False,
                        }
                    },
                }
            ),
        )
        self._write(
            repo / "configs/tooling/zeroclaw_profiles.json",
            json.dumps({"profiles": {}}),
        )
        self._write(
            repo / "configs/registry/skills/dynamic-handoff.yaml",
            """
id: dynamic-handoff
outputs: [handoff_contract]
contract_fields: [objective, evidence]
""".strip()
            + "\n",
        )
        self._write(
            repo / "configs/registry/skills/ralph-loop-execute.yaml",
            """
id: ralph-loop-execute
outputs: [best_solution]
comparison_mode: score_then_select
verification_required: true
""".strip()
            + "\n",
        )
        return td

    def test_cmd_swarm_doctor_reports_swarm_v2_readiness(self) -> None:
        with self._repo() as td, patch.object(swarmctl, "_repo_root", return_value=Path(td)), patch.dict(
            os.environ, {"ENABLE_SWARM_V2": "1"}, clear=False
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = swarmctl.cmd_swarm_doctor(SimpleNamespace())
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertTrue(payload["feature_enabled"])
            self.assertEqual(payload["workflow"]["handoff_skill"], "dynamic-handoff")
            self.assertEqual(payload["lane_events"]["storage"], ".agent/swarm/events/{task_id}.jsonl")

    def test_cmd_swarm_inspect_merges_route_workflow_and_recovery(self) -> None:
        with self._repo() as td, patch.object(swarmctl, "_repo_root", return_value=Path(td)), patch.dict(
            os.environ, {"ENABLE_SWARM_V2": "true"}, clear=False
        ), patch.object(
            swarmctl,
            "resolve_route_context",
            return_value={
                "mcp_profile": "swarm",
                "route": {
                    "orchestration_path": "Swarm Path",
                    "runtime_provider": "agent_os_python",
                    "runtime_profile": None,
                    "primary_model": "openrouter/anthropic/claude-3.7-sonnet",
                    "telemetry": {"v4_path": "Swarm Path"},
                },
            },
        ):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = swarmctl.cmd_swarm_inspect(
                    SimpleNamespace(
                        objective="complex refactor with recovery",
                        task_type="T4",
                        complexity="C4",
                        execution_channel="auto",
                    )
                )
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["mcp_profile"], "swarm")
            self.assertEqual(payload["workflow"]["workflow_id"], "swarm-path-to-completion")
            self.assertEqual(payload["recovery"]["policy"]["max_auto_recovery_attempts"], 1)
            self.assertIn("CollisionDetected", payload["lane_events"]["event_types"])

    def test_cmd_swarm_events_summarizes_lane_event_file(self) -> None:
        with self._repo() as td, patch.object(swarmctl, "_repo_root", return_value=Path(td)), patch.dict(
            os.environ, {"ENABLE_SWARM_V2": "1"}, clear=False
        ):
            repo = Path(td)
            event_file = repo / ".agent/swarm/events/task-123.jsonl"
            event_file.parent.mkdir(parents=True, exist_ok=True)
            event_file.write_text(
                "\n".join(
                    [
                        json.dumps({"lane_id": "plan", "task_id": "task-123", "event_type": "Started", "payload": {}, "ts": "2026-04-08T00:00:00Z"}),
                        json.dumps({"lane_id": "plan", "task_id": "task-123", "event_type": "CollisionDetected", "payload": {}, "ts": "2026-04-08T00:00:01Z"}),
                        json.dumps({"lane_id": "sprint", "task_id": "task-123", "event_type": "Failed", "payload": {}, "ts": "2026-04-08T00:00:02Z"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            out = io.StringIO()
            with redirect_stdout(out):
                rc = swarmctl.cmd_swarm_events(SimpleNamespace(task_id="task-123"))
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["event_count"], 3)
            self.assertEqual(payload["failed_event_count"], 1)
            self.assertTrue(payload["collision_detected"])
            self.assertEqual(payload["lanes"], ["plan", "sprint"])


if __name__ == "__main__":
    unittest.main()
