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


class TestSwarmctlTelegramReadiness(unittest.TestCase):
    def _run(self, *, repo_root: Path, mode: str) -> tuple[int, dict]:
        prev_repo = os.environ.get("AGENT_OS_REPO_ROOT")
        os.environ["AGENT_OS_REPO_ROOT"] = str(repo_root)
        prev_stdout = sys.stdout
        capture = StringIO()
        sys.stdout = capture
        try:
            code = swarmctl.cmd_telegram_readiness(type("Args", (), {"mode": mode})())
        finally:
            sys.stdout = prev_stdout
            if prev_repo is None:
                os.environ.pop("AGENT_OS_REPO_ROOT", None)
            else:
                os.environ["AGENT_OS_REPO_ROOT"] = prev_repo
        return code, json.loads(capture.getvalue())

    def test_readiness_webhook_detects_missing_required_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / ".env").write_text("TG_BOT_MODE=webhook\n", encoding="utf-8")
            code, payload = self._run(repo_root=repo, mode="webhook")
            self.assertEqual(code, 2)
            self.assertFalse(payload["ready"])
            keys = {item["key"] for item in payload["checks"]}
            self.assertIn("TG_WEBHOOK_URL", keys)
            self.assertIn("TG_WEBHOOK_SECRET", keys)

    def test_readiness_polling_passes_when_keys_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / ".env").write_text(
                "\n".join(
                    [
                        "ZERA_BOT_TOKEN=***",
                        "TG_ALLOWED_CHAT_IDS=1",
                        "TG_ADMIN_CHAT_IDS=1",
                        "AG_RUNTIME_PROVIDER=zeroclaw",
                        "AG_RUNTIME_PROFILE=zera-telegram-prod",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            code, payload = self._run(repo_root=repo, mode="polling")
            self.assertEqual(code, 0)
            self.assertTrue(payload["ready"])


if __name__ == "__main__":
    unittest.main()
