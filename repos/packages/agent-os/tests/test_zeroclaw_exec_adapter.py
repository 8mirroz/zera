from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import zeroclaw_exec_adapter


class TestZeroClawExecAdapter(unittest.TestCase):
    def test_worker_maintenance_adds_harness_gardening_for_critical_routes(self) -> None:
        payload = {
            "run_id": "run-maint-critical",
            "objective": "refresh routing and observability hardening",
            "route_decision": {
                "task_type": "T4",
                "complexity": "C4",
                "selected_mode": "analysis",
                "persona_id": "agent-os",
                "background_profile": "worker-maintenance",
                "scheduler_profile": "local-dev",
            },
        }

        response = zeroclaw_exec_adapter.build_response(payload, profile="worker-maint-local")
        jobs = response["meta"]["background_jobs"]

        self.assertIn("memory_consolidation", jobs)
        self.assertIn("pending_task_follow_up", jobs)
        self.assertIn("harness_gardening", jobs)

    def test_worker_maintenance_skips_harness_gardening_for_simple_routes(self) -> None:
        payload = {
            "run_id": "run-maint-simple",
            "objective": "follow up on pending small maintenance task",
            "route_decision": {
                "task_type": "T2",
                "complexity": "C2",
                "selected_mode": "plan",
                "persona_id": "agent-os",
                "background_profile": "worker-maintenance",
                "scheduler_profile": "local-dev",
            },
        }

        response = zeroclaw_exec_adapter.build_response(payload, profile="worker-maint-local")
        jobs = response["meta"]["background_jobs"]

        self.assertIn("memory_consolidation", jobs)
        self.assertIn("pending_task_follow_up", jobs)
        self.assertNotIn("harness_gardening", jobs)


if __name__ == "__main__":
    unittest.main()
