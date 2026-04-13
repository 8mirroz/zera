"""Tests for GoalStack — push/pop/complete/cancel/pending_count."""
from __future__ import annotations

from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_os.goal_stack import GoalStack, GoalEntry


class TestGoalStackBasic:
    def test_push_creates_queued_goal(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        goal = gs.push("Implement feature X", "implement")
        assert goal.status == "queued"
        assert goal.title == "Implement feature X"
        assert goal.action_type == "implement"
        assert goal.id

    def test_list_returns_all_goals(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        gs.push("Goal A", "research")
        gs.push("Goal B", "implement")
        assert len(gs.list()) == 2

    def test_persistence_across_instances(self, tmp_path):
        path = tmp_path / "goals.json"
        gs1 = GoalStack(tmp_path, storage_path=path)
        gs1.push("Persistent goal", "implement", metadata={"priority": "high"})

        gs2 = GoalStack(tmp_path, storage_path=path)
        goals = gs2.list()
        assert len(goals) == 1
        assert goals[0].title == "Persistent goal"
        assert goals[0].metadata["priority"] == "high"


class TestGoalStackPop:
    def test_pop_returns_first_queued(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        gs.push("First", "implement")
        gs.push("Second", "research")
        popped = gs.pop()
        assert popped is not None
        assert popped.title == "First"
        assert len(gs.list()) == 1

    def test_pop_empty_returns_none(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        assert gs.pop() is None

    def test_pop_skips_non_queued(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        goal = gs.push("Done goal", "implement")
        gs.complete(goal.id)
        result = gs.pop()
        assert result is None

    def test_pop_respects_priority(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        gs.push("Low", "implement", priority=0)
        gs.push("High", "implement", priority=10)
        gs.push("Medium", "implement", priority=5)
        popped = gs.pop()
        assert popped is not None
        assert popped.title == "High"

    def test_pop_blocks_on_unmet_dependency(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        blocker = gs.push("Blocker", "research")
        gs.push("Dependent", "implement", depends_on=[blocker.id])
        # Only blocker is eligible
        popped = gs.pop()
        assert popped is not None
        assert popped.title == "Blocker"

    def test_pop_unblocks_after_dependency_completed(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        blocker = gs.push("Blocker", "research")
        gs.push("Dependent", "implement", depends_on=[blocker.id])
        gs.complete(blocker.id)
        popped = gs.pop()
        assert popped is not None
        assert popped.title == "Dependent"

    def test_peek_does_not_remove(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        gs.push("Task", "implement")
        peeked = gs.peek()
        assert peeked is not None
        assert gs.pending_count() == 1


class TestGoalStackLifecycle:
    def test_complete_sets_status(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        goal = gs.push("Task", "implement")
        result = gs.complete(goal.id)
        assert result is True
        assert gs.list()[0].status == "completed"

    def test_cancel_sets_status(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        goal = gs.push("Task", "implement")
        result = gs.cancel(goal.id)
        assert result is True
        assert gs.list()[0].status == "cancelled"

    def test_complete_unknown_id_returns_false(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        assert gs.complete("nonexistent-id") is False

    def test_pending_count(self, tmp_path):
        gs = GoalStack(tmp_path, storage_path=tmp_path / "goals.json")
        g1 = gs.push("A", "implement")
        g2 = gs.push("B", "research")
        gs.push("C", "fix")
        gs.complete(g1.id)
        gs.cancel(g2.id)
        assert gs.pending_count() == 1

    def test_status_persists_after_reload(self, tmp_path):
        path = tmp_path / "goals.json"
        gs1 = GoalStack(tmp_path, storage_path=path)
        goal = gs1.push("Task", "implement")
        gs1.complete(goal.id)

        gs2 = GoalStack(tmp_path, storage_path=path)
        assert gs2.list()[0].status == "completed"
