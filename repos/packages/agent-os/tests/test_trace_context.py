"""Tests for Phase 1 trace context, sink, and structured emitter."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest import TestCase

# Ensure package is importable from src/
ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.observability import emit_event, emit_workflow_event, emit_events, TraceEmitter
from agent_os.trace_context import (
    StructuredTraceEmitter,
    TraceContext,
    TraceSink,
)


# ===================================================================
# TraceContext
# ===================================================================

class TestTraceContext(TestCase):
    def test_root_context_has_no_parent(self) -> None:
        ctx = TraceContext.root(task_id="t-1", tier="C3", component="agent")
        self.assertIsNone(ctx.parent_span_id)
        self.assertEqual(ctx.level, 0)
        self.assertTrue(ctx.trace_id.startswith("trace-"))
        self.assertTrue(ctx.span_id.startswith("span-"))
        self.assertEqual(ctx.task_id, "t-1")
        self.assertEqual(ctx.tier, "C3")
        self.assertEqual(ctx.component, "agent")

    def test_child_context_inherits_trace_id(self) -> None:
        parent = TraceContext.root(task_id="t-1", tier="C3", component="agent")
        child = parent.child(task_id="t-2", tier="C2", component="tool")
        self.assertEqual(child.trace_id, parent.trace_id)
        self.assertEqual(child.parent_span_id, parent.span_id)
        self.assertEqual(child.level, 1)
        self.assertNotEqual(child.span_id, parent.span_id)

    def test_three_levels_deep_propagation(self) -> None:
        root = TraceContext.root(task_id="t-1", tier="C4", component="agent")
        child1 = root.child(task_id="t-2", tier="C3", component="tool")
        child2 = child1.child(task_id="t-3", tier="C2", component="verifier")
        child3 = child2.child(task_id="t-4", tier="C1", component="memory")

        # All share the same trace_id
        self.assertEqual(root.trace_id, child1.trace_id)
        self.assertEqual(root.trace_id, child2.trace_id)
        self.assertEqual(root.trace_id, child3.trace_id)

        # Chain of parent_span_id
        self.assertIsNone(root.parent_span_id)
        self.assertEqual(child1.parent_span_id, root.span_id)
        self.assertEqual(child2.parent_span_id, child1.span_id)
        self.assertEqual(child3.parent_span_id, child2.span_id)

        # Depths
        self.assertEqual(root.level, 0)
        self.assertEqual(child1.level, 1)
        self.assertEqual(child2.level, 2)
        self.assertEqual(child3.level, 3)


# ===================================================================
# TraceSink
# ===================================================================

class TestTraceSink(TestCase):
    def test_write_and_read_single_event(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))
            sink.write({"ts": "2026-04-14T00:00:00", "event_type": "task_start", "task_id": "x"})

            results = sink.query_by_task_id("x")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["event_type"], "task_start")

    def test_query_by_trace_id(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))
            tid = "trace-abc123"
            sink.write({"trace_id": tid, "event_type": "tool_call", "ts": "2026-04-14T00:01:00"})
            sink.write({"trace_id": "other-trace", "event_type": "task_end", "ts": "2026-04-14T00:02:00"})
            sink.write({"trace_id": tid, "event_type": "tool_result", "ts": "2026-04-14T00:03:00"})

            results = sink.query_by_trace_id(tid)
            self.assertEqual(len(results), 2)
            # Chronological order
            self.assertEqual(results[0]["event_type"], "tool_call")
            self.assertEqual(results[1]["event_type"], "tool_result")

    def test_query_by_task_id_from_data_field(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))
            sink.write({
                "event_type": "task_start",
                "ts": "2026-04-14T00:00:00",
                "data": {"task_id": "task-42"},
            })

            results = sink.query_by_task_id("task-42")
            self.assertEqual(len(results), 1)

    def test_query_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))
            for i in range(20):
                sink.write({"task_id": "t-many", "event_type": "tool_call", "ts": f"2026-04-14T00:{i:02d}:00"})

            results = sink.query_by_task_id("t-many", limit=5)
            self.assertLessEqual(len(results), 5)

    def test_file_rotation_daily(self) -> None:
        """Verify that rotate_if_needed archives the old file and resets _current_date."""
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td), rotation_policy="daily")
            today = _today_str_for_test()
            old_date = "2020-01-01"

            # Write normally (today's date, no rotation)
            sink.write({"event_type": "test", "ts": f"{today}T00:00:00"})
            today_file = sink.get_current_file()
            self.assertTrue(today_file.exists())
            self.assertEqual(len(list(Path(td).glob("agent_traces*"))), 1)

            # Now create an "old date" file manually and set _current_date to match
            old_file = Path(td) / f"agent_traces_{old_date}.jsonl"
            old_file.write_text('{"event_type": "old", "ts": "2020-01-01T00:00:00"}\n')
            sink._current_date = old_date

            # Write again: triggers rotation of old file
            sink.write({"event_type": "new", "ts": f"{today}T01:00:00"})

            # Old file should have been archived
            self.assertFalse(old_file.exists())
            archived = list(Path(td).glob(f"agent_traces_{old_date}.*"))
            self.assertGreaterEqual(len(archived), 1, "Old file should have been archived")

            # New current file should be for today
            self.assertEqual(sink._current_date, today)
            self.assertTrue(sink.get_current_file().exists())

            # Total files: archived old + today's
            all_files = list(Path(td).glob("agent_traces*"))
            self.assertGreaterEqual(len(all_files), 2)

    def test_file_rotation_size(self) -> None:
        """Verify rotation when file exceeds max_file_size_mb."""
        with tempfile.TemporaryDirectory() as td:
            # 1 MB max to trigger rotation quickly
            sink = TraceSink(trace_dir=Path(td), max_file_size_mb=1, rotation_policy="size")
            # Write enough data to exceed 1 MB (~1024 chars per line, ~1050 lines)
            big_payload = "X" * 1000
            for i in range(1100):
                sink.write({"event_type": "size-test", "payload": big_payload, "i": i})

            files = sorted(Path(td).glob("agent_traces_*.jsonl"))
            # At least 2 files: original + at least one rotation
            self.assertGreaterEqual(len(files), 2)

    def test_get_current_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))
            current = sink.get_current_file()
            self.assertTrue(str(current).endswith(".jsonl"))
            self.assertIn(_today_str_for_test(), str(current))


# ===================================================================
# StructuredTraceEmitter
# ===================================================================

class TestStructuredTraceEmitter(TestCase):
    def _make_emitter(self) -> tuple[StructuredTraceEmitter, Path]:
        td = tempfile.mkdtemp()
        sink = TraceSink(trace_dir=Path(td))
        return StructuredTraceEmitter(sink=sink), Path(td)

    def _read_events(self, directory: Path) -> list[dict]:
        results = []
        for fp in sorted(directory.glob("agent_traces_*.jsonl")):
            for line in fp.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    results.append(json.loads(line))
        return results

    def test_task_start(self) -> None:
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="ts-1", tier="C3", component="agent")
        emitter.task_start(ctx, extra_field="hello")

        events = self._read_events(d)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["event_type"], "task_start")
        self.assertEqual(ev["level"], "info")
        self.assertEqual(ev["data"]["task_id"], "ts-1")
        self.assertEqual(ev["data"]["extra_field"], "hello")
        self.assertIn("trace_id", ev)
        self.assertIn("span_id", ev)
        self.assertIn("ts", ev)

    def test_task_end(self) -> None:
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="te-1", tier="C2", component="tool")
        emitter.task_end(ctx, duration_ms=150.5, status="completed")

        events = self._read_events(d)
        ev = events[0]
        self.assertEqual(ev["event_type"], "task_end")
        self.assertEqual(ev["data"]["status"], "completed")
        self.assertEqual(ev["data"]["duration_ms"], 150.5)

    def test_task_error(self) -> None:
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="err-1", tier="C4", component="verifier")
        emitter.task_error(ctx, error_type="ValidationError", error_message="bad input")

        events = self._read_events(d)
        ev = events[0]
        self.assertEqual(ev["event_type"], "task_error")
        self.assertEqual(ev["level"], "error")
        self.assertEqual(ev["data"]["error_type"], "ValidationError")
        self.assertEqual(ev["data"]["error_message"], "bad input")

    def test_tool_call_and_result(self) -> None:
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="tool-1", tier="C3", component="tool")
        emitter.tool_call(ctx, tool_name="search_web", query="hello")
        emitter.tool_result(ctx, tool_name="search_web", status="ok", duration_ms=42.0)

        events = self._read_events(d)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_type"], "tool_call")
        self.assertEqual(events[0]["data"]["tool_name"], "search_web")
        self.assertEqual(events[1]["event_type"], "tool_result")
        self.assertEqual(events[1]["data"]["status"], "ok")
        self.assertEqual(events[1]["data"]["duration_ms"], 42.0)

    def test_retry_event(self) -> None:
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="retry-1", tier="C3", component="agent")
        emitter.retry(ctx, attempt=2, reason="rate_limit")

        events = self._read_events(d)
        ev = events[0]
        self.assertEqual(ev["event_type"], "retry")
        self.assertEqual(ev["level"], "warn")
        self.assertEqual(ev["data"]["attempt"], 2)

    def test_fallback_event(self) -> None:
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="fb-1", tier="C3", component="agent")
        emitter.fallback(ctx, from_model="gpt-4", to_model="claude-3", reason="timeout")

        events = self._read_events(d)
        ev = events[0]
        self.assertEqual(ev["event_type"], "fallback")
        self.assertEqual(ev["level"], "warn")
        self.assertEqual(ev["data"]["from_model"], "gpt-4")
        self.assertEqual(ev["data"]["to_model"], "claude-3")

    def test_lease_issue_and_expire(self) -> None:
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="lease-1", tier="C3", component="agent")
        emitter.lease_issue(ctx, agent_id="a-1")
        emitter.lease_expire(ctx, agent_id="a-1")

        events = self._read_events(d)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event_type"], "lease_issue")
        self.assertEqual(events[0]["level"], "info")
        self.assertEqual(events[1]["event_type"], "lease_expire")
        self.assertEqual(events[1]["level"], "warn")

    def test_child_context_via_emitter(self) -> None:
        emitter, _ = self._make_emitter()
        parent = TraceContext.root(task_id="p-1", tier="C4", component="agent")
        child = emitter.child_context(parent, task_id="c-1", tier="C2", component="tool")

        self.assertEqual(child.trace_id, parent.trace_id)
        self.assertEqual(child.parent_span_id, parent.span_id)
        self.assertEqual(child.level, 1)

    def test_all_events_have_required_envelope_fields(self) -> None:
        """Every emitted event must have ts, trace_id, span_id, task_id, tier, component, level, event_type, data."""
        emitter, d = self._make_emitter()
        ctx = TraceContext.root(task_id="full-1", tier="C3", component="agent")

        # Emit all event types
        emitter.task_start(ctx)
        emitter.task_end(ctx, duration_ms=10)
        emitter.task_error(ctx, error_type="E", error_message="m")
        emitter.tool_call(ctx, tool_name="t")
        emitter.tool_result(ctx, tool_name="t", status="ok")
        emitter.retry(ctx, attempt=1, reason="r")
        emitter.fallback(ctx, from_model="a", to_model="b", reason="r")
        emitter.lease_issue(ctx, agent_id="a-1")
        emitter.lease_expire(ctx, agent_id="a-1")

        required = {"ts", "trace_id", "span_id", "parent_span_id", "task_id",
                     "tier", "component", "level", "event_type", "data"}
        events = self._read_events(d)
        self.assertEqual(len(events), 9)
        for ev in events:
            missing = required - set(ev.keys())
            self.assertEqual(missing, set(), f"Missing fields in {ev['event_type']}: {missing}")


# ===================================================================
# Thread Safety
# ===================================================================

class TestThreadSafety(TestCase):
    def test_concurrent_writes_from_10_threads(self) -> None:
        """10 threads each write 100 events; all 1000 must be present."""
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))
            errors: list[str] = []

            def writer(thread_id: int) -> None:
                try:
                    for i in range(100):
                        sink.write({
                            "event_type": "concurrent-test",
                            "task_id": f"t-{thread_id}-{i}",
                            "ts": _utc_now_iso_thread(),
                        })
                except Exception as e:
                    errors.append(f"thread-{thread_id}: {e}")

            threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [], f"Thread errors: {errors}")

            # Count total lines in all trace files
            total = 0
            for fp in Path(td).glob("agent_traces_*.jsonl"):
                total += sum(1 for line in fp.read_text().splitlines() if line.strip())
            self.assertEqual(total, 1000)

    def test_concurrent_writes_no_corruption(self) -> None:
        """Concurrent writes must produce valid JSON on every line."""
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))

            def writer(thread_id: int) -> None:
                for i in range(50):
                    sink.write({
                        "event_type": "json-test",
                        "i": i,
                        "thread": thread_id,
                        "ts": _utc_now_iso_thread(),
                    })

            threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Every line must be valid JSON
            for fp in Path(td).glob("agent_traces_*.jsonl"):
                for line in fp.read_text().splitlines():
                    if line.strip():
                        json.loads(line)  # raises if corrupt


# ===================================================================
# Performance
# ===================================================================

class TestPerformance(TestCase):
    def test_1000_emissions_under_1_second(self) -> None:
        """1000 sequential emissions should complete in < 1 second total."""
        with tempfile.TemporaryDirectory() as td:
            sink = TraceSink(trace_dir=Path(td))
            emitter = StructuredTraceEmitter(sink=sink)
            ctx = TraceContext.root(task_id="perf-1", tier="C3", component="agent")

            t0 = time.perf_counter()
            for i in range(1000):
                emitter.tool_call(ctx, tool_name=f"tool-{i}")
            elapsed = time.perf_counter() - t0

            self.assertLess(elapsed, 1.0, f"1000 emissions took {elapsed:.3f}s (limit: 1.0s)")


# ===================================================================
# Backward Compatibility
# ===================================================================

class TestBackwardCompatibility(TestCase):
    def test_existing_emit_event_still_works(self) -> None:
        """Existing emit_event() must still write valid JSONL after adding trace_context."""
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "compat.jsonl"
            prev = os.environ.get("AGENT_OS_TRACE_FILE")
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                emit_event("route_decision", {
                    "component": "router",
                    "run_id": "run-compat",
                    "task_type": "T3",
                    "complexity": "C3",
                })
            finally:
                if prev is None:
                    os.environ.pop("AGENT_OS_TRACE_FILE", None)
                else:
                    os.environ["AGENT_OS_TRACE_FILE"] = prev

            lines = trace_file.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any(line.strip() for line in lines))
            ev = json.loads(lines[0])
            self.assertEqual(ev["event_type"], "route_decision")
            self.assertIn("ts", ev)
            self.assertIn("component", ev)

    def test_existing_emit_workflow_event_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "compat_wf.jsonl"
            prev = os.environ.get("AGENT_OS_TRACE_FILE")
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                emit_workflow_event(
                    "test-workflow",
                    "completed",
                    duration_ms=50,
                    token_cost=0.01,
                )
            finally:
                if prev is None:
                    os.environ.pop("AGENT_OS_TRACE_FILE", None)
                else:
                    os.environ["AGENT_OS_TRACE_FILE"] = prev

            lines = trace_file.read_text(encoding="utf-8").splitlines()
            ev = json.loads(lines[0])
            self.assertEqual(ev["event_type"], "workflow_completed")
            self.assertEqual(ev["workflow_name"], "test-workflow")

    def test_existing_emit_events_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "compat_multi.jsonl"
            prev = os.environ.get("AGENT_OS_TRACE_FILE")
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                emit_events([
                    {"event_type": "agent_run_started", "status": "started", "component": "agent"},
                    {"event_type": "agent_run_completed", "status": "completed", "component": "agent"},
                ])
            finally:
                if prev is None:
                    os.environ.pop("AGENT_OS_TRACE_FILE", None)
                else:
                    os.environ["AGENT_OS_TRACE_FILE"] = prev

            lines = [l for l in trace_file.read_text().splitlines() if l.strip()]
            self.assertEqual(len(lines), 2)

    def test_existing_TraceEmitter_still_works(self) -> None:
        """Legacy TraceEmitter class must still function."""
        with tempfile.TemporaryDirectory() as td:
            emitter = TraceEmitter(log_dir=Path(td))
            from agent_os.observability import SessionTrace
            trace = SessionTrace(trace_id="legacy-1", task_type="T3", complexity="C3")
            emitter.emit(trace)

            traces = emitter.get_traces()
            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0]["trace_id"], "legacy-1")


# ===================================================================
# Helpers
# ===================================================================

def _today_str_for_test() -> str:
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _utc_now_iso_thread() -> str:
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc).isoformat()
