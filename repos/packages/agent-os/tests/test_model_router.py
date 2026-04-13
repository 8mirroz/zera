from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.exceptions import BudgetExceededError
from agent_os.model_router import ModelRouter, UnifiedRouter


class TestModelRouter(unittest.TestCase):
    def setUp(self) -> None:
        self.router = ModelRouter(repo_root=ROOT)
        self.unified_router = UnifiedRouter(repo_root=ROOT)

    def test_routes_match_matrix(self) -> None:
        out = self.unified_router.route("T1", "C2")
        self.assertEqual(out["model_tier"], "worker")
        self.assertIn("primary_model", out)
        self.assertEqual(out["routing_source"], "v4")
        self.assertIn("orchestration_path", out)
        self.assertIn("telemetry", out)
        self.assertIn("max_total_tokens", out["telemetry"])

    def test_budget_guard_blocks_excess(self) -> None:
        with self.assertRaises(BudgetExceededError):
            self.unified_router.route("T3", context={"token_budget": 1, "cost_budget": 0.00001})

if __name__ == "__main__":
    unittest.main()
