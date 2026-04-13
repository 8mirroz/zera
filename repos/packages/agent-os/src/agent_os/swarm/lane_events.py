from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_LANE_EVENT_TYPES = {
    "Started",
    "Blocked",
    "Failed",
    "Finished",
    "ReadyForPrompt",
    "CollisionDetected",
}


@dataclass(frozen=True)
class LaneEvent:
    task_id: str
    lane_id: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.event_type not in ALLOWED_LANE_EVENT_TYPES:
            raise ValueError(f"Unsupported lane event type: {self.event_type}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_lane_event(path: Path, event: LaneEvent) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def read_lane_events(path: Path) -> list[LaneEvent]:
    if not path.exists():
        return []
    events: list[LaneEvent] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        events.append(
            LaneEvent(
                task_id=str(row["task_id"]),
                lane_id=str(row["lane_id"]),
                event_type=str(row["event_type"]),
                payload=dict(row.get("payload") or {}),
                ts=str(row["ts"]),
            )
        )
    return events
