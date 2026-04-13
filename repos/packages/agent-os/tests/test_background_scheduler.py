from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.background_scheduler import BackgroundJobQueue


class TestBackgroundScheduler(unittest.TestCase):
    def test_enqueue_dedupes_and_claims_due_items(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            queue = BackgroundJobQueue(repo)
            item_one, created_one = queue.enqueue(
                job_type="goal_review",
                objective="review goals",
                runtime_provider="zeroclaw",
                runtime_profile="zera-edge-local",
                persona_id="zera-v1",
                scheduler_profile="local-dev",
                idempotency_key="zera-v1:goal_review:plan",
            )
            item_two, created_two = queue.enqueue(
                job_type="goal_review",
                objective="review goals",
                runtime_provider="zeroclaw",
                runtime_profile="zera-edge-local",
                persona_id="zera-v1",
                scheduler_profile="local-dev",
                idempotency_key="zera-v1:goal_review:plan",
            )
            claimed = queue.claim_due(limit=5)
            self.assertTrue(created_one)
            self.assertFalse(created_two)
            self.assertEqual(item_one.id, item_two.id)
            self.assertEqual(len(claimed), 1)
            queue.mark_completed(claimed[0], result={"status": "completed"})
            self.assertEqual(len(queue.queued_items()), 0)

    def test_pause_and_resume_background_processing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            queue = BackgroundJobQueue(repo)
            paused = queue.pause_for(minutes=5)
            self.assertTrue(queue.is_paused())
            self.assertTrue(paused.get("paused_until"))
            resumed = queue.resume()
            self.assertFalse(queue.is_paused())
            self.assertIsNone(resumed.get("paused_until"))

    def test_failed_job_moves_to_dead_letter_after_max_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            queue = BackgroundJobQueue(repo)
            item, _ = queue.enqueue(
                job_type="goal_review",
                objective="review goals",
                runtime_provider="zeroclaw",
                runtime_profile="zera-edge-local",
                persona_id="zera-v1",
                scheduler_profile="local-dev",
                idempotency_key="zera-v1:goal_review:dead",
                max_attempts=1,
            )
            claimed = queue.claim_due(limit=1)
            self.assertEqual(len(claimed), 1)
            queue.mark_failed(claimed[0], error="boom")
            payload = queue._load()
            self.assertEqual(len(payload["failed"]), 1)
            self.assertEqual(payload["failed"][0]["dead_letter_reason"], "boom")


if __name__ == "__main__":
    unittest.main()
