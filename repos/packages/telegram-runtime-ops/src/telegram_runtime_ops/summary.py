from __future__ import annotations

from typing import Any


def summarize_jobs(status: dict[str, Any]) -> dict[str, int]:
    return {
        "queued": int(status.get("queued", 0) or 0),
        "failed": int(status.get("failed", 0) or 0),
        "completed": int(status.get("completed", 0) or 0),
    }


def summarize_approvals(tickets: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ticket in tickets:
        status = getattr(ticket, "status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts
