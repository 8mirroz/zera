from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.swarm import BranchLockRequest, LaneEvent, detect_branch_lock_collisions, read_lane_events, write_lane_event


class TestSwarmContracts(unittest.TestCase):
    def test_lane_event_round_trip_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "events.jsonl"
            event = LaneEvent(task_id="task-1", lane_id="lane-a", event_type="Started", payload={"branch": "feat/a"})

            write_lane_event(path, event)

            events = read_lane_events(path)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_type, "Started")
            self.assertEqual(events[0].payload["branch"], "feat/a")

    def test_branch_lock_detects_same_branch_scope_collision(self) -> None:
        collisions = detect_branch_lock_collisions(
            [
                BranchLockRequest(lane_id="lane-a", branch="feat/a", scope="repos/packages/agent-os"),
                BranchLockRequest(lane_id="lane-b", branch="feat/a", scope="repos/packages/agent-os/src"),
                BranchLockRequest(lane_id="lane-c", branch="feat/c", scope="templates"),
            ]
        )

        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0].lane_ids, ("lane-a", "lane-b"))
        self.assertEqual(collisions[0].reason, "nested_scope_same_branch")


if __name__ == "__main__":
    unittest.main()
