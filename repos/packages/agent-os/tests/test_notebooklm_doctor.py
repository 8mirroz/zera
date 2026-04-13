from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS))

import notebooklm_doctor


class TestNotebookLMDoctor(unittest.TestCase):
    def _write(self, path: Path, data: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")

    def _build_config(self, root: Path) -> None:
        self._write(
            root / "configs/tooling/notebooklm_integration.json",
            json.dumps(
                {
                    "version_pin": "0.3.3",
                    "python_bin": "python3.12",
                    "install_extras": "browser",
                    "default_retry": 3,
                    "default_timeout": 300,
                    "research_mode_default": "deep",
                    "auth_precedence_policy": [
                        "--storage",
                        "NOTEBOOKLM_AUTH_JSON",
                        "NOTEBOOKLM_HOME/storage_state.json",
                    ],
                }
            ),
        )

    def test_missing_config_returns_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            report = notebooklm_doctor.run_notebooklm_doctor(Path(td))
            self.assertEqual(report["status"], "fail")
            self.assertFalse(report["checks"]["config"]["ok"])

    def test_happy_path_minimal(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._build_config(root)

            def fake_run(cmd: list[str], timeout: int = 30):
                joined = " ".join(cmd)
                if joined == "notebooklm --version":
                    return {"cmd": cmd, "code": 0, "stdout": "notebooklm, version 0.3.3\n", "stderr": ""}
                if joined == "notebooklm status --paths":
                    return {"cmd": cmd, "code": 0, "stdout": "paths", "stderr": ""}
                if joined == "notebooklm auth check --json":
                    return {"cmd": cmd, "code": 0, "stdout": '{"ok": true}', "stderr": ""}
                if cmd[:3] == ["python3.12", "-c", cmd[2]]:
                    return {"cmd": cmd, "code": 0, "stdout": "ok\n", "stderr": ""}
                return {"cmd": cmd, "code": 0, "stdout": "", "stderr": ""}

            env_auth = json.dumps({"cookies": [{"name": "SID"}]})
            with patch.object(notebooklm_doctor.shutil, "which", side_effect=lambda x: f"/usr/bin/{x}"), patch.object(
                notebooklm_doctor, "_run", side_effect=fake_run
            ), patch.dict(os.environ, {"NOTEBOOKLM_AUTH_JSON": env_auth}, clear=False):
                report = notebooklm_doctor.run_notebooklm_doctor(root)

            self.assertEqual(report["status"], "pass")
            self.assertTrue(report["binary_ok"])
            self.assertTrue(report["version_ok"])
            self.assertTrue(report["auth_ok"])
            self.assertTrue(report["paths_ok"])

    def test_invalid_env_auth_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._build_config(root)

            with patch.object(notebooklm_doctor.shutil, "which", side_effect=lambda x: f"/usr/bin/{x}"), patch.object(
                notebooklm_doctor,
                "_run",
                side_effect=lambda cmd, timeout=30: {"cmd": cmd, "code": 0, "stdout": '{"ok": true}', "stderr": ""},
            ), patch.dict(os.environ, {"NOTEBOOKLM_AUTH_JSON": "{"}, clear=False):
                report = notebooklm_doctor.run_notebooklm_doctor(root)

            self.assertFalse(report["checks"]["auth_source"]["valid"])
            self.assertEqual(report["checks"]["auth_source"]["source"], "NOTEBOOKLM_AUTH_JSON")


if __name__ == "__main__":
    unittest.main()
