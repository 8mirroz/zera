"""Observability utilities for Agent OS trace and event emission."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class SessionTrace:
    """Backward-compatible session trace record."""

    trace_id: str
    start_time: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    task_type: str = ""
    complexity: str = ""
    model_used: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    tool_calls: int = 0
    duration_ms: float = 0
    cost_usd: float = 0.0
    outcome: str = ""


class TraceEmitter:
    """Legacy trace emitter kept for compatibility with existing tooling."""

    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = log_dir
        self.log_dir.mkdir(exist_ok=True, parents=True)
        self.log_file = self.log_dir / "agent_traces.jsonl"

    def emit(self, trace: SessionTrace) -> None:
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(trace), ensure_ascii=False) + "\n")

    def summary(self, last_n: int = 10) -> dict[str, Any]:
        traces = self.get_traces(last_n=last_n)
        total_tokens = sum(t.get("tokens_input", 0) + t.get("tokens_output", 0) for t in traces)
        total_cost = sum(t.get("cost_usd", 0) for t in traces)
        total_duration = sum(t.get("duration_ms", 0) for t in traces)
        return {
            "sessions": len(traces),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_duration_ms": round(total_duration / max(len(traces), 1), 3),
        }

    def get_traces(self, last_n: int = 100) -> list[dict[str, Any]]:
        if not self.log_file.exists():
            return []
        rows = [line for line in self.log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [json.loads(line) for line in rows[-last_n:]]

    def clear(self) -> None:
        if self.log_file.exists():
            self.log_file.unlink()


_TOP_LEVEL_EVENT_FIELDS = {
    "run_id",
    "level",
    "component",
    "task_type",
    "complexity",
    "model_tier",
    "model",
    "tool_name",
    "status",
    "duration_ms",
    "message",
    "runtime_provider",
    "runtime_profile",
    "persona_id",
    "persona_version",
    "mode",
    "background_job_type",
    "approval_policy",
    "autonomy_mode",
    "approval_ticket_id",
    "risk_class",
    "command_id",
    "requested_command_id",
    "client_id",
    "loop",
    "candidate_class",
    "workflow_type",
    "decision",
    "rollback_path",
    "approval_route",
    "target_layer",
    "governance_impact",
    "risk_level",
    "branch_id",
    "branch_type",
    "source_id",
    "import_lane",
    # Fields from configs/global/observability.yaml
    "workflow_name",
    "token_cost",
    "tool_calls",
    "success_rate",
    "retry_count",
    "quality_gate_failures",
    "user_acceptance",
    "memory_hit_rate",
    "region_profile_used",
    # Modular Suite v2/v3 Fields
    "intent_class",
    "arbitration_rule_id",
    "lane_selected",
    "risk_score_aggregate",
    "escalation_triggered",
    "memory_pollution_index",
    "gate_id",
    "gate_status",
    "slo_breach_detected",
    "recovery_action_id",
    "identity_persona_version",
}


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _default_component(event_type: str) -> str:
    if event_type.startswith("triage_"):
        return "triage"
    if event_type.startswith("route_"):
        return "router"
    if event_type.startswith("agent_") or event_type.startswith("bootstrap_"):
        return "agent"
    if event_type.startswith("tool_"):
        return "tool"
    if event_type.startswith("verification_"):
        return "verifier"
    if event_type.startswith("ralph_"):
        return "ralph"
    if event_type.startswith("retro_") or event_type.startswith("self_reflection_"):
        return "retro"
    if event_type.startswith("policy_") or event_type.startswith("approval_") or event_type.startswith("autonomy_"):
        return "policy"
    if event_type.startswith("memory_") or event_type.startswith("build_memory_") or event_type.startswith("goal_stack_"):
        return "memory"
    if event_type.startswith("eval_") or event_type.startswith("persona_eval_"):
        return "eval"
    if event_type.startswith("background_"):
        return "agent"
    if event_type.startswith("ml_"):
        return "ml"
    if event_type.startswith("gate_") or event_type.startswith("override_"):
        return "quality_gates"
    return "agent"


def _normalize_event_row(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    src = dict(payload or {})
    explicit_data = src.pop("data", None)

    row: dict[str, Any] = {
        "ts": _utc_now_iso(),
        "run_id": str(src.pop("run_id", "") or uuid4()),
        "event_type": event_type,
        "level": str(src.pop("level", "info") or "info"),
        "component": str(src.pop("component", "") or _default_component(event_type)),
        "data": {},
    }

    for key in _TOP_LEVEL_EVENT_FIELDS - {"run_id", "level", "component"}:
        value = src.pop(key, None)
        if value is not None:
            row[key] = value

    if isinstance(explicit_data, dict):
        row["data"].update(explicit_data)
    elif explicit_data is not None:
        row["data"]["value"] = explicit_data

    for key, value in src.items():
        row["data"][key] = value

    return row


def emit_event(event_type: str, payload: dict[str, Any]) -> None:
    trace_path = os.getenv("AGENT_OS_TRACE_FILE")
    if not trace_path:
        trace_path = str(Path("logs") / "agent_traces.jsonl")

    row = _normalize_event_row(event_type, payload)
    path = Path(trace_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def emit_events(events: list[dict[str, Any]]) -> None:
    for event in events:
        event_type = str(event.get("event_type") or "custom")
        payload = {k: v for k, v in event.items() if k != "event_type"}
        data = payload.pop("data", {})
        if isinstance(data, dict):
            payload.update(data)
        emit_event(event_type, payload)


def emit_workflow_event(
    workflow_name: str,
    status: str,
    *,
    duration_ms: float = 0,
    token_cost: float = 0.0,
    tool_calls: int = 0,
    quality_gate_failures: int = 0,
    retry_count: int = 0,
    memory_hit_rate: float = 0.0,
    region_profile_used: str = "",
    run_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Emit a structured workflow lifecycle event (observability.yaml contract)."""
    payload: dict[str, Any] = {
        "workflow_name": workflow_name,
        "status": status,
        "duration_ms": duration_ms,
        "token_cost": token_cost,
        "tool_calls": tool_calls,
        "quality_gate_failures": quality_gate_failures,
        "retry_count": retry_count,
        "memory_hit_rate": memory_hit_rate,
        "region_profile_used": region_profile_used,
        "component": "workflow",
    }
    if run_id:
        payload["run_id"] = run_id
    if extra:
        payload["data"] = extra
    emit_event("workflow_completed", payload)


def emit_zera_command_event(event_type: str, payload: dict[str, Any]) -> None:
    row = {
        "component": "agent",
        "target_layer": "zera_command_runtime",
        "governance_impact": "none",
        "eval_suite": [],
        "source": "scripts/zera_command_runtime.py",
    }
    row.update(payload)
    emit_event(event_type, row)
