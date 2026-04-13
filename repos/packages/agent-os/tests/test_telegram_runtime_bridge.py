from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BOT_DIR = ROOT / "sandbox/template-telegram/bot"
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

import runtime_bridge


class TestTelegramRuntimeBridge(unittest.TestCase):
    def test_allowed_chat_ids_parsing_and_gate(self) -> None:
        prev = os.environ.get("TG_ALLOWED_CHAT_IDS")
        os.environ["TG_ALLOWED_CHAT_IDS"] = "1, 2, invalid"
        try:
            self.assertEqual(runtime_bridge.allowed_chat_ids(), {1, 2})
            self.assertTrue(runtime_bridge.is_chat_allowed(1))
            self.assertFalse(runtime_bridge.is_chat_allowed(3))
        finally:
            if prev is None:
                os.environ.pop("TG_ALLOWED_CHAT_IDS", None)
            else:
                os.environ["TG_ALLOWED_CHAT_IDS"] = prev

    def test_admin_chat_ids_fall_back_to_allowlist(self) -> None:
        prev_allow = os.environ.get("TG_ALLOWED_CHAT_IDS")
        prev_admin = os.environ.get("TG_ADMIN_CHAT_IDS")
        os.environ["TG_ALLOWED_CHAT_IDS"] = "5"
        os.environ.pop("TG_ADMIN_CHAT_IDS", None)
        try:
            self.assertEqual(runtime_bridge.admin_chat_ids(), {5})
            self.assertTrue(runtime_bridge.is_admin_chat(5))
            self.assertFalse(runtime_bridge.is_admin_chat(6))
        finally:
            if prev_allow is None:
                os.environ.pop("TG_ALLOWED_CHAT_IDS", None)
            else:
                os.environ["TG_ALLOWED_CHAT_IDS"] = prev_allow
            if prev_admin is None:
                os.environ.pop("TG_ADMIN_CHAT_IDS", None)
            else:
                os.environ["TG_ADMIN_CHAT_IDS"] = prev_admin

    def test_response_chunks_splits_long_text(self) -> None:
        text = ("hello " * 1000).strip()
        chunks = runtime_bridge.response_chunks(text, limit=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 500 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
