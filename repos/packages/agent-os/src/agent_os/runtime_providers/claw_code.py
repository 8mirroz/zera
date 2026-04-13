from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from ..contracts import AgentInput, AgentOutput
from ..exceptions import RuntimeProviderExecutionError, RuntimeProviderUnavailableError
from ..observability import emit_event
from ..security_policy import SecurityPolicy
from .base import RuntimeProvider


class ClawCodeRuntimeProvider(RuntimeProvider):
    """Runtime provider bridge for claw-code-compatible stdio execution."""

    name = "claw_code"

    def run(
        self,
        agent_input: AgentInput,
        *,
        repo_root: Path,
        runtime_profile: str | None = None,
    ) -> AgentOutput:
        start_ms = int(time.time() * 1000)
        route_decision = agent_input.route_decision if isinstance(agent_input.route_decision, dict) else {}
        profile_data = route_decision.get("runtime_profile_data") if isinstance(route_decision.get("runtime_profile_data"), dict) else {}
        security = SecurityPolicy(repo_root).validate_runtime_profile(runtime_profile, profile_data, provider_name=self.name)
        if not security.allowed:
            raise RuntimeProviderExecutionError("; ".join(security.issues))

        emit_event(
            "agent_run_started",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": "ok",
                "message": "Claw-Code runtime started",
                "objective": agent_input.objective,
                "route_decision": route_decision,
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
            },
        )

        payload = {
            "run_id": agent_input.run_id,
            "objective": agent_input.objective,
            "plan_steps": list(agent_input.plan_steps),
            "route_decision": route_decision,
        }
        result = self._execute_profile(repo_root=repo_root, runtime_profile=runtime_profile, profile_data=profile_data, payload=payload)
        output = self._to_agent_output(result)

        duration_ms = int(time.time() * 1000) - start_ms
        emit_event(
            "agent_run_completed",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": output.status,
                "duration_ms": duration_ms,
                "message": "Claw-Code runtime completed",
                "data": {"artifacts_count": len(output.artifacts)},
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
            },
        )
        return output

    def _execute_profile(
        self,
        *,
        repo_root: Path,
        runtime_profile: str | None,
        profile_data: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        command = profile_data.get("command", [])
        native_command = profile_data.get("native_command", [])
        execution_mode = str(profile_data.get("execution_mode") or "health_probe")
        timeout_seconds = int(profile_data.get("timeout_seconds", 15))

        if execution_mode == "stdio_json" and isinstance(command, list) and command:
            return self._run_stdio_json_command(repo_root, command, timeout_seconds=timeout_seconds, payload=payload)
        if execution_mode == "claw_native" and isinstance(native_command, list) and native_command:
            return self._run_stdio_json_command(repo_root, native_command, timeout_seconds=timeout_seconds, payload=payload)

        claw_code_bin = self._resolve_claw_code_bin()
        self._health_probe(claw_code_bin)
        return {
            "status": "completed",
            "diff_summary": (
                "Claw-Code runtime provider executed health probe and accepted run context. "
                "Repository mutations remain disabled in integration mode."
            ),
            "test_report": {
                "status": "not-run",
                "details": "Claw-Code provider currently runs in health-probe mode.",
            },
            "artifacts": [],
            "next_action": (
                f"Configure a stdio_json command for runtime profile '{runtime_profile or 'default'}' to enable full execution."
            ),
            "meta": {"runtime_provider": self.name},
        }

    def _run_stdio_json_command(
        self,
        repo_root: Path,
        command: list[Any],
        *,
        timeout_seconds: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        args = [self._resolve_arg(repo_root, part) for part in command]
        try:
            proc = subprocess.run(
                args,
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                cwd=repo_root,
                timeout=max(1, timeout_seconds),
                check=False,
            )
        except Exception as exc:
            raise RuntimeProviderExecutionError(f"Claw-Code stdio JSON command failed: {exc}") from exc
        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeProviderExecutionError(f"Claw-Code stdio JSON command exit={proc.returncode}: {stderr[:300]}")
        stdout = (proc.stdout or "").strip()
        if not stdout:
            raise RuntimeProviderExecutionError("Claw-Code stdio JSON command returned empty stdout")
        try:
            result = json.loads(stdout.splitlines()[-1])
        except Exception as exc:
            raise RuntimeProviderExecutionError(f"Claw-Code stdio JSON command returned non-JSON output: {exc}") from exc
        if not isinstance(result, dict):
            raise RuntimeProviderExecutionError("Claw-Code stdio JSON command returned unexpected payload shape")
        return result

    @staticmethod
    def _to_agent_output(result: dict[str, Any]) -> AgentOutput:
        return AgentOutput(
            status=str(result.get("status") or "failed"),
            diff_summary=str(result.get("diff_summary") or "Claw-Code execution returned no summary."),
            test_report=dict(result.get("test_report") or {}),
            artifacts=list(result.get("artifacts") or []),
            next_action=str(result.get("next_action") or ""),
            response_text=str(result.get("response_text") or "") or None,
            meta=dict(result.get("meta") or {}),
        )

    @staticmethod
    def _resolve_arg(repo_root: Path, value: Any) -> str:
        raw = str(value)
        if raw == "__CLAW_CODE_BIN__":
            return ClawCodeRuntimeProvider._resolve_claw_code_bin()
        if "/" in raw and not os.path.isabs(raw):
            candidate = repo_root / raw
            if candidate.exists():
                return str(candidate)
        return raw

    @staticmethod
    def _resolve_claw_code_bin() -> str:
        raw = (os.getenv("CLAW_CODE_BIN") or "").strip()
        if raw:
            if os.path.isabs(raw) and os.path.exists(raw):
                return raw
            resolved = shutil.which(raw)
            if resolved:
                return resolved
        for name in ("claw", "claw-code"):
            resolved = shutil.which(name)
            if resolved:
                return resolved
        raise RuntimeProviderUnavailableError(
            "Claw-Code binary not found. Install `claw`/`claw-code` or set CLAW_CODE_BIN."
        )

    @staticmethod
    def _health_probe(binary_path: str) -> None:
        try:
            proc = subprocess.run(
                [binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception as exc:
            raise RuntimeProviderExecutionError(f"Claw-Code health probe failed: {exc}") from exc
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise RuntimeProviderExecutionError(
                f"Claw-Code health probe exit={proc.returncode}: {stderr[:300]}"
            )
