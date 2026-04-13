from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import swarmctl


class TestSwarmctlBackgroundControls(unittest.TestCase):
    def _capture(self, fn, args) -> dict:
        prev_stdout = sys.stdout
        stdout = StringIO()
        sys.stdout = stdout
        try:
            code = fn(args)
        finally:
            sys.stdout = prev_stdout
        self.assertEqual(code, 0)
        return json.loads(stdout.getvalue())

    def test_pause_and_resume_commands(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            try:
                paused = self._capture(swarmctl.cmd_background_pause, type("Args", (), {"minutes": 15})())
                self.assertEqual(paused["status"], "paused")
                resumed = self._capture(swarmctl.cmd_background_resume, type("Args", (), {})())
                self.assertEqual(resumed["status"], "resumed")
            finally:
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo


if __name__ == "__main__":
    unittest.main()
