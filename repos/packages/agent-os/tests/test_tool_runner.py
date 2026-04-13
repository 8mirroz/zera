from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.contracts import ToolInput
from agent_os.tool_runner import ToolRunner


class TestToolRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = ToolRunner(default_timeout_seconds=5, test_timeout_seconds=10)

    def test_read_tool_success(self) -> None:
        out = self.runner.run(ToolInput(tool_name="echo", args=["ok"], mode="read", correlation_id="t1"))
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.exit_code, 0)

    def test_read_mode_retries_once(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / "marker"
            script = f'if [ -f "{marker}" ]; then exit 0; else touch "{marker}"; exit 1; fi'
            out = self.runner.run(ToolInput(tool_name="sh", args=["-c", script], mode="read", correlation_id="t2"))
            self.assertEqual(out.exit_code, 0)

    def test_write_mode_no_retry(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            counter = Path(td) / "counter"
            script = (
                f'n=$(cat "{counter}" 2>/dev/null || echo 0); '
                f'n=$((n+1)); echo "$n" > "{counter}"; exit 1'
            )
            out = self.runner.run(ToolInput(tool_name="sh", args=["-c", script], mode="write", correlation_id="t3"))
            self.assertEqual(out.status, "error")
            self.assertEqual(counter.read_text(encoding="utf-8").strip(), "1")


if __name__ == "__main__":
    unittest.main()
