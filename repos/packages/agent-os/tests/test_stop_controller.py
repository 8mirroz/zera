from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.stop_controller import StopController


class TestStopController(unittest.TestCase):
    def test_signal_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            controller = StopController(repo)
            signal = controller.signal(scope="global", minutes=15)
            self.assertTrue(controller.is_stopped(scope="global"))
            self.assertEqual(signal.scope, "global")
            controller.clear(scope="global")
            self.assertFalse(controller.is_stopped(scope="global"))


if __name__ == "__main__":
    unittest.main()
