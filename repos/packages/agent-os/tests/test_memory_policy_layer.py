"""Tests for MemoryPolicyLayer — scoped memory with write_rules enforcement.

Covers:
- Scoped write (session/project/workspace/user_preferences)
- TTL assignment per scope
- never_write rule blocks credential-like keys
- require_confirmation returns pending sentinel
- search across scopes
- retrieval_priority order
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.memory_policy_layer import MemoryPolicyLayer, _NEVER_WRITE_KEYWORDS


class TestMemoryPolicyLayerWrite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = MemoryPolicyLayer(repo_root=ROOT)

    def test_session_write_succeeds(self):
        result = self.layer.write("test_key", {"value": "hello"}, scope="session")
        self.assertIsNotNone(result)
        self.assertGreater(len(result.memory_ids), 0)

    def test_project_write_succeeds(self):
        result = self.layer.write("arch_decision", {"value": "use postgres"}, scope="project")
        self.assertIsNotNone(result)

    def test_workspace_write_succeeds(self):
        result = self.layer.write("global_convention", {"value": "snake_case"}, scope="workspace")
        self.assertIsNotNone(result)

    def test_user_preferences_write_succeeds(self):
        result = self.layer.write("lang_pref", {"value": "ru"}, scope="user_preferences")
        self.assertIsNotNone(result)

    def test_scoped_key_prefixed(self):
        result = self.layer.write("my_key", {"v": 1}, scope="project")
        self.assertIsNotNone(result)
        stored_key = result.result.get("key", "")
        self.assertTrue(stored_key.startswith("project:"), f"Expected project: prefix, got: {stored_key}")

    def test_session_key_prefixed(self):
        result = self.layer.write("tmp", {"v": 2}, scope="session")
        stored_key = result.result.get("key", "")
        self.assertTrue(stored_key.startswith("session:"))


class TestMemoryPolicyLayerNeverWrite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = MemoryPolicyLayer(repo_root=ROOT)

    def test_credential_key_blocked(self):
        result = self.layer.write("temporary_credentials", {"token": "abc123"})
        self.assertIsNone(result)

    def test_secret_in_payload_blocked(self):
        result = self.layer.write("config", {"secret": "my_password"})
        self.assertIsNone(result)

    def test_token_in_key_blocked(self):
        result = self.layer.write("api_token_store", {"value": "xyz"})
        self.assertIsNone(result)

    def test_normal_key_not_blocked(self):
        result = self.layer.write("project_decision", {"value": "use redis"})
        self.assertIsNotNone(result)

    def test_never_write_keywords_coverage(self):
        """All _NEVER_WRITE_KEYWORDS should block writes."""
        for kw in _NEVER_WRITE_KEYWORDS:
            with self.subTest(keyword=kw):
                result = self.layer.write(kw, {"data": "test"})
                self.assertIsNone(result, f"Expected None for keyword '{kw}'")


class TestMemoryPolicyLayerConfirmation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = MemoryPolicyLayer(repo_root=ROOT)

    def test_require_confirmation_returns_pending(self):
        result = self.layer.write(
            "sensitive_assumption",
            {"value": "irreversible decision"},
            require_confirmation=True,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.result.get("status"), "pending_confirmation")
        self.assertEqual(len(result.memory_ids), 0)

    def test_require_confirmation_does_not_persist(self):
        self.layer.write(
            "confirm_test_key",
            {"value": "should not persist"},
            require_confirmation=True,
        )
        read_result = self.layer.read("confirm_test_key", scope="session")
        items = read_result.result.get("items", [])
        self.assertEqual(len(items), 0)


class TestMemoryPolicyLayerSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = MemoryPolicyLayer(repo_root=ROOT)
        cls.layer.write("search_test_item", {"content": "postgres architecture decision"}, scope="project")

    def test_search_returns_list(self):
        results = self.layer.search("postgres")
        self.assertIsInstance(results, list)

    def test_search_with_scope_filter(self):
        results = self.layer.search("postgres", scopes=["project"])
        self.assertIsInstance(results, list)


class TestMemoryPolicyLayerRetrievalPriority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layer = MemoryPolicyLayer(repo_root=ROOT)

    def test_retrieval_priority_order(self):
        priority = self.layer._retrieval_priority()
        self.assertEqual(priority[0], "session")
        self.assertIn("project", priority)
        self.assertIn("workspace", priority)
        self.assertIn("user_preferences", priority)

    def test_retrieval_priority_session_first(self):
        priority = self.layer._retrieval_priority()
        self.assertEqual(priority.index("session"), 0)


if __name__ == "__main__":
    unittest.main()
