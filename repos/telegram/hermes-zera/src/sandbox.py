"""Sandbox Infrastructure — patterns from Agent-S / CUA.

Provides:
- Sandbox execution environment isolation
- Trace recording and replay
- Benchmark discipline for agent evaluation
- GUI-agent interface patterns (future desktop control)

Inspired by:
- simular-ai/Agent-S (Agent-Computer Interface, OSWorld)
- trycua/cua (sandboxes, SDKs, benchmarks for desktop agents)
"""
from __future__ import annotations

import json
import time
import hashlib
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("hermes-zera.sandbox")


@dataclass
class SandboxConfig:
    """Configuration for a sandboxed execution environment."""
    name: str
    max_tokens: int = 4096
    max_tool_calls: int = 50
    timeout_seconds: int = 300
    allowed_operations: list[str] = field(default_factory=lambda: ["read", "write", "execute"])
    forbidden_operations: list[str] = field(default_factory=lambda: ["rm -rf", "sudo", "chmod 777"])
    network_access: bool = False
    filesystem_access: bool = True
    workdir: str = "/tmp/hermes-sandbox"


@dataclass
class TraceEvent:
    """Single recorded event in a trace."""
    timestamp: float
    phase: str  # plan, execute, evaluate, reflect
    action: str
    input: dict[str, Any]
    output: dict[str, Any]
    latency_ms: float
    success: bool
    error: str | None = None


@dataclass
class Trace:
    """Full execution trace — replayable audit log."""
    trace_id: str
    task: str
    tier: str
    events: list[TraceEvent] = field(default_factory=list)
    total_latency_ms: float = 0.0
    status: str = "running"  # running, completed, failed

    def add_event(self, event: TraceEvent) -> None:
        self.events.append(event)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "tier": self.tier,
            "events": [asdict(e) for e in self.events],
            "total_latency_ms": self.total_latency_ms,
            "status": self.status,
        }

    def save(self, traces_dir: Path) -> Path:
        """Save trace to file."""
        traces_dir.mkdir(parents=True, exist_ok=True)
        trace_file = traces_dir / f"{self.trace_id}.json"
        trace_file.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"💾 Trace saved: {trace_file}")
        return trace_file


@dataclass
class BenchmarkResult:
    """Result of running a benchmark."""
    benchmark_name: str
    task_count: int
    pass_count: int
    fail_count: int
    avg_score: float
    avg_latency_ms: float
    per_task: list[dict[str, Any]] = field(default_factory=list)


