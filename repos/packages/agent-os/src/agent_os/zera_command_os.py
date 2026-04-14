from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .persona_mode_router import PersonaModeRouter
from .yaml_compat import parse_simple_yaml

try:  # pragma: no cover
    import yaml
except ModuleNotFoundError:  # pragma: no cover
    yaml = None


# Lazy-initialized trace emitter
_emitter: Any = None


def _get_emitter() -> Any:
    global _emitter
    if _emitter is None:
        from .trace_context import TraceSink, StructuredTraceEmitter, TraceContext
        _emitter = StructuredTraceEmitter(TraceSink(filename="agent_traces.jsonl"))
    return _emitter


_CAPABILITY_RANK = {
    "none": 0,
    "limited": 1,
    "full": 2,
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:  # pragma: no cover
        data = parse_simple_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must parse to a mapping")
    return data


class ZeraCommandOS:
    """Canonical Zera command registry and client-aware command resolver."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        tooling = self.repo_root / "configs" / "tooling"
        self.command_registry = _load_yaml(tooling / "zera_command_registry.yaml")
        self.client_profiles = _load_yaml(tooling / "zera_client_profiles.yaml")
        self.branching_policy = _load_yaml(tooling / "zera_branching_policy.yaml")
        self.research_registry = _load_yaml(tooling / "zera_research_registry.yaml")
        self.skill_foundry = _load_yaml(tooling / "zera_skill_foundry.yaml")
        self.external_imports = _load_yaml(tooling / "zera_external_imports.yaml")
        self.governance = json.loads((tooling / "zera_growth_governance.json").read_text(encoding="utf-8"))
        self.mode_router = PersonaModeRouter(self.repo_root)

    def list_commands(self) -> list[str]:
        commands = self.command_registry.get("commands", {})
        return sorted(commands) if isinstance(commands, dict) else []

    def command_catalog(self) -> list[dict[str, Any]]:
        commands = self.command_registry.get("commands", {})
        if not isinstance(commands, dict):
            return []
        rows: list[dict[str, Any]] = []
        for command_id in sorted(commands):
            row = commands[command_id]
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "command_id": command_id,
                    "mode_binding": row.get("mode_binding"),
                    "loop_binding": row.get("loop_binding"),
                    "allowed_clients": list(row.get("allowed_clients", [])),
                    "tool_profile": row.get("tool_profile"),
                    "approval_route": row.get("approval_route"),
                }
            )
        return rows

    def infer_command(self, objective: str) -> tuple[str, str, float]:
        normalized = str(objective or "").strip().lower()
        commands = self.command_registry.get("commands", {})
        best_id = str(self.command_registry.get("default_command") or "zera:plan")
        best_score = 0
        if isinstance(commands, dict):
            for command_id, row in commands.items():
                if not isinstance(row, dict):
                    continue
                keywords = row.get("inference_keywords", [])
                aliases = row.get("aliases", [])
                score = 0
                for keyword in list(keywords) + list(aliases):
                    key = str(keyword).strip().lower()
                    if key and key in normalized:
                        score += 1
                if score > best_score:
                    best_score = score
                    best_id = str(command_id)
        if best_score > 0:
            confidence = min(0.99, 0.5 + best_score * 0.12)
            return best_id, "keyword_or_alias_match", confidence

        selected_mode = self.mode_router.select_mode(objective, default_mode="plan")
        mode_defaults = self.command_registry.get("mode_defaults", {})
        if isinstance(mode_defaults, dict) and selected_mode in mode_defaults:
            return str(mode_defaults[selected_mode]), "mode_router_fallback", 0.51
        return best_id, "default_command", 0.35

    def _client_row(self, client_id: str) -> dict[str, Any]:
        clients = self.client_profiles.get("clients", {})
        if not isinstance(clients, dict) or client_id not in clients:
            raise ValueError(f"Unknown client: {client_id}")
        row = clients[client_id]
        if not isinstance(row, dict):
            raise ValueError(f"Invalid client profile: {client_id}")
        return row

    def _command_row(self, command_id: str) -> dict[str, Any]:
        commands = self.command_registry.get("commands", {})
        if not isinstance(commands, dict) or command_id not in commands:
            raise ValueError(f"Unknown command: {command_id}")
        row = commands[command_id]
        if not isinstance(row, dict):
            raise ValueError(f"Invalid command row: {command_id}")
        return row

    def _capability_sufficient(self, actual: str | None, required: str | None) -> bool:
        if required is None:
            return True
        return _CAPABILITY_RANK.get(str(actual or "none"), 0) >= _CAPABILITY_RANK.get(str(required or "none"), 0)

    def resolve_command(self, *, command_id: str | None, objective: str, client_id: str) -> dict[str, Any]:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=f"resolve_command:{client_id}", tier="C2", component="zera_command_os")
        t0 = time.perf_counter()
        emitter.task_start(ctx, command_id=command_id, client_id=client_id, objective_length=len(objective))

        try:
            requested = command_id
            decision_reason = "explicit_command"
            confidence = 1.0
            if not command_id:
                command_id, decision_reason, confidence = self.infer_command(objective)
            client_row = self._client_row(client_id)
            resolved_id = str(command_id)
            command_row = self._command_row(resolved_id)
            degraded = False
            degradation_reason: str | None = None

            supported = client_id in list(command_row.get("allowed_clients", []))
            required_caps = command_row.get("required_capabilities", {})
            if supported and isinstance(required_caps, dict):
                client_caps = client_row.get("capabilities", {})
                if isinstance(client_caps, dict):
                    for cap_name, required_value in required_caps.items():
                        actual = client_caps.get(cap_name)
                        if not self._capability_sufficient(str(actual or "none"), str(required_value or "none")):
                            supported = False
                            degradation_reason = f"client capability '{cap_name}' insufficient"
                            break

            if not supported:
                fallback = command_row.get("fallback", {})
                degrade_to = str(fallback.get("degrade_to") or "").strip() if isinstance(fallback, dict) else ""
                if not degrade_to:
                    raise ValueError(f"{client_id} cannot execute {resolved_id} and no fallback is defined")
                degraded = True
                degradation_reason = degradation_reason or str(fallback.get("reason") or "fallback required")
                resolved_id = degrade_to
                command_row = self._command_row(resolved_id)

            mode_binding = str(command_row.get("mode_binding") or "plan")
            if mode_binding == "fallback_router":
                mode_binding = self.mode_router.select_mode(objective, default_mode="plan")

            loop_binding = str(command_row.get("loop_binding") or "capability")

            result = {
                "requested_command_id": requested,
                "command_id": resolved_id,
                "client_id": client_id,
                "supported": not degraded,
                "degraded": degraded,
                "degradation_reason": degradation_reason,
                "decision_reason": decision_reason,
                "confidence": round(confidence, 3),
                "mode": mode_binding,
                "loop": loop_binding,
                "candidate_class": command_row.get("candidate_class"),
                "workflow_type": command_row.get("workflow_type"),
                "action_class_expectation": command_row.get("action_class_expectation"),
                "tool_profile": command_row.get("tool_profile"),
                "model_transport_tier": command_row.get("model_transport_tier"),
                "approval_route": command_row.get("approval_route"),
                "risk_level": command_row.get("risk_level"),
                "rollback_path": command_row.get("rollback_path"),
                "telemetry_schema": command_row.get("telemetry_schema", {}),
                "required_capabilities": required_caps if isinstance(required_caps, dict) else {},
            }

            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             command_id=resolved_id, client_id=client_id,
                             mode_binding=mode_binding, loop_binding=loop_binding,
                             confidence=round(confidence, 3), degraded=degraded)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise

    def render_prompt(self, *, command_id: str | None, objective: str, client_id: str, branch_manifest_path: str | None = None) -> dict[str, Any]:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=f"render_prompt:{client_id}", tier="C2", component="zera_command_os")
        t0 = time.perf_counter()
        emitter.task_start(ctx, command_id=command_id, client_id=client_id, branch_type=branch_manifest_path or "none")

        try:
            resolved = self.resolve_command(command_id=command_id, objective=objective, client_id=client_id)
            header = [
                "[ZERA COMMAND CONTEXT]",
                f"command_id: {resolved['command_id']}",
                f"client_id: {client_id}",
                f"mode: {resolved['mode']}",
                f"loop: {resolved['loop']}",
                f"workflow_type: {resolved['workflow_type']}",
                f"candidate_class: {resolved['candidate_class']}",
                f"tool_profile: {resolved['tool_profile']}",
                f"approval_route: {resolved['approval_route']}",
                f"decision_reason: {resolved['decision_reason']}",
                f"confidence: {resolved['confidence']}",
            ]
            if branch_manifest_path:
                header.append(f"branch_manifest_path: {branch_manifest_path}")
            header.extend(["", "[OBJECTIVE]", objective])
            prompt_text = "\n".join(header).strip() + "\n"

            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             command_id=resolved["command_id"], prompt_length=len(prompt_text),
                             branch_type=branch_manifest_path or "none")
            return {
                **resolved,
                "prompt": prompt_text,
            }
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise

    def create_branch_manifest(
        self,
        *,
        command_id: str,
        client_id: str,
        branch_type: str,
        objective: str,
        run_id: str,
        ttl_minutes: int | None = None,
    ) -> dict[str, Any]:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=f"branch_manifest:{run_id}", tier="C2", component="zera_command_os")
        t0 = time.perf_counter()
        emitter.task_start(ctx, branch_id=f"{branch_type}-{run_id}", branch_type=branch_type,
                           source_command=command_id, client_id=client_id)

        try:
            branch_types = self.branching_policy.get("branch_types", {})
            if not isinstance(branch_types, dict) or branch_type not in branch_types:
                raise ValueError(f"Unknown branch type: {branch_type}")
            branch_row = branch_types[branch_type]
            if not isinstance(branch_row, dict):
                raise ValueError(f"Invalid branch row: {branch_type}")
            if command_id not in list(branch_row.get("allowed_commands", [])):
                raise ValueError(f"{branch_type} is not allowed for {command_id}")
            resolved = self.resolve_command(command_id=command_id, objective=objective, client_id=client_id)
            defaults = self.branching_policy.get("defaults", {})
            storage = self.branching_policy.get("storage", {})
            manifest = {
                "branch_id": f"{branch_type}-{run_id}",
                "branch_type": branch_type,
                "parent_run_id": run_id,
                "source_command": resolved["command_id"],
                "origin_prompt": objective,
                "allowed_tools": [resolved["tool_profile"]],
                "max_turns": int(branch_row.get("max_turns", 6)),
                "ttl_minutes": int(ttl_minutes or defaults.get("ttl_minutes", 90)),
                "merge_policy": str(branch_row.get("merge_policy") or "summary_with_candidate_cards"),
                "candidate_emission_allowed": bool(branch_row.get("candidate_emission_allowed", True)),
                "stable_memory_write_allowed": bool(defaults.get("stable_memory_write_allowed", False)),
                "personality_promotion_allowed": bool(defaults.get("personality_promotion_allowed", False)),
                "storage_path": str(storage.get("branch_dir") or "${VAULT_PATH}/research/branches"),
            }
            if branch_row.get("requires_persona_review"):
                manifest["requires_persona_review"] = True

            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             branch_id=manifest["branch_id"], branch_type=branch_type,
                             source_command=command_id)
            return manifest
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise

    def create_source_card(
        self,
        *,
        source_id: str,
        source_name: str,
        extracted_components: list[str],
    ) -> dict[str, Any]:
        known_sources = self.research_registry.get("known_sources", {})
        if not isinstance(known_sources, dict) or source_name not in known_sources:
            raise ValueError(f"Unknown research source: {source_name}")
        source_row = known_sources[source_name]
        if not isinstance(source_row, dict):
            raise ValueError(f"Invalid source card source: {source_name}")
        return {
            "source_id": source_id,
            "source_name": source_name,
            "source_url": source_row.get("source_url"),
            "source_type": source_row.get("source_type"),
            "license": source_row.get("license"),
            "import_lane": source_row.get("import_lane"),
            "trust_score": source_row.get("trust_score"),
            "reverse_engineered_risk": source_row.get("reverse_engineered_risk"),
            "clean_room_required": source_row.get("clean_room_required"),
            "extracted_components": list(extracted_components),
            "allowed_usage_scope": source_row.get("allowed_usage_scope"),
        }

    def create_branch_merge_record(
        self,
        *,
        manifest: dict[str, Any],
        candidate_classification: str,
        summary: str,
        stable_memory_write_requested: bool = False,
        personality_promotion_requested: bool = False,
    ) -> dict[str, Any]:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=f"branch_merge:{manifest.get('branch_id', 'unknown')}",
                                tier="C2", component="zera_command_os")
        t0 = time.perf_counter()
        emitter.task_start(ctx, branch_id=manifest.get("branch_id"),
                           candidate_classification=candidate_classification,
                           summary_length=len(summary))

        try:
            classification = str(candidate_classification or "").strip().lower()
            allowed = {"capability", "personality", "mixed", "governance"}
            if not classification:
                raise ValueError("candidate classification is required for branch merge")
            if classification not in allowed:
                raise ValueError(f"Unsupported candidate classification: {classification}")
            if stable_memory_write_requested and not manifest.get("stable_memory_write_allowed", False):
                raise ValueError("stable memory writes are forbidden for this branch merge")
            if personality_promotion_requested and not manifest.get("personality_promotion_allowed", False):
                raise ValueError("personality promotion is forbidden for this branch merge")
            requires_review = classification in {"personality", "mixed", "governance"} or bool(manifest.get("requires_persona_review"))
            result = {
                "branch_id": manifest.get("branch_id"),
                "branch_type": manifest.get("branch_type"),
                "parent_run_id": manifest.get("parent_run_id"),
                "source_command": manifest.get("source_command"),
                "candidate_classification": classification,
                "summary": summary,
                "decision": "review_required" if requires_review else "eligible_for_eval",
                "stable_memory_write_requested": stable_memory_write_requested,
                "personality_promotion_requested": personality_promotion_requested,
                "requires_review": requires_review,
                "rollback_path": "discard branch artifacts and revert to pre-merge state",
            }

            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             branch_id=manifest.get("branch_id"), decision=result["decision"],
                             candidate_classification=classification)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise

    def evaluate_governor(
        self,
        *,
        axis_deltas: dict[str, int | float],
        cycle_significant_deltas: int,
        consecutive_regressions: int,
        router_rewrite: bool,
        review_approved: bool,
    ) -> dict[str, Any]:
        axes = self.governance.get("personality_governor", {}).get("axes", {})
        promotion_rules = self.governance.get("promotion_rules", {})
        max_significant = int(promotion_rules.get("max_significant_personality_deltas_per_cycle", 1))
        freeze_after = int(promotion_rules.get("freeze_after_consecutive_personality_regressions", 2))
        reasons: list[str] = []
        blocked = False
        freeze = False
        rollback = False
        requires_review = False
        significant_axes: list[str] = []

        for axis, raw_delta in axis_deltas.items():
            if axis not in axes:
                raise ValueError(f"Unknown governor axis: {axis}")
            delta = abs(float(raw_delta))
            axis_policy = axes[axis]
            soft = float(axis_policy.get("soft_delta_per_cycle", 1))
            hard = float(axis_policy.get("hard_delta_per_cycle", soft))
            freeze_threshold = float(axis_policy.get("freeze_threshold", hard))
            rollback_trigger = float(axis_policy.get("rollback_trigger", hard))
            if delta >= soft and delta > 0:
                significant_axes.append(axis)
            if delta > hard:
                blocked = True
                freeze = True
                reasons.append(f"{axis} exceeds hard delta budget")
            if delta >= freeze_threshold:
                blocked = True
                freeze = True
                reasons.append(f"{axis} reached freeze threshold")
            if delta >= rollback_trigger:
                rollback = True
            if axis == "emotional_closeness" and float(raw_delta) > 0 and not review_approved:
                blocked = True
                requires_review = True
                reasons.append("emotional closeness increase requires explicit review")

        if cycle_significant_deltas + len(significant_axes) > max_significant:
            blocked = True
            reasons.append("only one significant personality axis shift is allowed per cycle")
        if router_rewrite and significant_axes:
            blocked = True
            freeze = True
            reasons.append("router rewrite cannot be combined with a significant personality delta")
        if consecutive_regressions >= freeze_after:
            blocked = True
            freeze = True
            reasons.append("personality loop is frozen after repeated regressions")

        return {
            "blocked": blocked,
            "freeze": freeze,
            "rollback": rollback,
            "requires_review": requires_review,
            "reasons": reasons,
            "significant_axes": significant_axes,
        }

    def validate_import_activation(
        self,
        *,
        artifact_id: str,
        imported_files: list[str],
    ) -> dict[str, Any]:
        rows = self.external_imports.get("imports", [])
        row = None
        for candidate in rows:
            if isinstance(candidate, dict) and candidate.get("artifact_id") == artifact_id:
                row = candidate
                break
        if row is None:
            raise ValueError(f"Unknown import artifact: {artifact_id}")

        lane = str(row.get("import_lane") or "")
        blocked = False
        reasons: list[str] = []
        if lane in {"concept_reference_quarantine", "discovery_index_only"}:
            blocked = True
            reasons.append(f"{lane} artifacts cannot be activated into runtime code")
        if lane == "isolated_optional_component_only":
            for path in imported_files:
                normalized = str(path).lower()
                if "isolated" not in normalized and "optional" not in normalized:
                    blocked = True
                    reasons.append("GPL-isolated artifacts must stay within an isolated or optional boundary")
                    break
        if not row.get("rollback_path"):
            blocked = True
            reasons.append("import activation requires a rollback path")

        return {
            "artifact_id": artifact_id,
            "import_lane": lane,
            "blocked": blocked,
            "review_status": row.get("review_status"),
            "target_internal_subsystem": row.get("target_internal_subsystem"),
            "reasons": reasons,
        }


__all__ = ["ZeraCommandOS"]
