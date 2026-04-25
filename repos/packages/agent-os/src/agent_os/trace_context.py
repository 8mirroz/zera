"""Phase 1: Core Trace Emitter and File-Based Trace Sink.

Provides structured trace emission with parent-child correlation,
thread-safe JSONL file storage with rotation, and lifecycle event helpers.

Compatible with trace_schema.json v2.1 envelope:
  {ts, run_id, event_type, level, component, data, ...}
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


# ---------------------------------------------------------------------------
# TraceContext
# ---------------------------------------------------------------------------

@dataclass
class TraceContext:
    """Thread-safe trace context for a task execution tree."""

    run_id: str                  # Stable correlation ID (session/process run)
    trace_id: str                # Root correlation ID (shared across parent -> child)
    span_id: str                 # Unique span ID for this execution
    parent_span_id: str | None   # Parent's span_id (None for root)
    task_id: str                 # Task identifier
    tier: str                    # C1-C5
    component: str               # Emitting component
    level: int                   # Nesting depth (0=root, 1=child, etc.)
    started_at: str              # ISO-8601 timestamp

    @classmethod
    def root(cls, task_id: str, tier: str, component: str, run_id: str | None = None) -> TraceContext:
        """Create a root trace context (no parent)."""
        tid = f"trace-{uuid4().hex[:16]}"
        return cls(
            run_id=run_id or tid,
            trace_id=tid,
            span_id=f"span-{uuid4().hex[:12]}",
            parent_span_id=None,
            task_id=task_id,
            tier=tier,
            component=component,
            level=0,
            started_at=_utc_now_iso(),
        )

    def child(self, task_id: str, tier: str, component: str) -> TraceContext:
        """Create a child context inheriting run_id, trace_id and incrementing depth."""
        return TraceContext(
            run_id=self.run_id,
            trace_id=self.trace_id,
            span_id=f"span-{uuid4().hex[:12]}",
            parent_span_id=self.span_id,
            task_id=task_id,
            tier=tier,
            component=component,
            level=self.level + 1,
            started_at=_utc_now_iso(),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(tz=timezone.utc).isoformat()


def _file_size_mb(path: Path) -> float:
    """Return file size in megabytes."""
    if path.exists():
        return path.stat().st_size / (1024 * 1024)
    return 0.0


def _today_str() -> str:
    """Return today's date as YYYY-MM-DD in UTC."""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# TraceSink — file-based JSONL sink with rotation
# ---------------------------------------------------------------------------

