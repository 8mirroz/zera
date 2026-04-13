from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.approval_engine import ApprovalEngine


class TestApprovalEngine(unittest.TestCase):
    def test_create_and_resolve_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            engine = ApprovalEngine(repo)
            ticket = engine.create_ticket(
                action_type="external_contact",
                risk_class="external",
                summary="Contact a vendor",
                run_id="run-1",
                runtime_provider="zeroclaw",
                persona_id="zera-v1",
                approval_policy="zera-standard",
                proposal={"title": "Contact a vendor"},
            )
            self.assertEqual(ticket.status, "pending")
            again = engine.create_ticket(
                action_type="external_contact",
                risk_class="external",
                summary="Contact a vendor",
                run_id="run-1",
                runtime_provider="zeroclaw",
                persona_id="zera-v1",
                approval_policy="zera-standard",
                proposal={"title": "Contact a vendor"},
            )
            self.assertEqual(ticket.id, again.id)
            resolved = engine.resolve(ticket.id, resolution="approve", resolved_by="admin")
            self.assertIsNotNone(resolved)
            self.assertEqual(resolved.status, "approved")


if __name__ == "__main__":
    unittest.main()
