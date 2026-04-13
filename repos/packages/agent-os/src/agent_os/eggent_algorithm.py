from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_ALGORITHM_MATRIX: dict[str, Any] = {
    "version": "1.0",
    "repeat": 5,
    "timeout_minutes": 60,
    "real_trace_sample_default": 30,
    "scoring": {
        "quality_weight": 0.70,
        "autonomy_weight": 0.30,
    },
    "promotion_policy": {
        "pass_rate_min": 0.80,
        "hard_fail_rate_max": 0.05,
        "tie_break_delta": 0.03,
        "trace_v2_required": True,
        "prefer_lower_cost_on_tie": True,
        "prefer_lower_escalation_on_tie": True,
        "prefer_lower_openrouter_fallbacks_on_tie": True,
    },
    "variants": {
        "baseline": {
            "name": "Baseline",
            "gates": [],
            "free_first": True,
            "openrouter_fallback": "c4_c5_or_quality_failure",
        },
        "self_verify_gate": {
            "name": "Self-Verify Gate",
            "gates": ["self_verify"],
            "free_first": True,
            "openrouter_fallback": "c4_c5_or_quality_failure",
        },
        "spec_to_contract_gate": {
            "name": "Spec-to-Contract Gate",
            "gates": ["spec_contract"],
            "free_first": True,
            "openrouter_fallback": "c4_c5_or_quality_failure",
        },
        "confidence_weighted_escalation": {
            "name": "Confidence-Weighted Escalation",
            "gates": ["confidence_escalation"],
            "free_first": True,
            "openrouter_fallback": "c4_c5_or_quality_failure",
        },
        "multi_critic_review": {
            "name": "Multi-Critic Review",
            "gates": ["multi_critic"],
            "free_first": True,
            "openrouter_fallback": "c4_c5_or_quality_failure",
        },
        "autonomy_ladder": {
            "name": "Autonomy Ladder",
            "gates": ["autonomy_ladder"],
            "free_first": True,
            "openrouter_fallback": "c4_c5_or_quality_failure",
        },
    },
    "promoted_default": {
        "variant": "autonomy_ladder",
        "always_on_gates": ["autonomy_ladder"],
        "fallback_policy": "confidence_weighted_escalation",
        "shadow_gates": ["spec_contract", "self_verify", "multi_critic"],
    },
}


_PASSING_VERIFICATION = {"ok", "pass", "passed", "success", "green", "completed"}
_MISSING_VERIFICATION = {"", "not-run", "not_run", "none", "unknown", "skipped"}
_DESTRUCTIVE_TERMS = {
    "delete",
    "remove",
    "drop",
    "destroy",
    "purge",
    "reset",
    "external contact",
    "send email",
    "publish",
    "deploy",
}


