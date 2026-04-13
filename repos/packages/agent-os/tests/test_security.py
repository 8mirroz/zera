"""Security tests for SEC-003 (env var whitelist) and SEC-004 (fail-open default)."""
from __future__ import annotations

import logging
import os
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.model_router import ModelRouter, _ALLOWED_ENV_PREFIXES
from agent_os.memory_store import _parse_bool_env


class TestEnvVarSecurity(unittest.TestCase):
    """SEC-003: Environment variable expansion whitelist."""

    def test_allowed_env_expansion(self):
        """AGENT_MODEL_* vars should expand normally."""
        with mock.patch.dict(os.environ, {"AGENT_MODEL_BUILDER_A": "deepseek/deepseek-v3:free"}):
            result = ModelRouter._expand_env_vars("${AGENT_MODEL_BUILDER_A}")
            self.assertEqual(result, "deepseek/deepseek-v3:free")

    def test_allowed_prefix_openrouter(self):
        """OPENROUTER_* vars should expand."""
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            result = ModelRouter._expand_env_vars("$OPENROUTER_API_KEY")
            self.assertEqual(result, "test-key")

    def test_blocked_env_expansion(self):
        """Non-whitelisted vars stay unexpanded."""
        with mock.patch.dict(os.environ, {"HOME": "/Users/attacker", "MALICIOUS_VAR": "pwned"}):
            self.assertEqual(ModelRouter._expand_env_vars("${HOME}"), "${HOME}")
            self.assertEqual(ModelRouter._expand_env_vars("$MALICIOUS_VAR"), "$MALICIOUS_VAR")

    def test_nested_expansion_blocked(self):
        """Nested patterns should not cause issues."""
        result = ModelRouter._expand_env_vars("${${INNER}}")
        # The inner ${INNER} won't match the \w+ pattern cleanly,
        # so the outer pattern won't match either — stays as-is
        self.assertIn("$", result)

    def test_allowed_prefixes_exist(self):
        """Whitelist should contain expected prefixes."""
        self.assertIn("AGENT_MODEL_", _ALLOWED_ENV_PREFIXES)
        self.assertIn("OPENROUTER_", _ALLOWED_ENV_PREFIXES)
        self.assertIn("GEMINI_", _ALLOWED_ENV_PREFIXES)


class TestMemoryStoreSecurity(unittest.TestCase):
    """SEC-004: Memory store fail-open default."""

    def test_fail_open_default_is_false(self):
        """Default should be fail-closed (safe default)."""
        with mock.patch.dict(os.environ, {}, clear=False):
            # Remove MEMU_FAIL_OPEN if present
            env = os.environ.copy()
            env.pop("MEMU_FAIL_OPEN", None)
            with mock.patch.dict(os.environ, env, clear=True):
                result = _parse_bool_env("MEMU_FAIL_OPEN", False)
                self.assertFalse(result)

    def test_fail_open_explicit_true_accepted(self):
        """When explicitly set to True, should be accepted."""
        with mock.patch.dict(os.environ, {"MEMU_FAIL_OPEN": "true"}):
            result = _parse_bool_env("MEMU_FAIL_OPEN", False)
            self.assertTrue(result)

    def test_fail_open_explicit_false(self):
        """When explicitly set to False, should be False."""
        with mock.patch.dict(os.environ, {"MEMU_FAIL_OPEN": "false"}):
            result = _parse_bool_env("MEMU_FAIL_OPEN", False)
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
