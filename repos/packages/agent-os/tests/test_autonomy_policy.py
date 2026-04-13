from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.autonomy_policy import AutonomyPolicyEngine


class TestAutonomyPolicyEngine(unittest.TestCase):
    def test_evaluate_returns_approval_for_delayed_actions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            config = repo / "configs/tooling/autonomy_policy.yaml"
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(
                "\n".join(
                    [
                        "policy_name: \"test\"",
                        "default_action_class: allowed_with_delayed_approval",
                        "action_classes:",
                        "  allowed_with_delayed_approval:",
                        "    blocked: false",
                        "    requires_approval: true",
                        "action_type_map:",
                        "  research_refresh: allowed_with_delayed_approval",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            decision = AutonomyPolicyEngine(repo).evaluate("research_refresh")
            self.assertTrue(decision.allowed)
            self.assertTrue(decision.requires_approval)
            self.assertFalse(decision.blocked)


if __name__ == "__main__":
    unittest.main()
