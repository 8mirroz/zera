from __future__ import annotations

import subprocess
import time
from dataclasses import asdict
from typing import Any

from .contracts import ToolInput, ToolOutput
from .exceptions import PermissionDeniedError, ToolExecutionError, ToolNotFoundError, ToolTimeoutError

# ---------------------------------------------------------------------------
# Lazy-initialized structured trace emitter
# ---------------------------------------------------------------------------

_emitter: Any = None

def _get_emitter() -> Any:
    global _emitter
    if _emitter is None:
        from .trace_context import TraceSink, StructuredTraceEmitter
        _emitter = StructuredTraceEmitter(TraceSink(filename="agent_traces.jsonl"))
    return _emitter


class ToolRunner:
    """Unified tool contract wrapper with retry policy by mode."""

    def __init__(self, *, default_timeout_seconds: int = 60, test_timeout_seconds: int = 240) -> None:
        self.default_timeout_seconds = default_timeout_seconds
        self.test_timeout_seconds = test_timeout_seconds

    def _timeout_for(self, tool_name: str) -> int:
        if "test" in tool_name.lower():
            return self.test_timeout_seconds
        return self.default_timeout_seconds

    def run(self, tool_input: ToolInput) -> ToolOutput:
        mode = tool_input.mode
        if mode not in {"read", "write"}:
            raise PermissionDeniedError(f"Unsupported mode: {mode}")

        # --- trace: tool execution start ---
        from .trace_context import TraceContext
        ctx = TraceContext.root(
            task_id=f"tool-{tool_input.tool_name}",
            tier="C2",
            component="tool_runner",
        )
        # --- end trace ---

        retries = 1 if mode == "read" else 0
        timeout = self._timeout_for(tool_input.tool_name)
        attempt = 0
        last_error: Exception | None = None
        start_ms = int(time.time() * 1000)

        while attempt <= retries:
            attempt += 1
            # --- trace: tool_call event ---
            _get_emitter().tool_call(
                ctx,
                tool_name=tool_input.tool_name,
                mode=mode,
                attempt=attempt,
                args_count=len(tool_input.args),
                run_id=tool_input.correlation_id,
            )
            # --- end trace ---
            try:
                proc = subprocess.run(
                    [tool_input.tool_name, *tool_input.args],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise ToolNotFoundError(str(exc)) from exc
            except subprocess.TimeoutExpired as exc:
                last_error = ToolTimeoutError(f"Tool timeout ({timeout}s): {tool_input.tool_name}")
                if attempt <= retries:
                    continue
                raise last_error from exc

            duration_ms = int(time.time() * 1000) - start_ms
            if proc.returncode == 0:
                output = ToolOutput(
                    status="ok",
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    artifacts=[],
                    exit_code=proc.returncode,
                )
                # --- trace: tool_result event (ok) ---
                _get_emitter().tool_result(
                    ctx,
                    tool_name=tool_input.tool_name,
                    status="ok",
                    duration_ms=duration_ms,
                    mode=mode,
                    attempt=attempt,
                    run_id=tool_input.correlation_id,
                )
                # --- end trace ---
                return output

            last_error = ToolExecutionError(
                f"Tool failed: {tool_input.tool_name} exit={proc.returncode} stderr={proc.stderr.strip()}"
            )
            if attempt <= retries:
                continue

            duration_ms = int(time.time() * 1000) - start_ms
            output = ToolOutput(
                status="error",
                stdout=proc.stdout,
                stderr=proc.stderr,
                artifacts=[],
                exit_code=proc.returncode,
            )
            # --- trace: tool_result event (error) ---
            _get_emitter().tool_result(
                ctx,
                tool_name=tool_input.tool_name,
                status="error",
                duration_ms=duration_ms,
                mode=mode,
                attempt=attempt,
                exit_code=proc.returncode,
                run_id=tool_input.correlation_id,
            )
            # --- end trace ---
            return output

        if last_error is not None:
            raise last_error
        raise ToolExecutionError("Unknown tool runner error")

    @staticmethod
    def to_json(tool_output: ToolOutput) -> str:
        import json

        return json.dumps(asdict(tool_output), ensure_ascii=False, indent=2)
