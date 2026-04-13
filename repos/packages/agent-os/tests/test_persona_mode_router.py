from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.persona_mode_router import PersonaModeRouter


class TestPersonaModeRouter(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_selects_mode_from_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            self._write_json(
                repo / "configs/tooling/zera_mode_router.json",
                {
                    "default_mode": "plan",
                    "rules": [
                        {"mode": "analysis", "keywords": ["analyze", "why"]},
                        {"mode": "love", "keywords": ["support me"]},
                    ],
                },
            )
            router = PersonaModeRouter(repo)
            self.assertEqual(router.select_mode("please analyze this"), "analysis")
            self.assertEqual(router.select_mode("support me now"), "love")
            self.assertEqual(router.select_mode("something else"), "plan")


if __name__ == "__main__":
    unittest.main()

