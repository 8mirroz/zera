from __future__ import annotations

import io
import json
import os
import sys
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


class TestSwarmctlNotebookLMRouter(unittest.TestCase):
    def test_router_prompt_json(self) -> None:
        fake = {
            "workflow": "ide_assist",
            "objective": "help onboarding",
            "states": [{"state": "ingest", "goal": "g", "exit": "e"}],
            "commands": ["notebooklm list"],
            "router_prompt": "router",
            "checkpoints": [],
            "quality_gates": {},
        }
        out = io.StringIO()
        args = SimpleNamespace(
            workflow="ide_assist",
            objective="help onboarding",
            output_path="./x.md",
            no_checkpoints=False,
            json=True,
        )
        with patch.object(swarmctl, "_repo_root", return_value=ROOT), patch.object(
            swarmctl, "build_router_packet", return_value=fake
        ), redirect_stdout(out):
            rc = swarmctl.cmd_notebooklm_router_prompt(args)

        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["workflow"], "ide_assist")

    def test_router_prompt_text(self) -> None:
        fake = {
            "workflow": "debug_triage",
            "objective": "find root cause",
            "states": [{"state": "ingest", "goal": "g", "exit": "e"}],
            "commands": ["notebooklm list"],
            "router_prompt": "router",
            "checkpoints": [],
            "quality_gates": {},
        }
        out = io.StringIO()
        args = SimpleNamespace(
            workflow="debug_triage",
            objective="find root cause",
            output_path="./x.md",
            no_checkpoints=False,
            json=False,
        )
        with patch.object(swarmctl, "_repo_root", return_value=ROOT), patch.object(
            swarmctl, "build_router_packet", return_value=fake
        ), redirect_stdout(out):
            rc = swarmctl.cmd_notebooklm_router_prompt(args)

        self.assertEqual(rc, 0)
        text = out.getvalue()
        self.assertIn("Workflow: debug_triage", text)
        self.assertIn("Router Prompt:", text)


if __name__ == "__main__":
    unittest.main()
