from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.recovery import RecoveryState, RecoveryStateMachine


class TestRecoveryStateMachine(unittest.TestCase):
    def test_allows_nominal_execution_trace(self) -> None:
        machine = RecoveryStateMachine(run_id="run-1")

        machine.transition(RecoveryState.SPAWNING, reason="provider selected")
        machine.transition(RecoveryState.PREFLIGHT, reason="preflight checks")
        machine.transition(RecoveryState.RUNNING, reason="provider started")
        machine.transition(RecoveryState.VERIFYING, reason="provider completed")
        machine.transition(RecoveryState.DONE, reason="verification passed")

        self.assertEqual(machine.current, RecoveryState.DONE)
        self.assertEqual([row["to"] for row in machine.trace], ["SPAWNING", "PREFLIGHT", "RUNNING", "VERIFYING", "DONE"])

    def test_allows_recovery_to_degraded_trace(self) -> None:
        machine = RecoveryStateMachine(run_id="run-2")

        machine.transition(RecoveryState.SPAWNING, reason="provider selected")
        machine.transition(RecoveryState.PREFLIGHT, reason="preflight checks")
        machine.transition(RecoveryState.RUNNING, reason="provider started")
        machine.transition(RecoveryState.RECOVERY_IN_PROGRESS, reason="stdio json failure")
        machine.transition(RecoveryState.DEGRADED, reason="fallback available")
        machine.transition(RecoveryState.RUNNING, reason="fallback running")
        machine.transition(RecoveryState.DONE, reason="fallback completed")

        self.assertEqual(machine.current, RecoveryState.DONE)
        self.assertEqual(machine.trace[3]["to"], "RECOVERY_IN_PROGRESS")
        self.assertEqual(machine.trace[4]["to"], "DEGRADED")

    def test_rejects_illegal_transition(self) -> None:
        machine = RecoveryStateMachine(run_id="run-3")

        with self.assertRaisesRegex(ValueError, "Illegal recovery state transition"):
            machine.transition(RecoveryState.DONE, reason="cannot skip lifecycle")


if __name__ == "__main__":
    unittest.main()
