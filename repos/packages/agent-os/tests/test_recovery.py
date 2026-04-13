from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.recovery import FailureType, classify_failure, plan_recovery


class TestRecovery(unittest.TestCase):
    def test_classifies_initial_failure_types(self) -> None:
        cases = {
            "provider startup timed out": FailureType.PROVIDER_STARTUP,
            "stdio command returned non-JSON output": FailureType.STDIO_JSON_FAILURE,
            "MCP initialize handshake failed": FailureType.MCP_HANDSHAKE,
            "branch is stale against main": FailureType.STALE_BRANCH,
            "compile error in module": FailureType.COMPILE_FAILURE,
            "pytest failed": FailureType.TEST_FAILURE,
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(classify_failure(message), expected)

    def test_plan_recovery_returns_structured_event_payload(self) -> None:
        result = plan_recovery(
            FailureType.MCP_HANDSHAKE,
            run_id="run-1",
            runtime_provider="claw_code",
            message="MCP initialize handshake failed",
        )

        self.assertTrue(result.attempted)
        self.assertFalse(result.recovered)
        self.assertTrue(result.degraded_mode)
        self.assertEqual(result.failure_type, FailureType.MCP_HANDSHAKE)
        self.assertIn("degraded", result.next_action)
        self.assertEqual(result.event_payload["run_id"], "run-1")
        self.assertEqual(result.event_payload["data"]["failure_type"], "mcp_handshake")
        self.assertTrue(result.event_payload["data"]["degraded_mode"])


if __name__ == "__main__":
    unittest.main()
