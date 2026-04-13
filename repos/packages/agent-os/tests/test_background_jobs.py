from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.background_jobs import BackgroundJobRegistry


class TestBackgroundJobRegistry(unittest.TestCase):
    def test_materialize_returns_job_with_scheduler_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            path = repo / "configs/tooling/background_jobs.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "scheduler_profiles:",
                        "  local-dev:",
                        "    cadence_policy: debug",
                        "jobs:",
                        "  goal_review:",
                        "    cadence_minutes: 60",
                        "    retry_limit: 1",
                        "    concurrency_limit: 1",
                        "    quiet_hours: \"00:00-00:00\"",
                        "    stop_condition: done",
                        "    escalation_rule: none",
                        "    user_suppressible: true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            rows = BackgroundJobRegistry(repo).materialize(["goal_review"], scheduler_profile="local-dev")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["job_type"], "goal_review")
            self.assertEqual(rows[0]["scheduler_profile"], "local-dev")

    def test_materialize_skips_missing_job_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            path = repo / "configs/tooling/background_jobs.yaml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        "scheduler_profiles:",
                        "  local-dev:",
                        "    cadence_policy: debug",
                        "jobs:",
                        "  goal_review:",
                        "    cadence_minutes: 60",
                        "    retry_limit: 1",
                        "    concurrency_limit: 1",
                        "    quiet_hours: \"00:00-00:00\"",
                        "    stop_condition: done",
                        "    escalation_rule: none",
                        "    user_suppressible: true",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            rows = BackgroundJobRegistry(repo).materialize(
                ["goal_review", "missing_job"],
                scheduler_profile="local-dev",
            )
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["job_type"], "goal_review")


if __name__ == "__main__":
    unittest.main()
