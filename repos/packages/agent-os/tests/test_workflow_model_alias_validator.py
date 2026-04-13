from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS))

import workflow_model_alias_validator as alias_validator


class TestWorkflowModelAliasValidator(unittest.TestCase):
    def test_scan_file_detects_unknown_alias_and_hardcoded_model(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / ".agent/workflows/example.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "Use $AGENT_MODEL_C2_FREE for fast tasks.",
                        "Fallback to ${AGENT_MODEL_DOES_NOT_EXIST}.",
                        "Do not hardcode openrouter/deepseek/deepseek-r1:free in active workflows.",
                    ]
                ),
                encoding="utf-8",
            )

            scan = alias_validator._scan_file(path, root, {"AGENT_MODEL_C2_FREE"})

            self.assertEqual(scan["path"], ".agent/workflows/example.md")
            self.assertIn("AGENT_MODEL_C2_FREE", scan["alias_refs"])
            self.assertEqual(scan["unknown_aliases"], ["AGENT_MODEL_DOES_NOT_EXIST"])
            self.assertIn("openrouter/deepseek/deepseek-r1:free", scan["hardcoded_models"])


if __name__ == "__main__":
    unittest.main()
