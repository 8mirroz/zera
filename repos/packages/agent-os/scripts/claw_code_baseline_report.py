#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _provider(row: dict[str, Any]) -> str:
    return str(row.get("runtime_provider") or row.get("data", {}).get("runtime_provider") or "")


def _task_type(row: dict[str, Any]) -> str:
    top = str(row.get("task_type") or "").strip()
    if top:
        return top
    data = row.get("data", {})
    if isinstance(data, dict):
        nested = str(data.get("task_type") or "").strip()
        if nested:
            return nested
    return "unknown"


def _run_id(row: dict[str, Any]) -> str:
    return str(row.get("run_id") or "").strip()


def _percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    ranked = sorted(values)
    if len(ranked) == 1:
        return float(ranked[0])
    index = int(round((len(ranked) - 1) * max(0.0, min(1.0, pct))))
    return float(ranked[index])


def _build_experimental_candidates(
    selected: list[dict[str, Any]],
    completed: list[dict[str, Any]],
    fallback: list[dict[str, Any]],
    recovery: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    task_defaults = {
        "T2": {"timeout_seconds": 30, "max_chain_length": 2, "max_cost_usd_per_run": 0.02},
        "T3": {"timeout_seconds": 45, "max_chain_length": 3, "max_cost_usd_per_run": 0.03},
        "T4": {"timeout_seconds": 60, "max_chain_length": 4, "max_cost_usd_per_run": 0.05},
    }

    selected_by_run = {_run_id(row): row for row in selected if _run_id(row)}
    task_durations_ms: dict[str, list[int]] = {key: [] for key in task_defaults}
    task_selected_counts = Counter()
    task_fallback_counts = Counter()
    task_recovery_counts = Counter()

    for row in selected:
        task_selected_counts[_task_type(row)] += 1
    for row in fallback:
        run_id = _run_id(row)
        task_type = _task_type(selected_by_run.get(run_id, {})) if run_id else "unknown"
        task_fallback_counts[task_type] += 1
    for row in recovery:
        run_id = _run_id(row)
        task_type = _task_type(selected_by_run.get(run_id, {})) if run_id else "unknown"
        task_recovery_counts[task_type] += 1
    for row in completed:
        run_id = _run_id(row)
        if not run_id or run_id not in selected_by_run:
            continue
        task_type = _task_type(selected_by_run[run_id])
        duration_ms = int(row.get("duration_ms") or 0)
        if duration_ms > 0 and task_type in task_durations_ms:
            task_durations_ms[task_type].append(duration_ms)

    candidates: list[dict[str, Any]] = []
    observations: dict[str, dict[str, Any]] = {}
    for task_type, defaults in task_defaults.items():
        selected_count = int(task_selected_counts.get(task_type, 0))
        fallback_count = int(task_fallback_counts.get(task_type, 0))
        recovery_count = int(task_recovery_counts.get(task_type, 0))
        durations = task_durations_ms.get(task_type, [])
        fallback_rate = (fallback_count / selected_count) if selected_count else 0.0
        p95_ms = int(_percentile(durations, 0.95)) if durations else 0
        suggested_timeout = defaults["timeout_seconds"]
        if p95_ms > 0:
            # 4x p95 with bounds keeps headroom while avoiding runaway timeouts.
            suggested_timeout = max(15, min(120, int(round((p95_ms / 1000.0) * 4.0))))
        confidence = "low"
        if selected_count >= 10:
            confidence = "high"
        elif selected_count >= 3:
            confidence = "medium"

        observations[task_type] = {
            "selected_runs": selected_count,
            "fallback_runs": fallback_count,
            "recovery_attempts": recovery_count,
            "fallback_rate": round(fallback_rate, 4),
            "p95_duration_ms": p95_ms,
            "confidence": confidence,
        }
        candidates.append(
            {
                "candidate_id": f"claw_code_{task_type.lower()}_experimental_v1",
                "task_type": task_type,
                "timeout_seconds": suggested_timeout,
                "max_chain_length": defaults["max_chain_length"],
                "max_cost_usd_per_run": defaults["max_cost_usd_per_run"],
                "fallback_chain": ["zeroclaw", "agent_os_python"],
                "confidence": confidence,
            }
        )

    return candidates, observations


def build_baseline_report(trace_rows: list[dict[str, Any]], matrix: dict[str, Any]) -> dict[str, Any]:
    claw_rows = [row for row in trace_rows if _provider(row) == "claw_code"]
    selected = [row for row in claw_rows if row.get("event_type") == "runtime_provider_selected"]
    fallback = [row for row in claw_rows if row.get("event_type") == "runtime_provider_fallback"]
    recovery = [row for row in claw_rows if row.get("event_type") == "runtime_recovery_attempted"]
    degraded = [row for row in claw_rows if row.get("event_type") == "runtime_degraded_mode_entered"]
    completed = [row for row in claw_rows if row.get("event_type") == "agent_run_completed"]

    durations = [int(row.get("duration_ms") or 0) for row in completed if int(row.get("duration_ms") or 0) > 0]
    recovery_types = Counter(str(row.get("data", {}).get("failure_type") or "unknown") for row in recovery)
    profile_counts = Counter(str(row.get("runtime_profile") or "default") for row in selected)

    recommendations: list[dict[str, Any]] = []
    for name, row in (matrix.get("profiles") or {}).items():
        if not isinstance(row, dict):
            continue
        if row.get("runtime_provider") != "claw_code":
            continue
        recommendations.append(
            {
                "profile_id": str(name),
                "runtime_profile": str(row.get("runtime_profile") or ""),
                "task_types": list(row.get("task_types") or []),
                "max_chain_length": row.get("max_chain_length"),
                "max_cost_usd_per_run": row.get("max_cost_usd_per_run"),
            }
        )

    selected_runs = len(selected)
    fallback_runs = len(fallback)
    candidates, observations = _build_experimental_candidates(
        selected=selected,
        completed=completed,
        fallback=fallback,
        recovery=recovery,
    )
    return {
        "summary": {
            "claw_code_selected_runs": selected_runs,
            "claw_code_fallback_runs": fallback_runs,
            "fallback_rate": round((fallback_runs / selected_runs), 4) if selected_runs else 0.0,
            "recovery_attempts": len(recovery),
            "degraded_mode_entries": len(degraded),
            "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0.0,
        },
        "recovery_by_failure_type": dict(recovery_types),
        "runtime_profile_usage": dict(profile_counts),
        "recommended_profiles": recommendations,
        "task_type_observations": observations,
        "experimental_candidates": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate claw_code baseline report from trace events.")
    parser.add_argument("--trace-file", default="logs/agent_traces.jsonl", help="Path to trace JSONL")
    parser.add_argument("--matrix", default="configs/tooling/runtime_benchmark_matrix.json", help="Path to runtime benchmark matrix JSON")
    parser.add_argument("--out", default="docs/ki/claw_code_baseline_report.json", help="Output JSON report path")
    args = parser.parse_args()

    trace_file = Path(args.trace_file).resolve()
    matrix_path = Path(args.matrix).resolve()
    out_path = Path(args.out).resolve()

    report = build_baseline_report(
        trace_rows=_load_jsonl(trace_file),
        matrix=_load_json(matrix_path, fallback={"profiles": {}}),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
