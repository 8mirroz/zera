#!/usr/bin/env python3
"""Standalone trace viewer for agent-os trace files.

Usage:
    python scripts/trace_viewer.py <task_id> [--json] [--tree] [--repo-root /path/to/repo] [--limit N]

Reads JSONL trace files from logs/agent_traces_*.jsonl, filters by task_id,
and displays results as a timeline, tree, or raw JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _resolve_repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    # Walk up from this script: scripts/ -> agent-os/ -> packages/ -> repos/ -> zera/
    script_dir = Path(__file__).resolve().parent
    candidate = script_dir.parents[3]
    return candidate.resolve()


def _format_trace_details(event: dict) -> str:
    """Extract a concise details string from a trace event."""
    parts = []
    if event.get("model"):
        parts.append(f"model={event['model']}")
    if event.get("tool_name"):
        parts.append(f"tool={event['tool_name']}")
    if event.get("span_id"):
        parts.append(f"span={event['span_id'][:8]}")
    if event.get("parent_span_id"):
        parts.append(f"parent={event['parent_span_id'][:8]}")
    if event.get("duration_ms") is not None:
        parts.append(f"duration={event['duration_ms']}ms")
    if event.get("tokens"):
        tokens = event["tokens"]
        if isinstance(tokens, dict):
            parts.append(f"tokens_in={tokens.get('input', '?')} tokens_out={tokens.get('output', '?')}")
        else:
            parts.append(f"tokens={tokens}")
    msg = event.get("message") or event.get("error") or event.get("detail")
    if msg:
        msg_str = str(msg)[:120]
        parts.append(msg_str)
    return ", ".join(parts) if parts else ""


def _print_trace_tree(events: list[dict]) -> None:
    """Print trace as a tree showing parent->child relationships."""
    by_parent: dict[str, list[dict]] = {}
    for ev in events:
        parent = ev.get("parent_span_id") or "root"
        by_parent.setdefault(parent, []).append(ev)

    def _render(parent_id: str, depth: int) -> None:
        children = by_parent.get(parent_id, [])
        for ev in sorted(children, key=lambda e: e.get("timestamp", "")):
            ts = ev.get("timestamp", "?")[:23]
            level = ev.get("level", "INFO")
            component = ev.get("component", ev.get("source", "?"))
            event_type = ev.get("event_type", ev.get("event", "?"))
            indent = "  " * depth
            prefix = f"[{ts}] [{level}] [{component}] {event_type}"
            details = _format_trace_details(ev)
            if details:
                print(f"{indent}{prefix} - {details}")
            else:
                print(f"{indent}{prefix}")
            span_id = ev.get("span_id", "")
            if span_id in by_parent:
                _render(span_id, depth + 1)

    _render("root", 0)
    # Also render any orphans (spans whose parent never appeared)
    all_span_ids = {ev.get("span_id") for ev in events}
    all_parent_ids = {ev.get("parent_span_id") for ev in events if ev.get("parent_span_id")}
    orphans = all_parent_ids - all_span_ids - {"root", None}
    for orphan_parent in sorted(orphans):
        if orphan_parent in by_parent:
            print(f"\n(orphan subtree, parent={orphan_parent[:8]})")
            _render(orphan_parent, 0)


def _print_trace_timeline(events: list[dict]) -> None:
    """Print trace as a chronological timeline."""
    sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))
    for ev in sorted_events:
        ts = ev.get("timestamp", "?")[:23]
        level = ev.get("level", "INFO")
        component = ev.get("component", ev.get("source", "?"))
        event_type = ev.get("event_type", ev.get("event", "?"))
        details = _format_trace_details(ev)
        if details:
            print(f"[{ts}] [{level}] [{component}] {event_type} - {details}")
        else:
            print(f"[{ts}] [{level}] [{component}] {event_type}")
    print(f"\n{len(sorted_events)} events total")


def collect_events(trace_dir: Path, task_id: str, limit: int) -> list[dict]:
    """Collect all trace events for a given task_id from JSONL files."""
    events: list[dict] = []
    for trace_file in sorted(trace_dir.glob("agent_traces_*.jsonl")):
        for line in trace_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if event.get("task_id") == task_id:
                    events.append(event)
                    if len(events) >= limit:
                        break
            except json.JSONDecodeError:
                continue
        if len(events) >= limit:
            break
    return events


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="trace_viewer",
        description="Display trace events for a task from agent-os trace files.",
    )
    parser.add_argument("task_id", help="Task ID to trace")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--tree", action="store_true", help="Show parent->child tree")
    parser.add_argument("--limit", type=int, default=1000, help="Max events to show (default: 1000)")
    parser.add_argument("--repo-root", default=None, help="Path to repo root (defaults to auto-detected)")
    args = parser.parse_args()

    repo_root = _resolve_repo_root(args.repo_root)
    trace_dir = repo_root / "logs"

    if not trace_dir.exists():
        print(f"Logs directory not found: {trace_dir}", file=sys.stderr)
        return 1

    events = collect_events(trace_dir, args.task_id, args.limit)

    if not events:
        print(f"No traces found for task: {args.task_id}")
        return 1

    if args.json:
        print(json.dumps(events, ensure_ascii=False, indent=2))
        return 0

    if args.tree:
        _print_trace_tree(events)
    else:
        _print_trace_timeline(events)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
