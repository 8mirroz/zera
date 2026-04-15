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
from .swarm.swarm_orchestrator import SwarmOrchestrator

# Execution Guards — pre/post-flight validation, stall detection, heartbeat
try:
    from .execution_guards import (
        ExecutionGuards,
        HeartbeatMonitor,
        ProgressSignal,
        ViolationLevel,
    )
except ImportError:
    ExecutionGuards = None  # type: ignore
    HeartbeatMonitor = None  # type: ignore
    ProgressSignal = None  # type: ignore
    ViolationLevel = None  # type: ignore

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


def _emit_heartbeat_event(ctx: Any, agent_id: str, tier: str, hb: Any) -> None:
    """Emit a heartbeat trace event."""
    try:
        _get_emitter().task_start(
            ctx,
            agent_id=agent_id,
            task_id=f"heartbeat-{agent_id}",
            tier=tier,
            run_id=agent_id,
        )
    except Exception:
        pass  # Heartbeat should never crash the runtime

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

        # Initialize Execution Guards (pre/post-flight, stall detection, heartbeat)
        self.execution_guards: ExecutionGuards | None = None
        self._heartbeat_monitor: HeartbeatMonitor | None = None
        if ExecutionGuards is not None:
            try:
                self.execution_guards = ExecutionGuards.from_config(self.repo_root)
            except Exception as e:
                logger.warning("Failed to initialize execution guards: %s", e)

        # Swarm Orchestrator
        self.swarm_orchestrator = SwarmOrchestrator(self.repo_root, self)

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
        doc_files = [
            "constitution.md",
            "identity.md",
            "tone.md",
            "safety.md",
            "relationship_boundaries.md",
            "execution_contract.md",  # Execution truth contract
        ]
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
            run_id=agent_id,
        )
        _get_emitter().task_start(ctx, agent_id=agent_id, task_id=task_id, tier=complexity)
        
        # Signal progress — execution starting
        if self.execution_guards and ProgressSignal is not None:
            self.execution_guards.signal_progress(
                ProgressSignal.STATE_TRANSITION,
                state="executing",
            )
            self.execution_guards.stall_detector.set_state("executing")
        
        # Start continuous background heartbeat monitor
        if self.execution_guards and HeartbeatMonitor is not None:
            self._heartbeat_monitor = HeartbeatMonitor(
                interval_seconds=self.execution_guards.heartbeat.interval_seconds,
                run_id=agent_id,
                stall_detector=self.execution_guards.stall_detector,
            )
            self._heartbeat_monitor.set_callback(lambda hb: _emit_heartbeat_event(ctx, agent_id, complexity, hb))
            self._heartbeat_monitor.start()

        # --- end trace ---

        # 1. Profile Injection
        if profile_ctx := self._get_profile_context():
            agent_input = replace(agent_input, objective=profile_ctx + agent_input.objective)

        # 2. Resolution
        agent_input = self._apply_zera_command_os(agent_input)
        resolution = self._resolution_for_input(agent_input)

        # --- Subagent/Swarm Lane Interception ---
        if resolution.get("lane") == "swarm" and not agent_input.swarm_mode:
            return self.swarm_orchestrator.coordinate(agent_input)

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
            _get_emitter().task_end(ctx, duration_ms=(time.perf_counter() - t_start) * 1000, status="blocked", agent_id=agent_id, ticket_id=ticket_id)
            return AgentOutput(
                status="blocked",
                diff_summary=f"Execution paused: {risk_report['reason']}\n\n[ACTION REQUIRED] Created Approval Ticket #{ticket_id}. Please resolve to continue.",
                test_report={"status": "pending", "ticket_id": ticket_id},
                artifacts=[],
                next_action=f"Approve ticket {ticket_id} to authorize this intent class."
            )
        elif risk_report["action"] == "block":
            _get_emitter().task_error(ctx, error_type="connector_blocked", error_message=risk_report.get("reason", ""), agent_id=agent_id)
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

            # 4. Execution Guards — Pre-flight + Post-flight validation
            if self.execution_guards:
                # Signal progress — tool execution completed
                if ProgressSignal is not None:
                    self.execution_guards.signal_progress(
                        ProgressSignal.TOOL_RESULT_RECEIVED,
                        state="verifying",
                        tool_call=runtime_provider_name,
                    )
                    self.execution_guards.stall_detector.set_state("verifying")
                
                # Emit heartbeat — provider execution completed
                if self.execution_guards.heartbeat.should_emit():
                    heartbeat_payload = self.execution_guards.heartbeat.emit()
                    if heartbeat_payload:
                        _get_emitter().task_start(
                            ctx,
                            agent_id=agent_id,
                            task_id=f"heartbeat-{agent_id}",
                            tier=complexity,
                            run_id=agent_id,
                        )
                        self.execution_guards.heartbeat.reset()
                
                # GAP 1 FIX: Pre-flight validation — validate response claims
                diff_summary = str(output.diff_summary or "")
                preflight_result = self.execution_guards.preflight_validate(
                    diff_summary,
                    tool_results=[],  # Provider results not directly accessible here
                )
                if not preflight_result.passed and isinstance(output.meta, dict):
                    output.meta["execution_guards_preflight"] = {
                        "passed": preflight_result.passed,
                        "violations": [
                            {"type": v.violation_type.value, "level": v.level.value, "message": v.message}
                            for v in preflight_result.violations
                        ],
                        "retry_message": preflight_result.retry_message,
                    }
                    # Append warning but don't reject (provider already ran)
                    output.diff_summary += "\n\n[GUARD] Preflight validation warnings. Response contains claims without evidence."
                
                # GAP 4 FIX: Post-flight grounding check — verify filesystem claims
                postflight_result = self.execution_guards.postflight_check(
                    diff_summary,
                    tool_results=[],
                    filesystem_root=self.repo_root,
                )
                if not postflight_result.passed and isinstance(output.meta, dict):
                    output.meta["execution_guards_postflight"] = {
                        "passed": postflight_result.passed,
                        "grounded_claims": postflight_result.grounded_claims,
                        "ungrounded_claims": postflight_result.ungrounded_claims,
                        "ungrounded_details": postflight_result.ungrounded_details,
                        "filesystem_verified": postflight_result.filesystem_verified,
                        "filesystem_failures": postflight_result.filesystem_failures,
                    }
                    output.diff_summary += "\n\n[GUARD] Post-flight grounding warnings. Some filesystem claims not verified."

                # Validate artifact summary on completion
                artifact_validation = self.execution_guards.validate_completion_artifacts(diff_summary)
                if not artifact_validation.passed and isinstance(output.meta, dict):
                    output.meta["execution_guards_artifact"] = {
                        "passed": artifact_validation.passed,
                        "violations": [
                            {"type": v.violation_type.value, "message": v.message}
                            for v in artifact_validation.violations
                        ],
                    }
                    # Append validation warnings to output
                    output.diff_summary += "\n\n[GUARD] Artifact summary validation warnings. See metadata for details."

                # Add violation summary to metadata
                if isinstance(output.meta, dict):
                    output.meta["execution_guards_summary"] = self.execution_guards.get_violation_summary()

            elapsed_ms = (time.perf_counter() - t_start) * 1000
            _get_emitter().task_end(ctx, duration_ms=elapsed_ms, status=output.status, agent_id=agent_id, provider=runtime_provider_name)

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

            # Stop continuous heartbeat monitor
            hb_stats = self._stop_heartbeat_monitor()
            if hb_stats and isinstance(output.meta, dict):
                output.meta["heartbeat_stats"] = hb_stats

            return output

        except TimeoutError as timeout_exc:
            # Stop heartbeat monitor on error
            self._stop_heartbeat_monitor()
            
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            _get_emitter().task_error(ctx, error_type="timeout", error_message=str(timeout_exc), agent_id=agent_id)
            # Signal stall due to timeout
            if self.execution_guards and ProgressSignal is not None:
                self.execution_guards.stall_detector.set_state("executing")
                stall_event = self.execution_guards.get_stall_event()
                if stall_event:
                    logger.warning("Stall detected during timeout: %s", stall_event.likely_cause.value)
            return self._fallback_or_fail(agent_input, resolution, timeout_exc, ctx)

        except Exception as exc:
            # Stop heartbeat monitor on error
            self._stop_heartbeat_monitor()
            
            elapsed_ms = (time.perf_counter() - t_start) * 1000
            _get_emitter().task_error(ctx, error_type=type(exc).__name__, error_message=str(exc), agent_id=agent_id)
            # Signal stall due to error
            if self.execution_guards and ProgressSignal is not None:
                self.execution_guards.stall_detector.set_state("failed")
                stall_event = self.execution_guards.get_stall_event()
                if stall_event:
                    logger.warning("Stall detected during error: %s", stall_event.likely_cause.value)
            return self._fallback_or_fail(agent_input, resolution, exc, ctx)

    def _get_profile_context(self) -> str:
        if not ProfileManager: return ""
        try:
            pm = ProfileManager(self.repo_root / "configs/orchestrator/user_profile.json")
            return pm.get_summary_context() + "\n"
        except Exception: return ""

    def _stop_heartbeat_monitor(self) -> dict[str, Any] | None:
        """Stop the background heartbeat monitor and return stats."""
        if self._heartbeat_monitor and self._heartbeat_monitor._running:
            return self._heartbeat_monitor.stop()
        return None

    def _fallback_or_fail(
        self,
        agent_input: AgentInput,
        resolution: dict,
        error: Exception,
        ctx: Any = None,
    ) -> AgentOutput:
        # GAP 3 FIX: Signal progress in fallback path
        if self.execution_guards and ProgressSignal is not None:
            self.execution_guards.stall_detector.set_state("executing")
            self.execution_guards.signal_progress(
                ProgressSignal.STATE_TRANSITION,
                state="executing",
            )
        
        fallback_chain = list(resolution.get("runtime_fallback_chain") or [])
        for fallback_provider in fallback_chain:
            try:
                provider = self.runtime_registry.get_provider(fallback_provider)
                output = provider.run(agent_input, repo_root=self.repo_root)
                
                # Signal progress on fallback success
                if self.execution_guards and ProgressSignal is not None:
                    self.execution_guards.signal_progress(
                        ProgressSignal.TOOL_RESULT_RECEIVED,
                        state="verifying",
                        tool_call=fallback_provider,
                    )
                
                return output
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

        # Signal stall on final failure
        if self.execution_guards and ProgressSignal is not None:
            self.execution_guards.stall_detector.set_state("failed")
        
        _agent_id = str(agent_input.run_id or "unknown")
        _get_emitter().task_error(ctx, error_type=type(error).__name__, error_message=str(error), agent_id=_agent_id)

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
