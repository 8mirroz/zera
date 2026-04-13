from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from ..approval_engine import ApprovalEngine
from ..autonomy_policy import AutonomyPolicyEngine
from ..contracts import AgentInput, AgentOutput, MemoryStoreInput
from ..exceptions import RuntimeProviderExecutionError, RuntimeProviderUnavailableError
from ..goal_stack import GoalStack
from ..loop_guard import LoopGuard
from ..memory_store import MemoryStore
from ..observability import emit_event
from ..persona_eval import PersonaEvalSuite
from ..persona_mode_router import PersonaModeRouter
from ..reflection_policy import evaluate_reflection_payload
from ..risk_classifier import RiskClassifier
from ..security_policy import SecurityPolicy
from ..stop_controller import StopController
from .base import RuntimeProvider


class ZeroClawRuntimeProvider(RuntimeProvider):
    """Runtime provider bridge for ZeroClaw-compatible stdio execution."""

    name = "zeroclaw"

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
        persona_id = str(route_decision.get("persona_id") or profile_data.get("persona_id") or "")
        selected_mode = route_decision.get("mode")
        if not selected_mode and persona_id.startswith("zera"):
            selected_mode = PersonaModeRouter(repo_root).select_mode(agent_input.objective, default_mode="plan")
        security = SecurityPolicy(repo_root).validate_runtime_profile(runtime_profile, profile_data, provider_name=self.name)
        if not security.allowed:
            raise RuntimeProviderExecutionError("; ".join(security.issues))
        stop_controller = StopController(repo_root)
        if stop_controller.is_stopped(scope=persona_id or "global"):
            self._emit_stop_signal_events(
                agent_input=agent_input,
                route_decision=route_decision,
                selected_mode=str(selected_mode or "plan"),
                reason="Stop signal active before runtime execution",
            )
            return AgentOutput(
                status="completed",
                diff_summary="ZeroClaw execution skipped because a stop signal is active.",
                test_report={"status": "not-run", "details": "Stop signal honored before runtime execution."},
                artifacts=[],
                next_action="Clear stop signal to resume bounded autonomous execution.",
                response_text="Autonomous execution is paused right now. I did not queue or execute new actions.",
                meta={"selected_mode": selected_mode, "stop_honored": True},
            )

        emit_event(
            "agent_run_started",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": "ok",
                "message": "ZeroClaw runtime started",
                "objective": agent_input.objective,
                "route_decision": route_decision,
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
                "persona_id": persona_id or None,
                "mode": selected_mode,
                "approval_policy": route_decision.get("approval_policy"),
                "autonomy_mode": route_decision.get("autonomy_mode"),
            },
        )

        payload = {
            "run_id": agent_input.run_id,
            "objective": agent_input.objective,
            "plan_steps": list(agent_input.plan_steps),
            "route_decision": {**route_decision, "selected_mode": selected_mode},
        }

        result = self._execute_profile(repo_root=repo_root, runtime_profile=runtime_profile, profile_data=profile_data, payload=payload)
        output = self._to_agent_output(result)
        meta = dict(output.meta or {})
        meta.setdefault("selected_mode", selected_mode)
        output.meta = meta

        self._emit_autonomy_and_background(
            repo_root=repo_root,
            agent_input=agent_input,
            route_decision=route_decision,
            output=output,
            selected_mode=str(selected_mode or "plan"),
        )
        self._persist_memory_updates(repo_root=repo_root, agent_input=agent_input, output=output)

        duration_ms = int(time.time() * 1000) - start_ms
        emit_event(
            "verification_result",
            {
                "run_id": agent_input.run_id,
                "component": "verifier",
                "status": str((output.test_report or {}).get("status") or "ok"),
                "duration_ms": 0,
                "message": "Verification metadata captured from ZeroClaw execution adapter",
                "data": {
                    "verification_status": str((output.test_report or {}).get("status") or "not-run"),
                    "reason": str((output.test_report or {}).get("details") or "No verification details supplied"),
                    "hallucination": {
                        "unsupported_claims": 0,
                        "total_claims": 0,
                        "hallucination_rate": None,
                        "judge": "not-run",
                    },
                },
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
                "persona_id": persona_id or None,
                "mode": selected_mode,
            },
        )
        emit_event(
            "agent_run_completed",
            {
                "component": "agent",
                "run_id": agent_input.run_id,
                "status": output.status,
                "duration_ms": duration_ms,
                "message": "ZeroClaw runtime completed",
                "data": {
                    "artifacts_count": len(output.artifacts),
                    "repo_root": str(repo_root),
                    "mode": selected_mode,
                    "response_present": bool(output.response_text),
                },
                "runtime_provider": self.name,
                "runtime_profile": runtime_profile,
                "persona_id": persona_id or None,
                "mode": selected_mode,
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
        use_native_bin = str(os.getenv("ZEROCLAW_USE_NATIVE_BIN", "")).strip().lower() in {"1", "true", "yes", "on"}

        if execution_mode == "stdio_json" and isinstance(command, list) and command:
            chosen_command = native_command if use_native_bin and isinstance(native_command, list) and native_command else command
            return self._run_stdio_json_command(repo_root, chosen_command, timeout_seconds=timeout_seconds, payload=payload)

        if execution_mode == "zeroclaw_native" and isinstance(native_command, list) and native_command:
            return self._run_stdio_json_command(repo_root, native_command, timeout_seconds=timeout_seconds, payload=payload)

        zeroclaw_bin = self._resolve_zeroclaw_bin()
        self._health_probe(zeroclaw_bin)
        return {
            "status": "completed",
            "diff_summary": (
                "ZeroClaw runtime provider executed health probe and accepted run context. "
                "Repository mutations remain disabled in integration mode."
            ),
            "test_report": {
                "status": "not-run",
                "details": "ZeroClaw provider currently runs in health-probe mode.",
            },
            "artifacts": [],
            "next_action": (
                f"Configure a stdio_json command for runtime profile '{runtime_profile or 'default'}' to enable full execution."
            ),
            "meta": {},
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
            raise RuntimeProviderExecutionError(f"ZeroClaw stdio command failed: {exc}") from exc
        if proc.returncode != 0:
            stderr = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeProviderExecutionError(f"ZeroClaw stdio command exit={proc.returncode}: {stderr[:300]}")
        stdout = (proc.stdout or "").strip()
        if not stdout:
            raise RuntimeProviderExecutionError("ZeroClaw stdio command returned empty stdout")
        try:
            result = json.loads(stdout.splitlines()[-1])
        except Exception as exc:
            raise RuntimeProviderExecutionError(f"ZeroClaw stdio command returned non-JSON output: {exc}") from exc
        if not isinstance(result, dict):
            raise RuntimeProviderExecutionError("ZeroClaw stdio command returned unexpected payload shape")
        return result

    def _emit_autonomy_and_background(
        self,
        *,
        repo_root: Path,
        agent_input: AgentInput,
        route_decision: dict[str, Any],
        output: AgentOutput,
        selected_mode: str,
    ) -> None:
        meta = output.meta if isinstance(output.meta, dict) else {}
        self._emit_persona_eval(repo_root=repo_root, agent_input=agent_input, route_decision=route_decision, output=output, selected_mode=selected_mode)
        persona_scope = str(route_decision.get("persona_id") or "global")
        approvals = ApprovalEngine(repo_root)
        stop_controller = StopController(repo_root)
        if stop_controller.is_stopped(scope=persona_scope):
            self._emit_stop_signal_events(
                agent_input=agent_input,
                route_decision=route_decision,
                selected_mode=selected_mode,
                reason="Stop signal active during autonomy/background emission",
            )
            return

        reflection = meta.get("self_reflection")
        if isinstance(reflection, dict):
            reflection_result = evaluate_reflection_payload(repo_root, reflection, run_id=agent_input.run_id)
            if reflection_result.valid:
                if reflection_result.decision == "auto_apply_memory_tag" and isinstance(reflection_result.memory_update, dict):
                    updates = meta.get("memory_updates", [])
                    if not isinstance(updates, list):
                        updates = []
                    updates.append(reflection_result.memory_update)
                    meta["memory_updates"] = updates
                emit_event(
                    "self_reflection_written",
                    {
                        "run_id": agent_input.run_id,
                        "component": "eval",
                        "status": "ok",
                        "message": str(reflection.get("summary") or "Runtime self-reflection captured"),
                        "runtime_provider": self.name,
                        "persona_id": route_decision.get("persona_id"),
                        "mode": selected_mode,
                        "data": {
                            **reflection,
                            "schema_name": reflection_result.schema_name,
                            "schema_version": reflection_result.schema_version,
                            "decision": reflection_result.decision,
                            "review_reasons": list(reflection_result.review_reasons),
                            "memory_update_key": (
                                str((reflection_result.memory_update or {}).get("key") or "")
                                if reflection_result.decision == "auto_apply_memory_tag"
                                else None
                            ),
                        },
                    },
                )
                if reflection_result.decision == "review_required":
                    bounded_action = reflection.get("bounded_action") if isinstance(reflection.get("bounded_action"), dict) else {}
                    risk_assessment = reflection.get("risk_assessment") if isinstance(reflection.get("risk_assessment"), dict) else {}
                    ticket = approvals.create_ticket(
                        action_type=str(bounded_action.get("action_type") or "request_operator_review"),
                        risk_class=str(risk_assessment.get("risk_level") or "unknown"),
                        summary=str(reflection.get("summary") or "Self-reflection proposal"),
                        run_id=agent_input.run_id,
                        runtime_provider=self.name,
                        persona_id=str(route_decision.get("persona_id") or "") or None,
                        approval_policy=str(route_decision.get("approval_policy") or "") or None,
                        proposal={
                            "self_reflection": reflection,
                            "reflection_policy": reflection_result.to_dict(),
                        },
                    )
                    emit_event(
                        "approval_gate_triggered",
                        {
                            "run_id": agent_input.run_id,
                            "component": "policy",
                            "status": "warn",
                            "message": "Self-reflection proposal requires operator review",
                            "runtime_provider": self.name,
                            "persona_id": route_decision.get("persona_id"),
                            "mode": selected_mode,
                            "approval_policy": route_decision.get("approval_policy"),
                            "approval_ticket_id": ticket.id,
                            "risk_class": str(risk_assessment.get("risk_level") or "unknown"),
                            "data": {
                                "action_type": str(bounded_action.get("action_type") or "request_operator_review"),
                                "proposal_title": str(reflection.get("summary") or "Self-reflection proposal"),
                                "approval_ticket_id": ticket.id,
                                "reflection_policy": reflection_result.to_dict(),
                            },
                        },
                    )
            else:
                emit_event(
                    "self_reflection_invalid",
                    {
                        "run_id": agent_input.run_id,
                        "component": "eval",
                        "status": "error",
                        "message": "Self-reflection rejected by reflection policy",
                        "runtime_provider": self.name,
                        "persona_id": route_decision.get("persona_id"),
                        "mode": selected_mode,
                        "data": {
                            "reflection_policy": reflection_result.to_dict(),
                            "provided_fields": sorted(reflection.keys()),
                        },
                    },
                )

        policy = AutonomyPolicyEngine(repo_root)
        risk_classifier = RiskClassifier()
        loop_guard = LoopGuard(repo_root, budget_profile=str(route_decision.get("approval_policy") or route_decision.get("budget_profile") or ""))
        goal_stack = GoalStack(repo_root)
        proposals = meta.get("initiative_proposals", [])
        signatures_seen: dict[str, int] = {}
        processed_actions = 0
        if isinstance(proposals, list):
            for proposal in proposals:
                if not isinstance(proposal, dict):
                    continue
                title = str(proposal.get("title") or "").strip() or "Untitled initiative"
                action_type = str(proposal.get("action_type") or "unknown").strip()
                loop_decision = loop_guard.decide(
                    proposal,
                    signatures_seen=signatures_seen,
                    total_actions_seen=processed_actions,
                    max_actions=route_decision.get("max_actions"),
                )
                signatures_seen[loop_decision.signature] = signatures_seen.get(loop_decision.signature, 0) + 1
                if loop_decision.blocked:
                    event_type = "budget_limit_hit" if loop_decision.budget_limit_hit else "loop_guard_triggered"
                    emit_event(
                        event_type,
                        {
                            "run_id": agent_input.run_id,
                            "component": "policy",
                            "status": "warn",
                            "message": loop_decision.reason,
                            "runtime_provider": self.name,
                            "persona_id": route_decision.get("persona_id"),
                            "mode": selected_mode,
                            "data": {
                                **loop_decision.to_dict(),
                                "proposal": proposal,
                            },
                        },
                    )
                    continue
                decision = policy.evaluate(action_type)
                risk = risk_classifier.classify(action_type, approval_gates=list(route_decision.get("approval_gates") or []))
                requires_approval = decision.requires_approval or risk.requires_gate
                emit_event(
                    "autonomy_decision",
                    {
                        "run_id": agent_input.run_id,
                        "component": "policy",
                        "status": "ok" if decision.allowed and not requires_approval else ("warn" if requires_approval else "error"),
                        "message": decision.reason,
                        "runtime_provider": self.name,
                        "persona_id": route_decision.get("persona_id"),
                        "mode": selected_mode,
                        "approval_policy": route_decision.get("approval_policy"),
                        "autonomy_mode": route_decision.get("autonomy_mode"),
                        "risk_class": risk.risk_class,
                        "data": {
                            **decision.to_dict(),
                            "risk": risk.to_dict(),
                            "proposal": proposal,
                        },
                    },
                )
                if decision.blocked or requires_approval:
                    ticket = approvals.create_ticket(
                        action_type=action_type,
                        risk_class=risk.risk_class,
                        summary=title,
                        run_id=agent_input.run_id,
                        runtime_provider=self.name,
                        persona_id=str(route_decision.get("persona_id") or "") or None,
                        approval_policy=str(route_decision.get("approval_policy") or "") or None,
                        proposal=proposal,
                    )
                    emit_event(
                        "approval_gate_triggered",
                        {
                            "run_id": agent_input.run_id,
                            "component": "policy",
                            "status": "warn" if requires_approval else "error",
                            "message": decision.reason,
                            "runtime_provider": self.name,
                            "persona_id": route_decision.get("persona_id"),
                            "mode": selected_mode,
                            "approval_policy": route_decision.get("approval_policy"),
                            "approval_ticket_id": ticket.id,
                            "risk_class": risk.risk_class,
                            "data": {
                                "action_type": action_type,
                                "proposal_title": title,
                                "blocked": decision.blocked,
                                "requires_approval": requires_approval,
                                "approval_ticket_id": ticket.id,
                                "risk": risk.to_dict(),
                            },
                        },
                    )
                    continue
                goal = goal_stack.push(title, action_type, metadata={"run_id": agent_input.run_id, "proposal": proposal})
                processed_actions += 1
                emit_event(
                    "goal_stack_updated",
                    {
                        "run_id": agent_input.run_id,
                        "component": "memory",
                        "status": "ok",
                        "message": f"Goal queued: {goal.title}",
                            "runtime_provider": self.name,
                            "persona_id": route_decision.get("persona_id"),
                            "mode": selected_mode,
                            "data": goal.to_dict(),
                        },
                    )
                if route_decision.get("proof_required"):
                    emit_event(
                        "proof_of_action_recorded",
                        {
                            "run_id": agent_input.run_id,
                            "component": "agent",
                            "status": "ok",
                            "message": f"Proof recorded for queued goal '{goal.title}'",
                            "runtime_provider": self.name,
                            "persona_id": route_decision.get("persona_id"),
                            "mode": selected_mode,
                            "data": {
                                "goal_id": goal.id,
                                "action_type": action_type,
                                "proof": {
                                    "goal_title": goal.title,
                                    "queued_at": goal.created_at,
                                },
                            },
                        },
                    )

    def _emit_persona_eval(
        self,
        *,
        repo_root: Path,
        agent_input: AgentInput,
        route_decision: dict[str, Any],
        output: AgentOutput,
        selected_mode: str,
    ) -> None:
        response_text = str(output.response_text or "")
        if not response_text:
            return
        persona_version = str(route_decision.get("persona_version") or route_decision.get("persona_id") or "unknown")
        result = PersonaEvalSuite(repo_root).score(
            response_text=response_text,
            persona_version=persona_version,
            mode=selected_mode,
            meta=output.meta if isinstance(output.meta, dict) else {},
        )
        emit_event(
            "persona_eval_scored",
            {
                "run_id": agent_input.run_id,
                "component": "eval",
                "status": "pass" if result.passed else "fail",
                "message": f"Persona evaluation scored for {persona_version}",
                "runtime_provider": self.name,
                "persona_id": route_decision.get("persona_id"),
                "mode": selected_mode,
                "data": result.to_dict(),
            },
        )

    def _persist_memory_updates(
        self,
        *,
        repo_root: Path,
        agent_input: AgentInput,
        output: AgentOutput,
    ) -> None:
        meta = output.meta if isinstance(output.meta, dict) else {}
        updates = meta.get("memory_updates", [])
        if not isinstance(updates, list):
            return

        # Route memory writes through MemoryPolicyLayer for scope enforcement (R-002 fix)
        try:
            from ..memory_policy_layer import MemoryPolicyLayer
            policy = MemoryPolicyLayer(repo_root)
        except Exception:
            policy = None

        for row in updates:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key") or f"run:{agent_input.run_id}")
            payload = dict(row.get("payload") or {})
            options = dict(row.get("options") or {})
            scope = str(options.get("scope") or options.get("memory_class") or "session")

            if policy is not None:
                # Write through policy layer — enforces scope, TTL, write_rules
                policy.write(
                    key=key,
                    payload=payload,
                    scope=scope,
                )
            else:
                # Fallback: direct store write (degraded mode)
                from ..memory_store import MemoryStore
                from ..contracts import MemoryStoreInput
                store = MemoryStore(repo_root)
                store.operate(
                    MemoryStoreInput(
                        op="write",
                        key=key,
                        payload=payload,
                        correlation_id=agent_input.run_id,
                        options=options,
                    )
                )

    def _emit_stop_signal_events(
        self,
        *,
        agent_input: AgentInput,
        route_decision: dict[str, Any],
        selected_mode: str,
        reason: str,
    ) -> None:
        base_payload = {
            "run_id": agent_input.run_id,
            "component": "policy",
            "runtime_provider": self.name,
            "persona_id": route_decision.get("persona_id"),
            "mode": selected_mode,
            "message": reason,
            "data": {
                "stop_token": route_decision.get("stop_token"),
                "stop_conditions": route_decision.get("stop_conditions"),
            },
        }
        emit_event("stop_signal_received", {"status": "warn", **base_payload})
        emit_event("stop_signal_honored", {"status": "completed", **base_payload})

    @staticmethod
    def _to_agent_output(result: dict[str, Any]) -> AgentOutput:
        return AgentOutput(
            status=str(result.get("status") or "failed"),
            diff_summary=str(result.get("diff_summary") or "ZeroClaw execution returned no summary."),
            test_report=dict(result.get("test_report") or {}),
            artifacts=list(result.get("artifacts") or []),
            next_action=str(result.get("next_action") or ""),
            response_text=str(result.get("response_text") or "") or None,
            meta=dict(result.get("meta") or {}),
        )

    @staticmethod
    def _resolve_arg(repo_root: Path, value: Any) -> str:
        raw = str(value)
        if raw == "__ZEROCLAW_BIN__":
            return ZeroClawRuntimeProvider._resolve_zeroclaw_bin()
        if "/" in raw and not os.path.isabs(raw):
            candidate = repo_root / raw
            if candidate.exists():
                return str(candidate)
        return raw

    @staticmethod
    def _resolve_zeroclaw_bin() -> str:
        raw = (os.getenv("ZEROCLAW_BIN") or "").strip()
        if raw:
            if os.path.isabs(raw) and os.path.exists(raw):
                return raw
            resolved = shutil.which(raw)
            if resolved:
                return resolved
        resolved = shutil.which("zeroclaw")
        if resolved:
            return resolved
        raise RuntimeProviderUnavailableError(
            "ZeroClaw binary not found. Install `zeroclaw` or set ZEROCLAW_BIN."
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
            raise RuntimeProviderExecutionError(f"ZeroClaw health probe failed: {exc}") from exc
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise RuntimeProviderExecutionError(
                f"ZeroClaw health probe exit={proc.returncode}: {stderr[:300]}"
            )
