from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.registry_workflows import RegistryWorkflowResolver


class TestRegistryWorkflowResolver(unittest.TestCase):
    def test_resolve_swarm_workflow_with_handoff_and_iteration_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "configs/orchestrator").mkdir(parents=True)
            (repo / "configs/registry/workflows").mkdir(parents=True)
            (repo / "configs/registry/skills").mkdir(parents=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
version: "4.2"
routing:
  tiers:
    C4:
      path: "Swarm Path"
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
                encoding="utf-8",
            )
            (repo / "configs/registry/workflows/path-swarm.yaml").write_text(
                """
id: swarm-path-to-completion
name: Swarm Path (C4-C5)
entry_agent: core-orchestrator
handoff_skill: dynamic-handoff
iteration_skill: ralph-loop-execute
knowledge_policy:
  pre_search: true
  writeback: true
stages:
  - id: plan
    agent: architecture-systems-architect
  - id: audit
    agent: review-security-audit
completion_criteria:
  - "audit ok"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/registry/skills/dynamic-handoff.yaml").write_text(
                """
id: dynamic-handoff
outputs: [handoff_contract, event_log]
contract_fields: [objective, evidence, next_owner]
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/registry/skills/ralph-loop-execute.yaml").write_text(
                """
id: ralph-loop-execute
outputs: [best_solution, comparison_log]
comparison_mode: score_then_select
verification_required: true
""".strip()
                + "\n",
                encoding="utf-8",
            )

            payload = RegistryWorkflowResolver(repo).resolve(
                task_type="T4",
                complexity="C4",
                orchestration_path="Swarm Path",
            )

            self.assertEqual(payload["workflow_id"], "swarm-path-to-completion")
            self.assertEqual(payload["handoff"]["skill_id"], "dynamic-handoff")
            self.assertTrue(payload["handoff"]["required"])
            self.assertEqual(payload["handoff"]["contract_fields"], ["objective", "evidence", "next_owner"])
            self.assertTrue(payload["iteration"]["enabled"])
            self.assertEqual(payload["iteration"]["iterations"], 5)
            self.assertEqual(payload["iteration"]["comparison_mode"], "score_then_select")

    def test_resolve_derives_orchestration_path_from_workflow_ref_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "configs/orchestrator").mkdir(parents=True)
            (repo / "configs/registry/workflows").mkdir(parents=True)
            (repo / "configs/registry/skills").mkdir(parents=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
version: "4.2"
routing:
  tiers:
    C4:
      workflow: "configs/registry/workflows/path-swarm.yaml"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/registry/workflows/path-swarm.yaml").write_text(
                """
id: swarm-path-to-completion
name: Swarm Path (C4-C5)
handoff_skill: dynamic-handoff
iteration_skill: ralph-loop-execute
stages:
  - id: plan
    agent: architecture-systems-architect
""".strip()
                + "\n",
                encoding="utf-8",
            )
            (repo / "configs/registry/skills/dynamic-handoff.yaml").write_text("id: dynamic-handoff\n", encoding="utf-8")
            (repo / "configs/registry/skills/ralph-loop-execute.yaml").write_text("id: ralph-loop-execute\n", encoding="utf-8")

            payload = RegistryWorkflowResolver(repo).resolve(
                task_type="T2",
                complexity="C4",
                orchestration_path=None,
            )

            self.assertEqual(payload["orchestration_path"], "Swarm Path")


if __name__ == "__main__":
    unittest.main()
