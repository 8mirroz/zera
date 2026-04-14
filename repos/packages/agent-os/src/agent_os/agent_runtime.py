from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Dict, List, Optional

from .contracts import AgentInput, AgentOutput
from .background_job_dispatcher import enqueue_background_jobs_from_output
from .exceptions import RuntimeProviderExecutionError, RuntimeProviderUnavailableError
from .recovery import RecoveryState, RecoveryStateMachine, classify_failure, plan_recovery
from .registry_workflows import RegistryWorkflowResolver
from .runtime_registry import RuntimeRegistry
from .zera_command_os import ZeraCommandOS

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

# Phase 2 Governance Engines
from .arbitration_engine import ArbitrationEngine
from .platform_controller import PlatformController
from .connector_gater import ConnectorGater
from .quality_gate_manager import QualityGateManager

# L1 Memory Integration
try:
    from .profile_manager import ProfileManager
except ImportError:
    ProfileManager = None

# Memory policy enforcement
try:
    from .memory_policy_layer import MemoryPolicyLayer
except ImportError:
    MemoryPolicyLayer = None

logger = logging.getLogger(__name__)

class AgentRuntime:
    """Runtime dispatcher that routes execution to configured provider backends.
    
    Acts as the L1 Orchestration Layer, enforcing governance policies.
    """

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        runtime_registry: RuntimeRegistry | None = None,
        default_provider: str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.runtime_registry = runtime_registry or RuntimeRegistry(self.repo_root)
        self.default_provider = default_provider or self.runtime_registry.default_provider
        
        # Initialize modular governance engines
        self.arbitration_engine = ArbitrationEngine(self.repo_root)
        self.platform_controller = PlatformController(self.repo_root)
        self.connector_gater = ConnectorGater(self.repo_root)
        self.quality_gate_manager = QualityGateManager(self.repo_root)

    def _resolution_for_input(self, agent_input: AgentInput) -> dict:
        """Resolves routing, lane, and mode using modular arbitration engines."""
        route_decision = agent_input.route_decision if isinstance(agent_input.route_decision, dict) else {}
        
        # 1. Resolve Task Intent
        from .routing_vector import RoutingVector
        intent_str = str(route_decision.get("intent") or route_decision.get("task_type") or "analysis")
        intent_profile = RoutingVector.from_intent(self.repo_root, intent_str).to_dict()
        
        # 2. Resolve Lane (Arbitration)
        arbitration_context = {
            "retry_count": int(route_decision.get("retry_count", 0)),
            "prior_outcome": route_decision.get("prior_outcome"),
            "task_tags": route_decision.get("task_tags", []),
            "budget_consumed_ratio": float(route_decision.get("budget_consumed_ratio", 0.0)),
        }
        arb_decision = self.arbitration_engine.resolve_decision(intent_profile, arbitration_context)
        
        # 3. Resolve Operational Mode (Platform Control)
        mode_context = {
            **arbitration_context,
            "intent_class": intent_str,
            "complexity": str(route_decision.get("complexity") or "C1"),
            "user_mentions_direct_mode": route_decision.get("mode"),
        }
        active_mode = self.platform_controller.resolve_mode(mode_context)
        
        # 4. Resolve Provider/Profile based on Lane selection
        lane_mapping = {"quality": "T5", "swarm": "T4", "fast": "T1", "standard": "T3"}
        target_lane = str(arb_decision["lane"]).lower()
        registry_task_type = lane_mapping.get(target_lane, "T3")
        
        resolved = self.runtime_registry.resolve(
            task_type=registry_task_type,
            complexity=str(route_decision.get("complexity") or "C2"),
            requested_provider=str(route_decision.get("runtime_provider")) if route_decision.get("runtime_provider") else None,
            requested_profile=str(route_decision.get("runtime_profile")) if route_decision.get("runtime_profile") else None,
        )
        
        # Enforce Mode and Reason
        resolved["autonomy_mode"] = active_mode
        resolved["routing_decision_reason"] = arb_decision["reason"]
        resolved["escalation_path"] = arb_decision["escalation_path"]
        resolved["intent"] = intent_str
        resolved["complexity"] = str(route_decision.get("complexity") or "C2")
        
        return resolved

    def _should_apply_zera_command_os(self, route_decision: dict[str, object]) -> bool:
        command_id = str(route_decision.get("command_id") or "").strip()
        persona_id = str(route_decision.get("persona_id") or "").strip()
        return command_id.startswith("zera:") or persona_id.startswith("zera")

    def _assemble_zera_persona_prompt(self) -> str:
        persona_dir = self.repo_root / "configs" / "personas" / "zera"
        doc_files = ["constitution.md", "identity.md", "tone.md", "safety.md", "relationship_boundaries.md"]
        parts: list[str] = []
        for doc in doc_files:
            path = persona_dir / doc
            if path.exists():
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    parts.append(f"## {doc}\n{content}")
        return "\n\n".join(parts)

    def _apply_zera_command_os(self, agent_input: AgentInput) -> AgentInput:
        route_decision = agent_input.route_decision if isinstance(agent_input.route_decision, dict) else {}
        if not self._should_apply_zera_command_os(route_decision):
            return agent_input
        
        command_id = str(route_decision.get("command_id") or "").strip() or None
        resolved = ZeraCommandOS(self.repo_root).resolve_command(
            command_id=command_id,
            objective=agent_input.objective,
            client_id=str(route_decision.get("client_id") or "repo_native"),
        )
        enriched = {**route_decision, **resolved}
        
        persona_context = self._assemble_zera_persona_prompt()
        if persona_context:
            enriched["persona_context"] = persona_context

        return replace(agent_input, route_decision=enriched)

    def run(self, agent_input: AgentInput) -> AgentOutput:
        """Main execution loop with pre-flight, provider run, and post-flight validation."""
        # --- trace: agent start ---
        t_start = time.perf_counter()
        from .trace_context import TraceContext
        agent_id = str(agent_input.run_id or "unknown")
        task_id = str(getattr(agent_input, "objective", "") or agent_id)[:80]
        complexity = "C2"
        if isinstance(agent_input.route_decision, dict):
            complexity = str(agent_input.route_decision.get("complexity", "C2"))
        ctx = TraceContext.root(
            task_id=task_id,
            tier=complexity,
            component="agent_runtime",
        )
        _get_emitter().task_start(ctx, agent_id=agent_id, task_id=task_id, tier=complexity, run_id=agent_id)
        # --- end trace ---

        # 1. Profile Injection
        if profile_ctx := self._get_profile_context():
            agent_input = replace(agent_input, objective=profile_ctx + agent_input.objective)

        # 2. Resolution
        agent_input = self._apply_zera_command_os(agent_input)
        resolution = self._resolution_for_input(agent_input)
        
        runtime_provider_name = str(resolution.get("runtime_provider") or self.default_provider)
        runtime_profile = resolution.get("runtime_profile")
        
        # 3. Connector Gating
        risk_report = self.connector_gater.check_intent_risk(resolution.get("intent", "analysis"))
        if risk_report["action"] == "pending_approval":
            ticket_id = self.connector_gater.request_approval(
                proposal={"intent": resolution.get("intent"), "complexity": resolution.get("complexity")},
                risk_report=risk_report,
                run_id=agent_input.run_id
            )
            _get_emitter().task_end(ctx, duration_ms=(time.perf_counter() - t_start) * 1000, status="blocked", agent_id=agent_id, ticket_id=ticket_id, run_id=agent_id)
            return AgentOutput(
                status="blocked",
                diff_summary=f"Execution paused: {risk_report['reason']}\n\n[ACTION REQUIRED] Created Approval Ticket #{ticket_id}. Please resolve to continue.",
                test_report={"status": "pending", "ticket_id": ticket_id},
                artifacts=[],
                next_action=f"Approve ticket {ticket_id} to authorize this intent class."
            )
        elif risk_report["action"] == "block":
            _get_emitter().task_error(ctx, error_type="connector_blocked", error_message=risk_report.get("reason", ""), agent_id=agent_id, run_id=agent_id)
            return AgentOutput(
                status="blocked",
                diff_summary=f"Execution blocked by ConnectorGater: {risk_report['reason']}",
                test_report={"status": "failed", "error": "security_gating_block"},
                artifacts=[],
                next_action="Review connector security policy or request manual override."
            )

        # 4. Provider Execution
        try:
            provider = self.runtime_registry.get_provider(runtime_provider_name)
            output = provider.run(
                agent_input,
                repo_root=self.repo_root,
                runtime_profile=str(runtime_profile) if runtime_profile else None,
            )
            
            # 3. Hybrid Quality Gates Execution
            gate_profile = "critical" if resolution.get("complexity") in ["C4", "C5"] else "standard"
            gate_results = self.quality_gate_manager.run_suite(gate_profile, {"resolution": resolution})
            
            sync_results = gate_results.get("sync_results", [])
            async_gates = gate_results.get("async_gates", [])

            # Attach gate results to metadata
            if isinstance(output.meta, dict):
                output.meta["quality_gates"] = [asdict(r) for r in sync_results]
                if async_gates:
                    output.meta["pending_async_gates"] = async_gates
            
            if any(r.status == "fail" for r in sync_results):
                output.status = "validation_failed"
                output.diff_summary += "\n\n[ERROR] Synchronous Quality Gates Failed. See metadata for details."

            elapsed_ms = (time.perf_counter() - t_start) * 1000
            _get_emitter().task_end(ctx, duration_ms=elapsed_ms, status=output.status, agent_id=agent_id, provider=runtime_provider_name, run_id=agent_id)

            # Background Job Handling (Fix: using keyword arguments)
            if resolution.get("background_jobs_supported"):
                enqueue_background_jobs_from_output(
                    repo_root=self.repo_root,
                    run_id=agent_input.run_id,
                    runtime_provider=runtime_provider_name,
                    runtime_profile=str(runtime_profile) if runtime_profile else None,
                    route_decision=resolution,
                    output_meta=output.meta
                )

            return output

        except TimeoutError as timeout_exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            _get_emitter().task_error(ctx, error_type="timeout", error_message=str(timeout_exc), agent_id=agent_id, run_id=agent_id)
            return self._fallback_or_fail(agent_input, resolution, timeout_exc, ctx)

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            _get_emitter().task_error(ctx, error_type=type(exc).__name__, error_message=str(exc), agent_id=agent_id, run_id=agent_id)
            return self._fallback_or_fail(agent_input, resolution, exc, ctx)

    def _get_profile_context(self) -> str:
        if not ProfileManager: return ""
        try:
            pm = ProfileManager(self.repo_root / "configs/orchestrator/user_profile.json")
            return pm.get_summary_context() + "\n"
        except Exception: return ""

    def _fallback_or_fail(
        self,
        agent_input: AgentInput,
        resolution: dict,
        error: Exception,
        ctx: Any = None,
    ) -> AgentOutput:
        fallback_chain = list(resolution.get("runtime_fallback_chain") or [])
        for fallback_provider in fallback_chain:
            try:
                provider = self.runtime_registry.get_provider(fallback_provider)
                return provider.run(agent_input, repo_root=self.repo_root)
            except Exception:
                continue

        # If no ctx was passed in, create one now for the final error emit
        if ctx is None:
            from .trace_context import TraceContext
            task_id = str(getattr(agent_input, "objective", "") or str(agent_input.run_id or "unknown"))[:80]
            complexity = "C2"
            if isinstance(agent_input.route_decision, dict):
                complexity = str(agent_input.route_decision.get("complexity", "C2"))
            ctx = TraceContext.root(task_id=task_id, tier=complexity, component="agent_runtime")

        _agent_id = str(agent_input.run_id or "unknown")
        _get_emitter().task_error(ctx, error_type=type(error).__name__, error_message=str(error), agent_id=_agent_id, run_id=_agent_id)

        # Fix: correctly initialized AgentOutput
        return AgentOutput(
            status="failed",
            diff_summary=f"Runtime execution failed and fallback exhausted: {error}",
            test_report={"status": "error", "error": str(error)},
            artifacts=[],
            next_action="Check provider availability and network connectivity."
        )

    @staticmethod
    def to_json(agent_output: AgentOutput) -> str:
        return json.dumps(asdict(agent_output), ensure_ascii=False, indent=2)
