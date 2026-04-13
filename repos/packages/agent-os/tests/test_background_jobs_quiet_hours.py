from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.background_jobs import BackgroundJobRegistry


class TestBackgroundJobsQuietHours(unittest.TestCase):
    def test_in_quiet_hours_handles_wraparound_window(self) -> None:
        now = datetime(2026, 3, 11, 23, 30, tzinfo=timezone.utc)
        self.assertTrue(BackgroundJobRegistry.in_quiet_hours("23:00-08:00", now=now))

    def test_next_allowed_time_returns_end_of_window(self) -> None:
        now = datetime(2026, 3, 11, 23, 30, tzinfo=timezone.utc)
        out = BackgroundJobRegistry.next_allowed_time("23:00-08:00", now=now)
        self.assertEqual(out.hour, 8)
        self.assertEqual(out.minute, 0)


if __name__ == "__main__":
    unittest.main()
