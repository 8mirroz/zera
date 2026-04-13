from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS))

import notebooklm_router_prompt


class TestNotebookLMRouterPrompt(unittest.TestCase):
    def _write(self, path: Path, data: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    def test_build_router_packet_research(self) -> None:
        packet = notebooklm_router_prompt.build_router_packet(
            ROOT,
            workflow="research_artifacts",
            objective="analyze AI policy",
            output_path="./brief.md",
            with_checkpoints=True,
        )
        self.assertEqual(packet["workflow"], "research_artifacts")
        self.assertEqual(packet["objective"], "analyze AI policy")
        self.assertGreaterEqual(len(packet["states"]), 5)
        self.assertGreaterEqual(len(packet["commands"]), 5)
        self.assertIn("stateful workflow router", packet["router_prompt"])
        self.assertGreaterEqual(len(packet["checkpoints"]), 1)

    def test_unknown_workflow_raises(self) -> None:
        with self.assertRaises(ValueError):
            notebooklm_router_prompt.build_router_packet(
                ROOT,
                workflow="unknown",
                objective="x",
            )

    def test_template_file_shape(self) -> None:
        cfg = json.loads((ROOT / "configs/tooling/notebooklm_agent_router_templates.json").read_text(encoding="utf-8"))
        self.assertIn("workflows", cfg)
        for key in ("research_artifacts", "ide_assist", "debug_triage"):
            self.assertIn(key, cfg["workflows"])


if __name__ == "__main__":
    unittest.main()
