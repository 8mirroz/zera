from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.background_job_planner import build_background_objective, select_background_jobs


class TestBackgroundJobPlanner(unittest.TestCase):
    def test_select_background_jobs_adds_harness_gardening_for_worker_maintenance_c4(self) -> None:
        jobs = select_background_jobs(
            "worker-maintenance",
            "analysis",
            {"task_type": "T4", "complexity": "C4"},
        )
        self.assertEqual(jobs, ["memory_consolidation", "pending_task_follow_up", "harness_gardening"])

    def test_select_background_jobs_keeps_companion_behavior(self) -> None:
        jobs = select_background_jobs(
            "zera-companion",
            "plan",
            {"task_type": "T7", "complexity": "C2"},
        )
        self.assertEqual(jobs, ["goal_review", "memory_consolidation", "self_reflection", "rhythm_check_in"])

    def test_build_background_objective_returns_harness_specific_text(self) -> None:
        objective = build_background_objective(
            "harness_gardening",
            route_decision={"persona_id": "agent-os"},
            selected_mode="analysis",
        )
        self.assertIn("read-only harness gardening sweep", objective)
        self.assertIn("agent-os", objective)


if __name__ == "__main__":
    unittest.main()