def load_algorithm_matrix(repo_root: Path, matrix_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(matrix_path) if matrix_path else repo_root / "configs/tooling/eggent_algorithm_matrix.json"
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        return deepcopy(DEFAULT_ALGORITHM_MATRIX)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    matrix = deepcopy(DEFAULT_ALGORITHM_MATRIX)
    _deep_update(matrix, loaded)
    return matrix


def resolve_algorithm_variant(matrix: dict[str, Any], variant_id: str | None) -> tuple[str, dict[str, Any]]:
    normalized = str(variant_id or "baseline").strip() or "baseline"
    variants = matrix.get("variants")
    if not isinstance(variants, dict) or normalized not in variants:
        available = ", ".join(sorted(str(k) for k in (variants or {}).keys()))
        raise ValueError(f"Unknown Eggent algorithm variant: {normalized}. Available: {available}")
    variant = dict(variants[normalized])
    variant["id"] = normalized
    variant.setdefault("gates", [])
    return normalized, variant


def benchmark_repeat(matrix: dict[str, Any], explicit_repeat: int | None) -> int:
    if explicit_repeat is not None and int(explicit_repeat) > 0:
        return int(explicit_repeat)
    return max(1, int(matrix.get("repeat") or 1))


def derive_task_contract(objective: str, task_type: str, complexity: str) -> dict[str, Any]:
    text = str(objective or "").lower()
    requires_tests = "test" in text or "тест" in text
    requires_verification = requires_tests or any(token in text for token in ("verify", "verification", "проверь"))
    requires_approval = complexity in {"C4", "C5"} and any(term in text for term in _DESTRUCTIVE_TERMS)
    return {
        "requires_tests": bool(requires_tests),
        "requires_verification": bool(requires_verification),
        "requires_approval": bool(requires_approval),
        "risk_terms": sorted(term for term in _DESTRUCTIVE_TERMS if term in text),
    }


def evaluate_algorithm_gates(
    variant: dict[str, Any],
    *,
    objective: str,
    task_type: str,
    complexity: str,
    route_payload: dict[str, Any],
    run_payload: dict[str, Any],
    summary_data: dict[str, Any],
    base_checks: dict[str, bool],
) -> tuple[dict[str, bool], dict[str, Any]]:
    gates = {str(g) for g in variant.get("gates", []) if str(g).strip()}
    contract = derive_task_contract(objective, task_type, complexity)
    confidence = _confidence(route_payload, summary_data, base_checks)
    verification_state = _verification_state(summary_data, run_payload)
    checks: dict[str, bool] = {}

    if "self_verify" in gates:
        checks["self_verify_gate"] = _self_verify_passed(contract, verification_state, base_checks)

    if "spec_contract" in gates:
        checks["spec_to_contract_gate"] = _contract_satisfied(contract, summary_data, run_payload)

    if "confidence_escalation" in gates:
        checks["confidence_weighted_escalation"] = confidence >= 0.55 or complexity in {"C4", "C5"}

    if "multi_critic" in gates:
        checks["multi_critic_review"] = _multi_critic_passed(contract, summary_data, run_payload, confidence)

    if "autonomy_ladder" in gates:
        checks["autonomy_ladder"] = _autonomy_ladder_passed(contract, route_payload, summary_data)

    metadata = {
        "contract": contract,
        "confidence": round(confidence, 4),
        "verification_state": verification_state,
        "gates": sorted(gates),
        "openrouter_fallback_allowed": _openrouter_fallback_allowed(variant, complexity, checks),
    }
    return checks, metadata


def real_trace_cases(repo_root: Path, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    trace_path = Path(str(repo_root / "logs/agent_traces.jsonl"))
    if not trace_path.exists():
        return []

    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in reversed(trace_path.read_text(encoding="utf-8").splitlines()):
        if len(cases) >= limit:
            break
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except Exception:
            continue
        if event.get("event_type") != "task_run_summary":
            continue
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        objective = str(data.get("objective") or event.get("message") or "").strip()
        if not objective or objective in seen:
            continue
        seen.add(objective)
        run_id = str(event.get("run_id") or len(cases) + 1)
        cases.append(
            {
                "id": f"real-trace-{run_id[:12]}",
                "task_type": str(event.get("task_type") or "T3"),
                "complexity": str(event.get("complexity") or "C3"),
                "description": objective,
                "expected_path": str(data.get("orchestration_path") or ""),
                "max_tools": int(data.get("tool_calls_total") or 0),
                "max_duration_seconds": 300,
                "success_criteria": ["task_completed"],
                "source": "agent_traces",
                "source_run_id": run_id,
            }
        )
    return list(reversed(cases))


def promotion_gate(
    matrix: dict[str, Any],
    *,
    pass_rate: float,
    hard_fail_rate: float,
    trace_v2_clean: bool,
) -> dict[str, Any]:
    policy = matrix.get("promotion_policy") if isinstance(matrix.get("promotion_policy"), dict) else {}
    pass_rate_min = float(policy.get("pass_rate_min", 0.80))
    hard_fail_rate_max = float(policy.get("hard_fail_rate_max", 0.05))
    trace_required = bool(policy.get("trace_v2_required", True))
    reasons: list[str] = []
    if pass_rate < pass_rate_min:
        reasons.append("pass_rate_below_threshold")
    if hard_fail_rate > hard_fail_rate_max:
        reasons.append("hard_fail_rate_above_threshold")
    if trace_required and not trace_v2_clean:
        reasons.append("trace_v2_validation_failed")
    return {
        "disqualified": bool(reasons),
        "reasons": reasons,
        "thresholds": {
            "pass_rate_min": pass_rate_min,
            "hard_fail_rate_max": hard_fail_rate_max,
            "trace_v2_required": trace_required,
        },
    }


def _deep_update(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _verification_passed(summary_data: dict[str, Any], run_payload: dict[str, Any]) -> bool:
    return _verification_state(summary_data, run_payload) == "passed"


def _verification_state(summary_data: dict[str, Any], run_payload: dict[str, Any]) -> str:
    candidates = [
        summary_data.get("verification_status"),
        summary_data.get("test_report_status"),
        ((run_payload.get("agent") or {}).get("test_report") or {}).get("status")
        if isinstance(run_payload.get("agent"), dict)
        else None,
    ]
    normalized = {str(item or "").strip().lower() for item in candidates}
    if normalized & _PASSING_VERIFICATION:
        return "passed"
    observed = normalized - _MISSING_VERIFICATION
    if observed:
        return "failed"
    return "missing"


def _self_verify_passed(contract: dict[str, Any], verification_state: str, base_checks: dict[str, bool]) -> bool:
    if verification_state == "passed":
        return True
    if verification_state == "failed":
        return False
    if contract.get("requires_verification"):
        return False
    return all(base_checks.values())


def _contract_satisfied(contract: dict[str, Any], summary_data: dict[str, Any], run_payload: dict[str, Any]) -> bool:
    agent_status = str((run_payload.get("agent") or {}).get("status") or summary_data.get("agent_status") or "").lower()
    if agent_status not in {"completed", "success", "ok"}:
        return False
    if contract.get("requires_verification") and not _verification_passed(summary_data, run_payload):
        return False
    if contract.get("requires_approval") and not bool(summary_data.get("approval_gate_triggered")):
        return False
    return True


def _multi_critic_passed(
    contract: dict[str, Any],
    summary_data: dict[str, Any],
    run_payload: dict[str, Any],
    confidence: float,
) -> bool:
    if confidence < 0.55:
        return False
    return _contract_satisfied(contract, summary_data, run_payload)


def _autonomy_ladder_passed(
    contract: dict[str, Any],
    route_payload: dict[str, Any],
    summary_data: dict[str, Any],
) -> bool:
    if contract.get("requires_approval"):
        return bool(summary_data.get("approval_gate_triggered") or route_payload.get("approval_policy"))
    stop_honored = summary_data.get("stop_signal_honored")
    if stop_honored is False:
        return False
    return True


def _confidence(route_payload: dict[str, Any], summary_data: dict[str, Any], base_checks: dict[str, bool]) -> float:
    score = 0.35
    if route_payload.get("primary_model"):
        score += 0.15
    if all(base_checks.values()):
        score += 0.25
    if _verification_passed(summary_data, {"agent": {"status": summary_data.get("agent_status")}}):
        score += 0.15
    if int(summary_data.get("retrieval_chunks") or 0) > 0:
        score += 0.10
    return max(0.0, min(1.0, score))


def _openrouter_fallback_allowed(variant: dict[str, Any], complexity: str, checks: dict[str, bool]) -> bool:
    policy = str(variant.get("openrouter_fallback") or "")
    if policy == "never":
        return False
    if complexity in {"C4", "C5"}:
        return True
    if "quality_failure" in policy and any(value is False for value in checks.values()):
        return True
    return False
