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


class TestSwarmctlBackgroundStatus(unittest.TestCase):
    def test_background_status_reports_counts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            queue_path = repo / ".agents/runtime/background-jobs.json"
            queue_path.parent.mkdir(parents=True, exist_ok=True)
            queue_path.write_text(
                json.dumps(
                    {
                        "queued": [{"id": "a"}],
                        "completed": [{"id": "b"}, {"id": "c"}],
                        "failed": [],
                        "updated_at": "2026-03-11T00:00:00+00:00",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
            os.environ["AGENT_OS_REPO_ROOT"] = str(repo)
            stdout = StringIO()
            prev_stdout = sys.stdout
            sys.stdout = stdout
            try:
                code = swarmctl.cmd_background_status(type("Args", (), {})())
            finally:
                sys.stdout = prev_stdout
                if prev_repo is None:
                    os.environ.pop("AGENT_OS_REPO_ROOT", None)
                else:
                    os.environ["AGENT_OS_REPO_ROOT"] = prev_repo
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["queued"], 1)
            self.assertEqual(payload["completed"], 2)
            self.assertEqual(payload["failed"], 0)


if __name__ == "__main__":
    unittest.main()