class TraceSink:
    """Persistent trace storage with file rotation.

    Writes structured events as JSONL lines.  Rotation occurs when the
    current file exceeds ``max_file_size_mb`` or the date changes
    (daily policy).
    """

    def __init__(
        self,
        trace_dir: Path = Path("logs"),
        max_file_size_mb: int = 100,
        rotation_policy: str = "daily",  # "daily" | "size"
        filename: str | None = None,      # Override: exact filename (for backward compat)
    ) -> None:
        # Respect AGENT_OS_TRACE_FILE env var (same as legacy emit_event)
        env_trace = os.getenv("AGENT_OS_TRACE_FILE")
        if env_trace:
            env_path = Path(env_trace)
            if not env_path.is_absolute():
                env_path = Path.cwd() / env_path
            self.trace_dir = env_path.parent
            self._fixed_filename = env_path.name
            self.rotation_policy = "none"  # No rotation for explicit path
        else:
            self.trace_dir = trace_dir
            self.max_file_size_mb = max_file_size_mb
            self.rotation_policy = rotation_policy
            self._fixed_filename = filename
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._current_date = _today_str()

    # -- public API ---------------------------------------------------------

    def write(self, event: dict[str, Any]) -> None:
        """Thread-safe append of one event dict to the current trace file."""
        with self._lock:
            self.rotate_if_needed()
            target = self._current_file_path()
            with target.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def query_by_task_id(self, task_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        """Search all trace files for events matching *task_id*, chronological."""
        return self._query_all(lambda ev: ev.get("data", {}).get("task_id") == task_id
                               or ev.get("task_id") == task_id,
                               limit)

    def query_by_trace_id(self, trace_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        """Search all trace files for events matching *trace_id* (correlation)."""
        return self._query_all(lambda ev: ev.get("trace_id") == trace_id
                               or ev.get("data", {}).get("trace_id") == trace_id,
                               limit)

    def get_current_file(self) -> Path:
        """Return path to the currently active trace file."""
        return self._current_file_path()

    def rotate_if_needed(self) -> None:
        """Check file size/age; rotate to a new file if thresholds exceeded."""
        if self._fixed_filename is not None:
            return  # Fixed filename — no rotation
        today = _today_str()
        old_date = self._current_date  # save BEFORE any changes
        current = self.trace_dir / f"agent_traces_{old_date}.jsonl"

        if self.rotation_policy == "daily" and today != old_date:
            # Archive the old-date file before switching
            if current.exists():
                archive_name = _archive_path(current, today)
                current.rename(archive_name)
            self._current_date = today
        elif self.rotation_policy == "size" and _file_size_mb(current) >= self.max_file_size_mb:
            if current.exists():
                archive_name = _archive_path(current, today)
                current.rename(archive_name)

    # -- internals ----------------------------------------------------------

    def _current_file_path(self) -> Path:
        if self._fixed_filename is not None:
            return self.trace_dir / self._fixed_filename
        return self.trace_dir / f"agent_traces_{self._current_date}.jsonl"

    def _query_all(self, predicate: Any, limit: int) -> list[dict[str, Any]]:
        """Scan JSONL files in trace_dir, return matching events sorted by ts.
        Uses incremental reading with line-buffering to avoid OOM for large traces.
        """
        results: list[dict[str, Any]] = []
        files = []
        if self._fixed_filename is not None:
            files = [self.trace_dir / self._fixed_filename]
        else:
            files = sorted(self.trace_dir.glob("agent_traces_*.jsonl"))

        for fp in files:
            if not fp.exists():
                continue
            try:
                with fp.open("r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            ev = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if predicate(ev):
                            results.append(ev)
                            if len(results) >= limit:
                                return results
            except OSError:
                continue

        results.sort(key=lambda ev: ev.get("ts", ""))
        return results


def _current_date_safe() -> str:
    """Return the current date in a filesystem-safe format."""
    return _today_str()


def _archive_path(original: Path, archive_date: str) -> Path:
    """Compute an archive path for a trace file, avoiding collisions."""
    stem = original.stem  # e.g. "agent_traces_2026-04-14"
    archive_name = f"{stem}.{archive_date}.jsonl"
    target = original.parent / archive_name
    counter = 1
    while target.exists():
        archive_name = f"{stem}.{archive_date}_{counter}.jsonl"
        target = original.parent / archive_name
        counter += 1
    return target


# ---------------------------------------------------------------------------
# StructuredTraceEmitter
# ---------------------------------------------------------------------------

class StructuredTraceEmitter:
    """Phase 1: Structured trace emitter for task lifecycle events.

    Wraps a :class:`TraceSink` and emits strongly-typed lifecycle events
    (task_start, task_end, tool_call, retry, fallback, …) while keeping
    the v2.1 envelope contract.
    """

    # Event-type -> schema-level type mapping
    EVENT_TYPES = {
        "task_start": "task_start",
        "task_end": "task_end",
        "task_error": "task_error",
        "tool_call": "tool_call",
        "tool_result": "tool_result",
        "retry": "retry",
        "fallback": "fallback",
        "lease_issue": "lease_issue",
        "lease_expire": "lease_expire",
    }

    def __init__(self, sink: TraceSink) -> None:
        self.sink = sink

    # -- lifecycle events ---------------------------------------------------

    def task_start(self, ctx: TraceContext, **kwargs: Any) -> None:
        """Emit task_start event. Required fields: task_id, tier, component."""
        self._emit(ctx, "task_start", "info", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            **kwargs,
        })

    def task_end(
        self,
        ctx: TraceContext,
        duration_ms: float,
        status: str = "completed",
        **kwargs: Any,
    ) -> None:
        """Emit task_end event."""
        self._emit(ctx, "task_end", "info", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "status": status,
            "duration_ms": duration_ms,
            **kwargs,
        })

    def task_error(
        self,
        ctx: TraceContext,
        error_type: str,
        error_message: str,
        **kwargs: Any,
    ) -> None:
        """Emit task_error event. level=error."""
        self._emit(ctx, "task_error", "error", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "error_type": error_type,
            "error_message": error_message,
            **kwargs,
        })

    def tool_call(self, ctx: TraceContext, tool_name: str, **kwargs: Any) -> None:
        """Emit tool_call start event."""
        self._emit(ctx, "tool_call", "info", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "tool_name": tool_name,
            "status": "started",
            **kwargs,
        })

    def tool_result(
        self,
        ctx: TraceContext,
        tool_name: str,
        status: str,
        duration_ms: float = 0,
        **kwargs: Any,
    ) -> None:
        """Emit tool_result event."""
        self._emit(ctx, "tool_result", "info", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "tool_name": tool_name,
            "status": status,
            "duration_ms": duration_ms,
            **kwargs,
        })

    def retry(self, ctx: TraceContext, attempt: int, reason: str, **kwargs: Any) -> None:
        """Emit retry event. level=warning."""
        self._emit(ctx, "retry", "warn", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "attempt": attempt,
            "reason": reason,
            **kwargs,
        })

    def fallback(
        self,
        ctx: TraceContext,
        from_model: str,
        to_model: str,
        reason: str,
        **kwargs: Any,
    ) -> None:
        """Emit fallback event. level=warning."""
        self._emit(ctx, "fallback", "warn", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "from_model": from_model,
            "to_model": to_model,
            "reason": reason,
            **kwargs,
        })

    def lease_issue(self, ctx: TraceContext, agent_id: str, **kwargs: Any) -> None:
        """Emit lease_issue event."""
        self._emit(ctx, "lease_issue", "info", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "agent_id": agent_id,
            **kwargs,
        })

    def lease_expire(self, ctx: TraceContext, agent_id: str, **kwargs: Any) -> None:
        """Emit lease_expire event. level=warning."""
        self._emit(ctx, "lease_expire", "warn", {
            "task_id": ctx.task_id,
            "tier": ctx.tier,
            "component": ctx.component,
            "agent_id": agent_id,
            **kwargs,
        })

    # -- context helpers ----------------------------------------------------

    def child_context(
        self,
        parent_ctx: TraceContext,
        task_id: str,
        tier: str,
        component: str,
    ) -> TraceContext:
        """Create a child TraceContext with proper correlation IDs."""
        return parent_ctx.child(task_id=task_id, tier=tier, component=component)

    # -- internal -----------------------------------------------------------

    def _emit(
        self,
        ctx: TraceContext,
        event_type: str,
        level: str,
        data: dict[str, Any],
    ) -> None:
        """Build a v2.1-compliant envelope and write to sink.
        Implements Compaction Mode to reduce metadata noise in long sessions.
        """
        t0 = time.perf_counter()

        # Compaction Logic: If nesting is too deep, prune redundant context fields from envelope
        use_compaction = ctx.level > 5
        
        envelope: dict[str, Any] = {
            "ts": _utc_now_iso(),
            "run_id": ctx.run_id,
            "trace_id": ctx.trace_id,
            "span_id": ctx.span_id,
            "event_type": event_type,
            "level": level,
            "data": data,
        }

        if not use_compaction:
            # Full metadata for shallow spans
            envelope.update({
                "parent_span_id": ctx.parent_span_id,
                "task_id": ctx.task_id,
                "tier": ctx.tier,
                "component": ctx.component,
            })
        else:
            # Compact mode: only include bare essentials
            envelope["_compact"] = True

        # Extract priority fields to envelope level if present in data
        # This is required for schema validation of specific event types
        for field in ["status", "duration_ms", "tool_name", "task_type", "complexity", "model", "model_tier"]:
            val = data.get(field)
            if val is not None:
                if field == "duration_ms" and isinstance(val, (int, float)):
                    envelope[field] = int(val)
                else:
                    envelope[field] = val

        self.sink.write(envelope)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        # Log overhead if > 1 ms (dev-only, never raises)
        if elapsed_ms > 1.0:
            envelope["data"]["_emit_overhead_ms"] = round(elapsed_ms, 3)
