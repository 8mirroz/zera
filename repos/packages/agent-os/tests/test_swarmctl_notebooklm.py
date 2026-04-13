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


class TestSwarmctlNotebookLM(unittest.TestCase):
    def test_notebooklm_doctor_json_output(self) -> None:
        fake_report = {
            "status": "pass",
            "checks": {"binary": {"ok": True}},
            "hints": [],
            "binary_ok": True,
            "version_ok": True,
            "auth_ok": True,
            "paths_ok": True,
        }
        out = io.StringIO()
        with patch.object(swarmctl, "_repo_root", return_value=ROOT), patch.object(
            swarmctl, "run_notebooklm_doctor", return_value=fake_report
        ), redirect_stdout(out):
            rc = swarmctl.cmd_notebooklm_doctor(SimpleNamespace(json=True, extended_test=False))

        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "pass")

    def test_notebooklm_smoke_basic_failure_path(self) -> None:
        # Fail auth check to force non-zero status.
        def fake_run(cmd: list[str], timeout: int = 120):
            joined = " ".join(cmd)
            if joined == "auth check --json":
                return {"cmd": cmd, "ok": False, "code": 2, "stdout": "", "stderr": "auth failed"}
            return {"cmd": cmd, "ok": True, "code": 0, "stdout": "ok", "stderr": ""}

        out = io.StringIO()
        args = SimpleNamespace(
            json=True,
            e2e=False,
            cleanup=False,
            timeout=60,
            retry=3,
            output_file="/tmp/notebooklm-smoke-report.md",
            e2e_notebook_title="smoke",
        )
        with patch.object(swarmctl, "_run_notebooklm_command", side_effect=fake_run), redirect_stdout(out):
            rc = swarmctl.cmd_notebooklm_smoke(args)

        self.assertEqual(rc, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "fail")
        self.assertTrue(any(c["name"] == "auth_check" and not c["ok"] for c in payload["checks"]))

    def test_notebooklm_smoke_e2e_create_parse_failure(self) -> None:
        def fake_run(cmd: list[str], timeout: int = 120):
            joined = " ".join(cmd)
            if joined == "create bad":
                return {"cmd": cmd, "ok": True, "code": 0, "stdout": "created", "stderr": ""}
            return {"cmd": cmd, "ok": True, "code": 0, "stdout": "ok", "stderr": ""}

        out = io.StringIO()
        args = SimpleNamespace(
            json=True,
            e2e=True,
            cleanup=False,
            timeout=60,
            retry=3,
            output_file="/tmp/notebooklm-smoke-report.md",
            e2e_notebook_title="bad",
        )
        with patch.object(swarmctl, "_run_notebooklm_command", side_effect=fake_run), redirect_stdout(out):
            rc = swarmctl.cmd_notebooklm_smoke(args)

        self.assertEqual(rc, 2)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "fail")
        self.assertTrue(any(c["name"] == "e2e_notebook_id_parse" for c in payload["checks"]))


if __name__ == "__main__":
    unittest.main()
