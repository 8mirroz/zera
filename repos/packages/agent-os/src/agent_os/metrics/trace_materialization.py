#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUCCESS_STATUSES = {"ok", "pass", "success", "completed"}
FAIL_STATUSES = {"error", "fail", "failure"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _complexity_num(value: Any) -> int | None:
    if not isinstance(value, str) or not value.startswith("C"):
        return None
    try:
        return int(value[1:])
    except Exception:
        return None


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _safe_data(row: dict[str, Any]) -> dict[str, Any]:
    data = row.get("data")
    return data if isinstance(data, dict) else {}


def _legacy_to_v2_events(row: dict[str, Any]) -> list[dict[str, Any]]:
    entry = row.get("entry")
    if not isinstance(entry, dict):
        return []
    run_id = str(entry.get("run_id") or "")
    ts = entry.get("timestamp") or utc_now_iso()
    task_type = entry.get("task_type")
    complexity = entry.get("complexity")

    out: list[dict[str, Any]] = []

    task_summary = {
        "ts": ts,
        "run_id": run_id,
        "event_type": "task_run_summary",
        "level": "info",
        "component": "agent",
        "task_type": task_type,
        "complexity": complexity,
        "status": entry.get("outcome") or "completed",
        "message": "Migrated from legacy trace entry",
        "data": {
            "path": entry.get("path"),
            "tools_used": entry.get("tools_used", []),
            "tool_calls_total": entry.get("tool_calls_total"),
            "tool_calls_success": entry.get("tool_calls_success"),
            "tokens_input": entry.get("tokens_input"),
            "tokens_output": entry.get("tokens_output"),
            "duration_seconds": entry.get("duration_seconds"),
            "ki_generated": entry.get("ki_generated"),
            "pattern_extracted": entry.get("pattern_extracted"),
            "escalation_reason": entry.get("escalation_reason"),
        },
    }
    out.append(task_summary)

    ralph = entry.get("ralph_loop")
    if isinstance(ralph, dict):
        out.append(
            {
                "ts": ts,
                "run_id": run_id,
                "event_type": "ralph_iteration_scored",
                "level": "info",
                "component": "ralph",
                "task_type": task_type,
                "complexity": complexity,
                "status": "ok" if bool(ralph.get("enabled", True)) else "completed",
                "model": ralph.get("model_used"),
                "message": "Migrated Ralph loop score snapshot",
                "data": {
                    "ralph_loop": ralph,
                    "weighted_total": ((ralph.get("score") or {}).get("weighted_total") if isinstance(ralph.get("score"), dict) else None),
                },
            }
        )

    retro_needed = bool(entry.get("ki_generated")) or bool(entry.get("pattern_extracted")) or entry.get("event") == "retro_written"
    if retro_needed:
        out.append(
            {
                "ts": ts,
                "run_id": run_id,
                "event_type": "retro_written",
                "level": "info",
                "component": "retro",
                "task_type": task_type,
                "complexity": complexity,
                "status": "ok",
                "message": "Migrated retro signal from legacy trace entry",
                "data": {
                    "ki_generated": bool(entry.get("ki_generated")),
                    "pattern_extracted": bool(entry.get("pattern_extracted")),
                    "legacy_event": entry.get("event"),
                },
            }
        )

    return out


def _normalize_trace_rows(trace_file: Path, *, allow_legacy: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [line for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    events: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    stats = {
        "lines_total": len(rows),
        "v2_rows": 0,
        "legacy_rows": 0,
        "invalid_rows": 0,
    }
    for idx, line in enumerate(rows, start=1):
        try:
            row = json.loads(line)
        except Exception as e:
            stats["invalid_rows"] += 1
            errors.append({"line": idx, "error": f"invalid json: {e}"})
            continue
        if not isinstance(row, dict):
            stats["invalid_rows"] += 1
            errors.append({"line": idx, "error": "row must be object"})
            continue

        if "schema_version" in row and "entry" in row:
            if not allow_legacy:
                stats["invalid_rows"] += 1
                errors.append({"line": idx, "error": "legacy row encountered but allow_legacy=false"})
                continue
            stats["legacy_rows"] += 1
            events.extend(_legacy_to_v2_events(row))
            continue

        if "event_type" in row:
            stats["v2_rows"] += 1
            ev = dict(row)
            if not isinstance(ev.get("data"), dict):
                ev["data"] = {}
            events.append(ev)
            continue

        stats["invalid_rows"] += 1
        errors.append({"line": idx, "error": "unrecognized trace row format"})

    return events, {"stats": stats, "errors": errors}


def _ratio(numer: int, denom: int) -> float | None:
    if denom <= 0:
        return None
    return round(numer / denom, 4)


def materialize_metrics(trace_file: Path, *, allow_legacy: bool, include_dimensions: bool = True) -> dict[str, Any]:
    events, norm = _normalize_trace_rows(trace_file, allow_legacy=allow_legacy)
    stats = norm["stats"]
    errors = norm["errors"]

    by_type = Counter()
    runs_seen: set[str] = set()
    runs_with_policy_violation: set[str] = set()
    runs_with_retro: set[str] = set()
    runs_eligible_capture: set[str] = set()

    verification_total = 0
    verification_pass = 0
    verification_fail = 0

    tool_total = 0
    tool_success = 0

    fallback_tool_total = 0
    fallback_tool_success = 0

    task_summary_total = 0
    task_summary_success = 0
    task_summary_first_pass_success = 0
    task_summary_escalated = 0
    task_summary_fail = 0
    fallback_total = 0
    fallback_success = 0
    background_started = 0
    background_completed = 0
    persona_eval_total = 0
    persona_eval_pass = 0
    memory_retrieval_total = 0
    memory_retrieval_with_hits = 0
    autonomy_decision_total = 0
    approval_gate_total = 0
    stop_signal_received_total = 0
    stop_signal_honored_total = 0
    proof_of_action_total = 0
    budget_limit_total = 0
    self_reflection_written_total = 0
    self_reflection_rejected_total = 0
    self_reflection_with_schema_meta_total = 0
    harness_validation_started_total = 0
    harness_validation_completed_total = 0
    harness_evidence_total = 0
    doc_gardening_issue_total = 0

    ralph_scores_by_run: dict[str, list[float]] = defaultdict(list)
    dimensions: dict[str, Counter] = {
        "task_type": Counter(),
        "complexity": Counter(),
        "model_tier": Counter(),
        "model": Counter(),
        "event_type": Counter(),
        "component": Counter(),
        "runtime_provider": Counter(),
        "persona_version": Counter(),
        "mode": Counter(),
        "background_job_type": Counter(),
    }

    for ev in events:
        event_type = str(ev.get("event_type") or "")
        run_id = str(ev.get("run_id") or "")
        data = _safe_data(ev)
        by_type[event_type] += 1
        if run_id:
            runs_seen.add(run_id)

        if include_dimensions:
            for key in (
                "task_type",
                "complexity",
                "model_tier",
                "model",
                "event_type",
                "component",
                "runtime_provider",
                "mode",
                "background_job_type",
            ):
                value = ev.get(key) if key in {"event_type", "component"} else ev.get(key)
                if isinstance(value, str) and value:
                    dimensions[key][value] += 1
            persona_version = data.get("persona_version")
            if isinstance(persona_version, str) and persona_version:
                dimensions["persona_version"][persona_version] += 1

        if event_type == "policy_violation_detected" and run_id:
            runs_with_policy_violation.add(run_id)
            if isinstance(data.get("reflection_validation"), dict):
                self_reflection_rejected_total += 1

        if event_type == "retro_written" and run_id:
            runs_with_retro.add(run_id)

        complexity = ev.get("complexity")
        comp_num = _complexity_num(complexity)
        if event_type in {"triage_decision", "task_run_summary"} and run_id and comp_num is not None and comp_num >= 3:
            runs_eligible_capture.add(run_id)

        if event_type == "verification_result":
            verification_total += 1
            status = str(ev.get("status") or "").lower()
            if status in SUCCESS_STATUSES:
                verification_pass += 1
            elif status in FAIL_STATUSES:
                verification_fail += 1

        if event_type == "tool_call":
            tool_total += 1
            status = str(ev.get("status") or "").lower()
            if status in SUCCESS_STATUSES:
                tool_success += 1

        if event_type == "task_run_summary":
            task_summary_total += 1
            status = str(ev.get("status") or "").lower()
            if status in SUCCESS_STATUSES:
                task_summary_success += 1
                # First pass success: successful without escalation
                if not data.get("escalation_reason"):
                    task_summary_first_pass_success += 1
            elif status in FAIL_STATUSES:
                task_summary_fail += 1
            elif status == "escalated":
                task_summary_escalated += 1

            # Fallback tool stats if detailed tool_call events are missing.
            fallback_tool_total += max(0, _as_int(data.get("tool_calls_total"), 0))
            fallback_tool_success += max(0, _as_int(data.get("tool_calls_success"), 0))

        if event_type == "runtime_provider_fallback":
            fallback_total += 1
            status = str(ev.get("status") or "").lower()
            if status in SUCCESS_STATUSES or status == "warn":
                fallback_success += 1

        if event_type == "background_job_started":
            background_started += 1

        if event_type == "background_job_completed":
            background_completed += 1

        if event_type == "persona_eval_scored":
            persona_eval_total += 1
            status = str(ev.get("status") or "").lower()
            if status in SUCCESS_STATUSES or status == "pass":
                persona_eval_pass += 1

        if event_type == "memory_retrieval_scored":
            memory_retrieval_total += 1
            if _as_int(data.get("hits"), 0) > 0:
                memory_retrieval_with_hits += 1

        if event_type == "autonomy_decision":
            autonomy_decision_total += 1

        if event_type == "approval_gate_triggered":
            approval_gate_total += 1

        if event_type == "stop_signal_received":
            stop_signal_received_total += 1

        if event_type == "stop_signal_honored":
            stop_signal_honored_total += 1

        if event_type == "proof_of_action_recorded":
            proof_of_action_total += 1

        if event_type == "budget_limit_hit":
            budget_limit_total += 1

        if event_type == "self_reflection_written":
            self_reflection_written_total += 1
            if data.get("schema_version") and data.get("schema_name"):
                self_reflection_with_schema_meta_total += 1

        if event_type == "harness_validation_started":
            harness_validation_started_total += 1

        if event_type == "harness_validation_completed":
            harness_validation_completed_total += 1

        if event_type == "harness_evidence_collected":
            harness_evidence_total += 1

        if event_type == "doc_gardening_issue_found":
            doc_gardening_issue_total += 1

        if event_type == "ralph_iteration_scored":
            score = _as_float(data.get("weighted_total"))
            if score is None:
                ralph = data.get("ralph_loop")
                if isinstance(ralph, dict):
                    rscore = ralph.get("score")
                    if isinstance(rscore, dict):
                        score = _as_float(rscore.get("weighted_total"))
            if score is not None and run_id:
                ralph_scores_by_run[run_id].append(score)

    pass_rate_source = "verification_result" if verification_total > 0 else ("task_run_summary_fallback" if task_summary_total > 0 else "unavailable")
    pass_rate_numer = verification_pass if verification_total > 0 else task_summary_success
    pass_rate_denom = verification_total if verification_total > 0 else task_summary_total

    tool_source = "tool_call" if tool_total > 0 else ("task_run_summary_fallback" if fallback_tool_total > 0 else "unavailable")
    tool_numer = tool_success if tool_total > 0 else fallback_tool_success
    tool_denom = tool_total if tool_total > 0 else fallback_tool_total

    total_runs_for_compliance = len(runs_seen)
    compliant_runs = max(0, total_runs_for_compliance - len(runs_with_policy_violation))
    self_reflection_total_attempts = self_reflection_written_total + self_reflection_rejected_total

    ralph_run_uplifts: list[float] = []
    for _, scores in ralph_scores_by_run.items():
        if len(scores) < 2:
            continue
        uplift = max(scores) - scores[0]
        ralph_run_uplifts.append(round(uplift, 4))

    ralph_avg_uplift = round(sum(ralph_run_uplifts) / len(ralph_run_uplifts), 4) if ralph_run_uplifts else None

    result: dict[str, Any] = {
        "status": "ok",
        "generated_at": utc_now_iso(),
        "trace_file": str(trace_file),
        "allow_legacy": allow_legacy,
        "normalization": {
            **stats,
            "events_emitted_after_normalization": len(events),
            "normalization_errors_count": len(errors),
        },
        "event_counts": dict(sorted(by_type.items())),
        "kpis": {
            "pass_rate": {
                "value": _ratio(pass_rate_numer, pass_rate_denom),
                "numerator": pass_rate_numer,
                "denominator": pass_rate_denom,
                "source": pass_rate_source,
            },
            "first_pass_success_rate": {
                "value": _ratio(task_summary_first_pass_success, task_summary_total),
                "numerator": task_summary_first_pass_success,
                "denominator": task_summary_total,
                "source": "task_run_summary (без escalation_reason)",
            },
            "tool_success_rate": {
                "value": _ratio(tool_numer, tool_denom),
                "numerator": tool_numer,
                "denominator": tool_denom,
                "source": tool_source,
            },
            "capture_coverage": {
                "value": _ratio(len(runs_with_retro.intersection(runs_eligible_capture)), len(runs_eligible_capture)),
                "numerator": len(runs_with_retro.intersection(runs_eligible_capture)),
                "denominator": len(runs_eligible_capture),
                "source": "retro_written + triage_decision/task_run_summary (C3+)",
            },
            "escalation_rate": {
                "value": _ratio(task_summary_escalated, task_summary_total),
                "numerator": task_summary_escalated,
                "denominator": task_summary_total,
                "source": "task_run_summary",
            },
            "policy_compliance_rate": {
                "value": _ratio(compliant_runs, total_runs_for_compliance),
                "numerator": compliant_runs,
                "denominator": total_runs_for_compliance,
                "source": "policy_violation_detected",
            },
            "ralph_best_of_n_uplift": {
                "value": ralph_avg_uplift,
                "runs_with_multistep_ralph": len(ralph_run_uplifts),
                "runs_with_any_ralph_signal": len(ralph_scores_by_run),
                "source": "ralph_iteration_scored",
            },
            "flake_rate": {
                "value": None,
                "source": "verification_result",
                "note": "Requires explicit nondeterministic/flake signal in verification_result.data",
            },
            "runtime_provider_fallback_success": {
                "value": _ratio(fallback_success, fallback_total),
                "numerator": fallback_success,
                "denominator": fallback_total,
                "source": "runtime_provider_fallback",
            },
            "background_job_success_rate": {
                "value": _ratio(background_completed, background_started),
                "numerator": background_completed,
                "denominator": background_started,
                "source": "background_job_started/background_job_completed",
            },
            "persona_eval_pass_rate": {
                "value": _ratio(persona_eval_pass, persona_eval_total),
                "numerator": persona_eval_pass,
                "denominator": persona_eval_total,
                "source": "persona_eval_scored",
            },
            "memory_retrieval_hit_rate": {
                "value": _ratio(memory_retrieval_with_hits, memory_retrieval_total),
                "numerator": memory_retrieval_with_hits,
                "denominator": memory_retrieval_total,
                "source": "memory_retrieval_scored",
            },
            "autonomy_gate_rate": {
                "value": _ratio(approval_gate_total, autonomy_decision_total),
                "numerator": approval_gate_total,
                "denominator": autonomy_decision_total,
                "source": "autonomy_decision/approval_gate_triggered",
            },
            "stop_signal_compliance": {
                "value": _ratio(stop_signal_honored_total, stop_signal_received_total),
                "numerator": stop_signal_honored_total,
                "denominator": stop_signal_received_total,
                "source": "stop_signal_received/stop_signal_honored",
            },
            "proof_of_action_coverage": {
                "value": _ratio(proof_of_action_total, background_completed),
                "numerator": proof_of_action_total,
                "denominator": background_completed,
                "source": "proof_of_action_recorded/background_job_completed",
            },
            "budget_limit_hit_rate": {
                "value": _ratio(budget_limit_total, autonomy_decision_total),
                "numerator": budget_limit_total,
                "denominator": autonomy_decision_total,
                "source": "budget_limit_hit/autonomy_decision",
            },
            "self_reflection_valid_rate": {
                "value": _ratio(self_reflection_written_total, self_reflection_total_attempts),
                "numerator": self_reflection_written_total,
                "denominator": self_reflection_total_attempts,
                "source": "self_reflection_written/policy_violation_detected(reflection_validation)",
            },
            "self_reflection_rejection_rate": {
                "value": _ratio(self_reflection_rejected_total, self_reflection_total_attempts),
                "numerator": self_reflection_rejected_total,
                "denominator": self_reflection_total_attempts,
                "source": "policy_violation_detected(reflection_validation)",
            },
            "self_reflection_schema_coverage": {
                "value": _ratio(self_reflection_with_schema_meta_total, self_reflection_written_total),
                "numerator": self_reflection_with_schema_meta_total,
                "denominator": self_reflection_written_total,
                "source": "self_reflection_written.data(schema_name,schema_version)",
            },
            "harness_validation_completion_rate": {
                "value": _ratio(harness_validation_completed_total, harness_validation_started_total),
                "numerator": harness_validation_completed_total,
                "denominator": harness_validation_started_total,
                "source": "harness_validation_started/harness_validation_completed",
            },
            "harness_evidence_per_validation": {
                "value": _ratio(harness_evidence_total, harness_validation_started_total),
                "numerator": harness_evidence_total,
                "denominator": harness_validation_started_total,
                "source": "harness_evidence_collected/harness_validation_started",
            },
        },
        "run_counters": {
            "runs_seen": len(runs_seen),
            "runs_with_retro": len(runs_with_retro),
            "runs_eligible_capture_c3plus": len(runs_eligible_capture),
            "task_summary_total": task_summary_total,
            "task_summary_success": task_summary_success,
            "task_summary_first_pass_success": task_summary_first_pass_success,
            "task_summary_fail": task_summary_fail,
            "task_summary_escalated": task_summary_escalated,
            "fallback_total": fallback_total,
            "background_started": background_started,
            "background_completed": background_completed,
            "persona_eval_total": persona_eval_total,
            "memory_retrieval_total": memory_retrieval_total,
            "autonomy_decision_total": autonomy_decision_total,
            "stop_signal_received_total": stop_signal_received_total,
            "stop_signal_honored_total": stop_signal_honored_total,
            "proof_of_action_total": proof_of_action_total,
            "self_reflection_written_total": self_reflection_written_total,
            "self_reflection_rejected_total": self_reflection_rejected_total,
            "harness_validation_started_total": harness_validation_started_total,
            "harness_validation_completed_total": harness_validation_completed_total,
            "harness_evidence_total": harness_evidence_total,
            "doc_gardening_issue_total": doc_gardening_issue_total,
        },
        "errors": errors[:100],
    }

    if include_dimensions:
        result["dimensions"] = {k: dict(sorted(v.items())) for k, v in dimensions.items() if v}

    return result


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Materialize KPI snapshot from Agent OS trace JSONL (Trace Event v2 with optional legacy migration)")
    p.add_argument("--file", dest="trace_file", help="Trace file (defaults to AGENT_OS_TRACE_FILE or logs/agent_traces.jsonl)")
    p.add_argument("--allow-legacy", action="store_true", help="Normalize legacy {schema_version,entry} rows")
    p.add_argument("--no-dimensions", action="store_true", help="Skip dimensions counters in output")
    p.add_argument("--out", help="Write JSON result to file")
    p.add_argument("--json", action="store_true", help="Print JSON output (default)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    trace_file = Path(args.trace_file) if args.trace_file else Path(os.getenv("AGENT_OS_TRACE_FILE", str(root / "logs/agent_traces.jsonl")))
    if not trace_file.is_absolute():
        trace_file = root / trace_file
    try:
        result = materialize_metrics(trace_file, allow_legacy=bool(args.allow_legacy), include_dimensions=not bool(args.no_dimensions))
    except Exception as e:
        result = {"status": "error", "error": str(e)}

    if args.out and result.get("status") != "error":
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = root / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
