from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class GoalEntry:
    id: str
    title: str
    action_type: str
    status: str
    created_at: str
    metadata: dict[str, Any]
    priority: int = 0          # higher = more urgent; default 0
    depends_on: list[str] = field(default_factory=list)  # ids of blocking goals
    deadline: str | None = None  # ISO 8601 or None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "action_type": self.action_type,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "deadline": self.deadline,
        }


class GoalStack:
    """Small persistent initiative queue for bounded autonomous actions."""

    def __init__(self, repo_root: Path, storage_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.storage_path = storage_path or (self.repo_root / ".agent/memory/goal-stack.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._goals = self._load()

    def _load(self) -> list[GoalEntry]:
        if not self.storage_path.exists():
            return []
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        rows = data.get("goals", []) if isinstance(data, dict) else []
        out: list[GoalEntry] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            out.append(
                GoalEntry(
                    id=str(row.get("id") or uuid4()),
                    title=str(row.get("title") or ""),
                    action_type=str(row.get("action_type") or "unknown"),
                    status=str(row.get("status") or "queued"),
                    created_at=str(row.get("created_at") or _utc_now_iso()),
                    metadata=dict(row.get("metadata") or {}),
                    priority=int(row.get("priority") or 0),
                    depends_on=list(row.get("depends_on") or []),
                    deadline=row.get("deadline"),
                )
            )
        return out

    def save(self) -> None:
        payload = {
            "updated_at": _utc_now_iso(),
            "goals": [goal.to_dict() for goal in self._goals],
        }
        self.storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def push(
        self,
        title: str,
        action_type: str,
        *,
        metadata: dict[str, Any] | None = None,
        priority: int = 0,
        depends_on: list[str] | None = None,
        deadline: str | None = None,
    ) -> GoalEntry:
        goal = GoalEntry(
            id=str(uuid4()),
            title=str(title).strip(),
            action_type=str(action_type).strip(),
            status="queued",
            created_at=_utc_now_iso(),
            metadata=dict(metadata or {}),
            priority=int(priority),
            depends_on=list(depends_on or []),
            deadline=deadline,
        )
        self._goals.append(goal)
        self.save()
        return goal

    def list(self) -> list[GoalEntry]:
        return list(self._goals)

    def pop(self) -> GoalEntry | None:
        """Remove and return the highest-priority queued goal whose dependencies are all completed."""
        completed_ids = {g.id for g in self._goals if g.status == "completed"}
        candidates = [
            (i, g) for i, g in enumerate(self._goals)
            if g.status == "queued" and all(dep in completed_ids for dep in g.depends_on)
        ]
        if not candidates:
            return None
        # Sort by priority desc, then created_at asc (FIFO within same priority)
        candidates.sort(key=lambda x: (-x[1].priority, x[1].created_at))
        idx, goal = candidates[0]
        self._goals.pop(idx)
        self.save()
        return goal

    def peek(self) -> GoalEntry | None:
        """Return next goal without removing it."""
        completed_ids = {g.id for g in self._goals if g.status == "completed"}
        candidates = [
            g for g in self._goals
            if g.status == "queued" and all(dep in completed_ids for dep in g.depends_on)
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x.priority, x.created_at))
        return candidates[0]

    def complete(self, goal_id: str) -> bool:
        """Mark a goal as completed. Returns True if found."""
        return self._set_status(goal_id, "completed")

    def cancel(self, goal_id: str) -> bool:
        """Mark a goal as cancelled. Returns True if found."""
        return self._set_status(goal_id, "cancelled")

    def _set_status(self, goal_id: str, status: str) -> bool:
        for goal in self._goals:
            if goal.id == goal_id:
                goal.status = status
                self.save()
                return True
        return False

    def pending_count(self) -> int:
        """Return number of queued goals."""
        return sum(1 for g in self._goals if g.status == "queued")

