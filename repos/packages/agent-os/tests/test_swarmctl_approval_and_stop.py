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


class TestSwarmctlApprovalAndStop(unittest.TestCase):
    def _capture(self, fn, args) -> tuple[int, dict]:
        prev_stdout = sys.stdout
        stdout = StringIO()
        sys.stdout = stdout
        try:
            code = fn(args)
        finally:
            sys.stdout = prev_stdout
        return code, json.loads(stdout.getvalue())

    def test_stop_signal_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            try:
                code, stopped = self._capture(swarmctl.cmd_stop_signal, type("Args", (), {"scope": "global", "minutes": 10, "reason": "operator_stop"})())
                self.assertEqual(code, 0)
                self.assertEqual(stopped["status"], "stopped")
                code, cleared = self._capture(swarmctl.cmd_stop_clear, type("Args", (), {"scope": "global"})())
                self.assertEqual(code, 0)
                self.assertEqual(cleared["status"], "cleared")
            finally:
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo


if __name__ == "__main__":
    unittest.main()