class Sandbox:
    """Sandboxed execution environment with trace/replay."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig(name="default")
        self.traces_dir = Path(self.config.workdir) / "traces"
        self.benchmarks_dir = Path(self.config.workdir) / "benchmarks"
        self._trace: Trace | None = None

    def create_trace(self, task: str, tier: str) -> Trace:
        """Start a new trace."""
        trace_id = hashlib.md5(f"{task}{time.time()}".encode()).hexdigest()[:12]
        self._trace = Trace(
            trace_id=trace_id,
            task=task,
            tier=tier,
        )
        logger.info(f"🎬 Trace started: {trace_id}")
        return self._trace

    def record_event(
        self,
        phase: str,
        action: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        latency_ms: float,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Record an event in the current trace."""
        if not self._trace:
            raise RuntimeError("No active trace — call create_trace() first")

        event = TraceEvent(
            timestamp=time.time(),
            phase=phase,
            action=action,
            input=input_data,
            output=output_data,
            latency_ms=latency_ms,
            success=success,
            error=error,
        )
        self._trace.add_event(event)
        self._trace.total_latency_ms += latency_ms

    def finalize_trace(self, status: str = "completed") -> Trace:
        """Finalize and save the current trace."""
        if not self._trace:
            raise RuntimeError("No active trace")
        self._trace.status = status
        saved_path = self._trace.save(self.traces_dir)
        trace = self._trace
        self._trace = None
        return trace

    def check_safety(self, operation: str) -> tuple[bool, str]:
        """Check if an operation is safe within sandbox constraints."""
        for forbidden in self.config.forbidden_operations:
            if forbidden.lower() in operation.lower():
                return False, f"Operation contains forbidden pattern: {forbidden}"

        if operation not in self.config.allowed_operations:
            return False, f"Operation not in allowed list: {operation}"

        return True, "OK"

    def load_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Load a trace from file for replay."""
        trace_file = self.traces_dir / f"{trace_id}.json"
        if not trace_file.exists():
            return None
        return json.loads(trace_file.read_text(encoding="utf-8"))

    def list_traces(self) -> list[dict[str, str]]:
        """List all saved traces."""
        if not self.traces_dir.exists():
            return []
        traces = []
        for f in sorted(self.traces_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            data = json.loads(f.read_text(encoding="utf-8"))
            traces.append({
                "trace_id": data["trace_id"],
                "task": data["task"][:50],
                "tier": data["tier"],
                "status": data["status"],
                "events": len(data["events"]),
                "file": str(f),
            })
        return traces

    def run_benchmark(
        self,
        tasks: list[tuple[str, str]],  # (task, expected_tier)
        execution_fn: Any,
    ) -> BenchmarkResult:
        """Run a benchmark suite — evaluate agent on a set of tasks.

        Inspired by CUA/OSWorld benchmark discipline.
        """
        logger.info(f"🏁 Benchmark started: {len(tasks)} tasks")
        t0 = time.perf_counter()

        results: list[dict[str, Any]] = []
        pass_count = 0
        total_score = 0.0

        for task, expected_tier in tasks:
            task_t0 = time.perf_counter()

            # Execute in sandbox
            self.create_trace(task, expected_tier)
            try:
                output = execution_fn(task, expected_tier)
                self.record_event(
                    phase="execute",
                    action="task_execution",
                    input_data={"task": task, "tier": expected_tier},
                    output_data={"output": output[:200] if output else ""},
                    latency_ms=(time.perf_counter() - task_t0) * 1000,
                    success=bool(output),
                )
                passed = bool(output)
                score = 1.0 if passed else 0.0
            except Exception as e:
                self.record_event(
                    phase="execute",
                    action="task_execution",
                    input_data={"task": task, "tier": expected_tier},
                    output_data={},
                    latency_ms=(time.perf_counter() - task_t0) * 1000,
                    success=False,
                    error=str(e),
                )
                passed = False
                score = 0.0

            self.finalize_trace("completed" if passed else "failed")

            if passed:
                pass_count += 1
            total_score += score

            results.append({
                "task": task[:50],
                "tier": expected_tier,
                "passed": passed,
                "score": score,
                "latency_ms": (time.perf_counter() - task_t0) * 1000,
            })

        total_latency_ms = (time.perf_counter() - t0) * 1000
        task_count = len(tasks)

        benchmark = BenchmarkResult(
            benchmark_name=f"hermes-zera-{time.strftime('%Y%m%d')}",
            task_count=task_count,
            pass_count=pass_count,
            fail_count=task_count - pass_count,
            avg_score=total_score / max(1, task_count),
            avg_latency_ms=total_latency_ms / max(1, task_count),
            per_task=results,
        )

        # Save benchmark
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)
        bench_file = self.benchmarks_dir / f"{benchmark.benchmark_name}.json"
        bench_file.write_text(
            json.dumps(asdict(benchmark), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            f"🏁 Benchmark completed: {pass_count}/{task_count} passed "
            f"(score={benchmark.avg_score:.2f}, avg_latency={benchmark.avg_latency_ms:.0f}ms)"
        )

        return benchmark


# === GUI-Agent Interface Patterns (future desktop control) ===
# Inspired by Agent-S Agent-Computer Interface (ACI)

@dataclass
class ScreenState:
    """Representation of a screen state for GUI agent interaction."""
    width: int = 1920
    height: int = 1080
    screenshot_base64: str = ""
    accessible_tree: str = ""  # Accessibility tree for structured UI understanding
    focused_element: str = ""
    timestamp: float = 0.0


@dataclass
class GUIAction:
    """Action that a GUI agent can perform."""
    action_type: str  # click, type, scroll, press_key, wait
    x: int | None = None
    y: int | None = None
    text: str = ""
    key: str = ""
    duration_ms: int = 100


class GUIAgentInterface:
    """Interface for GUI control agents (future desktop control).

    Placeholder for Agent-S / CUA integration.
    Provides the API contract that desktop-control agents will implement.
    """

    def get_screen_state(self) -> ScreenState:
        """Capture current screen state."""
        raise NotImplementedError("Desktop control not yet integrated")

    def perform_action(self, action: GUIAction) -> dict[str, Any]:
        """Execute a GUI action."""
        raise NotImplementedError("Desktop control not yet integrated")

    def get_accessible_tree(self) -> str:
        """Get the accessibility tree of the current UI."""
        raise NotImplementedError("Desktop control not yet integrated")

    def find_element(self, description: str) -> dict[str, Any] | None:
        """Find a UI element matching the description."""
        raise NotImplementedError("Desktop control not yet integrated")
