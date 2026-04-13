from __future__ import annotations

import time
from pathlib import Path

from ..contracts import AgentInput, AgentOutput
from ..observability import emit_event
from .base import RuntimeProvider


class AgentOsPythonRuntimeProvider(RuntimeProvider):
    """Current in-process Python runtime behavior (legacy-compatible)."""

    name = "agent_os_python"

    def run(
        self,
        agent_input: AgentInput,
        *,
        repo_root: Path,
        runtime_profile: str | None = None,
    ) -> AgentOutput:
        _ = repo_root
        start_ms = int(time.time() * 1000)
        route_decision = agent_input.route_decision if isinstance(agent_input.route_decision, dict) else {}

        emit_event(
            "agent_run_started",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": "ok",
                "message": "Agent runtime started",
                "objective": agent_input.objective,
                "route_decision": route_decision,
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
            },
        )

        output = AgentOutput(
            status="completed",
            diff_summary="No repository mutations were performed by AgentRuntime MVP.",
            test_report={"status": "not-run", "details": "Use integration scripts for verification."},
            artifacts=[],
            next_action="Execute CodeEditor.apply with explicit target files and verify commands.",
        )

        # HONEST: verification_result status reflects actual verification_state
        # Audit finding RC-2: previously emitted status="ok" with verification_status="not-run"
        verification_status = output.test_report.get("status", "unknown") if isinstance(output.test_report, dict) else "unknown"
        emit_status = "warn" if verification_status == "not-run" else verification_status
        emit_event(
            "verification_result",
            {
                "run_id": agent_input.run_id,
                "component": "verifier",
                "status": emit_status,
                "duration_ms": 0,
                "message": f"Verification not executed in MVP runtime (status={verification_status})",
                "data": {
                    "verification_status": verification_status,
                    "reason": "AgentRuntime MVP does not execute verification commands",
                    "hallucination": {
                        "unsupported_claims": 0,
                        "total_claims": 0,
                        "hallucination_rate": None,
                        "judge": "not-run",
                    },
                },
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
            },
        )

        duration_ms = int(time.time() * 1000) - start_ms
        # HONEST: completion event reflects that verification was not-run
        completion_status = "completed_unverified" if verification_status == "not-run" else output.status
        emit_event(
            "agent_run_completed",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": completion_status,
                "duration_ms": duration_ms,
                "message": f"Agent runtime completed (verification={verification_status})",
                "data": {
                    "artifacts_count": len(output.artifacts),
                    "verification_status": verification_status,
                },
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
            },
        )
        return output

