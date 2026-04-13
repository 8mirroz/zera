from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.security_policy import SecurityPolicy


class TestSecurityPolicyRuntime(unittest.TestCase):
    def test_rejects_unsafe_zeroclaw_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            policy = SecurityPolicy(repo)
            decision = policy.validate_runtime_profile(
                "zera-edge-local",
                {"channel": "edge", "execution_mode": "stdio_json"},
                provider_name="zeroclaw",
            )
            self.assertFalse(decision.allowed)
            self.assertGreaterEqual(len(decision.issues), 3)

    def test_accepts_profile_with_allowlist_scope_and_network(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            cfg = repo / "configs/tooling"
            cfg.mkdir(parents=True, exist_ok=True)
            (cfg / "tool_execution_policy.yaml").write_text(
                "\n".join(
                    [
                        "allowed_tools:",
                        "  memory_read: read_only",
                        "  goal_stack: workspace_only",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (cfg / "network_policy.yaml").write_text(
                "\n".join(
                    [
                        "policies:",
                        "  local-dev-restricted:",
                        "    mode: allowlist",
                        "    allow_hosts:",
                        "      - localhost",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            policy = SecurityPolicy(repo)
            decision = policy.validate_runtime_profile(
                "zera-edge-local",
                {
                    "channel": "edge",
                    "execution_mode": "stdio_json",
                    "workspace_scope": "workspace_only",
                    "tool_allowlist": ["memory_read", "goal_stack"],
                    "network_policy": "local-dev-restricted",
                    "budget_profile": "zera-standard",
                },
                provider_name="zeroclaw",
            )
            self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
