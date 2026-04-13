from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "repos/packages/agent-os/scripts/smart_skill_matching.py"


class TestSmartSkillMatchingTrace(unittest.TestCase):
    def test_cli_emits_schema_normalized_trace_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            skill_dir = temp / "skills" / "debugging"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "\n".join(
                    [
                        "---",
                        "name: systematic-debugging",
                        "description: Debug failing tests systematically.",
                        "triggers:",
                        "  - failing test",
                        "---",
                        "# Systematic Debugging",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            trace_file = temp / "trace.jsonl"
            env = {**os.environ, "AGENT_OS_TRACE_FILE": str(trace_file)}

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "fix failing test",
                    "--skills_dir",
                    str(temp / "skills"),
                    "--run_id",
                    "skill-run-1",
                    "--task_type",
                    "T2",
                    "--json",
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(trace_file.exists(), "smart_skill_matching did not emit a trace event")
            row = json.loads(trace_file.read_text(encoding="utf-8").strip())
            self.assertEqual(row["event_type"], "skill_selection_metadata")
            self.assertEqual(row["run_id"], "skill-run-1")
            self.assertEqual(row["level"], "info")
            self.assertEqual(row["component"], "agent")
            self.assertEqual(row["data"]["top_skill"], "systematic-debugging")


if __name__ == "__main__":
    unittest.main()
