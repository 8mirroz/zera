#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
PROGRAM = ROOT / "configs/tooling/test_reliability_program.yaml"
MATRIX = ROOT / "configs/tooling/test_suite_matrix.yaml"
DEBUG_MAP = ROOT / "configs/tooling/debug_surface_map.yaml"
MAKEFILE = ROOT / "Makefile"
QUALITY = ROOT / "scripts/run_quality_checks.sh"
WORKFLOW = ROOT / ".github/workflows/test.yml"
REVIEW_PLAN = ROOT / "docs/ki/CODE_REVIEW_PLAN.md"
ONBOARDING = ROOT / "docs/AGENT_ONBOARDING.md"
HARNESS = ROOT / "configs/tooling/evaluation-harness.yaml"
DRIFT = ROOT / "configs/tooling/drift-detection-rules.yaml"

REQUIRED_SUITES = {"unit", "contract", "integration", "smoke", "doctor", "benchmark", "governance", "regression"}
REQUIRED_FAILURE_CLASSES = {
    "syntax_or_parse",
    "contract_violation",
    "routing_logic",
    "governance_boundary",
    "tooling_or_env",
    "integration_surface",
    "benchmark_regression",
    "observability_gap",
    "doc_runtime_drift",
    "flaky_or_nondeterministic",
}
REQUIRED_HARNESS_SCENARIOS = {
    "zera_command_registry_parity",
    "zera_branch_lifecycle",
    "zera_client_parity",
    "zera_governor_budget",
    "zera_source_import_foundry_safety",
}
REQUIRED_DRIFT_SIGNALS = {
    "zera_command_registry_drift",
    "zera_branch_policy_drift",
    "zera_client_parity_drift",
    "zera_governor_budget_breach",
    "zera_source_import_foundry_drift",
}
REQUIRED_MAKE_TARGETS = {
    "doctor:",
    "test-unit:",
    "test-contract:",
    "test-integration:",
    "test-smoke:",
    "test-governance:",
    "test-benchmark:",
    "test-all:",
    "debug-test:",
    "reliability-report:",
}


class ValidationError(Exception):
    pass


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValidationError(f"{path} must parse to a mapping")
    return data


def validate_configs() -> dict[str, object]:
    program = _load_yaml(PROGRAM)
    matrix = _load_yaml(MATRIX)
    debug_map = _load_yaml(DEBUG_MAP)
    harness = _load_yaml(HARNESS)
    drift = _load_yaml(DRIFT)

    profiles = set(program.get("profiles", {}))
    if {"local_quick", "pre_commit", "ci_required", "nightly", "all_non_benchmark"} - profiles:
        raise ValidationError("test_reliability_program.yaml missing required profiles")

    suites = set(matrix.get("suites", {}))
    missing_suites = REQUIRED_SUITES - suites
    if missing_suites:
        raise ValidationError(f"test_suite_matrix.yaml missing suites: {', '.join(sorted(missing_suites))}")

    failure_classes = set(debug_map.get("failure_classes", {}))
    missing_classes = REQUIRED_FAILURE_CLASSES - failure_classes
    if missing_classes:
        raise ValidationError(f"debug_surface_map.yaml missing failure classes: {', '.join(sorted(missing_classes))}")

    scenarios = set(harness.get("scenario_coverage", []))
    missing_scenarios = REQUIRED_HARNESS_SCENARIOS - scenarios
    if missing_scenarios:
        raise ValidationError(f"evaluation-harness.yaml missing scenarios: {', '.join(sorted(missing_scenarios))}")

    signals = set(drift.get("signals", []))
    missing_signals = REQUIRED_DRIFT_SIGNALS - signals
    if missing_signals:
        raise ValidationError(f"drift-detection-rules.yaml missing signals: {', '.join(sorted(missing_signals))}")
    responses = drift.get("responses", {})
    if not isinstance(responses, dict):
        raise ValidationError("drift-detection-rules.yaml responses must be a mapping")
    for signal in REQUIRED_DRIFT_SIGNALS:
        if signal not in responses:
            raise ValidationError(f"drift-detection-rules.yaml missing response for {signal}")

    for suite_name, suite in matrix["suites"].items():
        buckets = suite.get("buckets", [])
        if not buckets:
            raise ValidationError(f"suite '{suite_name}' has no buckets")
        for bucket in buckets:
            if bucket["kind"] == "pytest_glob":
                excludes = bucket.get("exclude", [])
                for ex in excludes:
                    for key in ("pattern", "reason", "owner", "sunset_date"):
                        if key not in ex or not ex[key]:
                            raise ValidationError(f"{suite_name}:{bucket['id']} exclude missing '{key}'")
            quarantine = bucket.get("quarantine")
            allowed_exit_codes = bucket.get("allowed_exit_codes", [0])
            if quarantine is not None:
                for key in ("owner", "reason", "exit_condition", "sunset_date"):
                    if key not in quarantine or not quarantine[key]:
                        raise ValidationError(f"{suite_name}:{bucket['id']} quarantine missing '{key}'")
                if allowed_exit_codes == [0]:
                    raise ValidationError(f"{suite_name}:{bucket['id']} quarantine requires non-default allowed_exit_codes")

    governance_buckets = matrix["suites"]["governance"].get("buckets", [])
    if not any("tests/test_zera_hybrid_pilot_contracts.py" in bucket.get("include", []) for bucket in governance_buckets):
        raise ValidationError("test_suite_matrix.yaml must wire tests/test_zera_hybrid_pilot_contracts.py into governance suite")
    if not any("tests/test_zera_hybrid_pilot_runtime_telemetry.py" in bucket.get("include", []) for bucket in governance_buckets):
        raise ValidationError(
            "test_suite_matrix.yaml must wire tests/test_zera_hybrid_pilot_runtime_telemetry.py into governance suite"
        )

    return {
        "profiles": sorted(profiles),
        "suites": sorted(suites),
        "failure_classes": sorted(failure_classes),
        "harness_scenarios": sorted(scenarios),
        "drift_signals": sorted(signals),
    }


def validate_make_and_scripts() -> dict[str, object]:
    make_text = MAKEFILE.read_text(encoding="utf-8")
    quality_text = QUALITY.read_text(encoding="utf-8")

    missing_targets = [target for target in REQUIRED_MAKE_TARGETS if target not in make_text]
    if missing_targets:
        raise ValidationError(f"Makefile missing targets: {', '.join(missing_targets)}")

    if "SWARMCTL_IGNORE" in make_text:
        raise ValidationError("Makefile must not retain SWARMCTL_IGNORE")
    if "--ignore=" in make_text:
        raise ValidationError("Makefile must not encode raw pytest ignores")
    if "reliability_orchestrator.py" not in quality_text:
        raise ValidationError("scripts/run_quality_checks.sh must delegate to reliability_orchestrator.py")
    if "pytest " in quality_text and "reliability_orchestrator.py" not in quality_text:
        raise ValidationError("scripts/run_quality_checks.sh must not contain raw pytest logic")

    return {"make_targets_verified": True, "quality_wrapper_verified": True}


def validate_ci_and_docs() -> dict[str, object]:
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    if "make test-contract" not in workflow_text:
        raise ValidationError("CI workflow must call make test-contract")
    if "make test-governance" not in workflow_text:
        raise ValidationError("CI workflow must call make test-governance")
    if "make test-smoke" not in workflow_text:
        raise ValidationError("CI workflow must call make test-smoke")
    if "make test-unit" not in workflow_text:
        raise ValidationError("CI workflow must call make test-unit")
    if "make doctor" not in workflow_text:
        raise ValidationError("CI workflow must call make doctor")
    if "--ignore=tests/test_swarmctl_" in workflow_text:
        raise ValidationError("CI workflow must not contain raw swarmctl ignore list")

    review_text = REVIEW_PLAN.read_text(encoding="utf-8")
    onboarding_text = ONBOARDING.read_text(encoding="utf-8")
    for required in ("make test-contract", "make test-governance", "make doctor", "make reliability-report"):
        if required not in review_text:
            raise ValidationError(f"CODE_REVIEW_PLAN.md missing '{required}'")
        if required not in onboarding_text:
            raise ValidationError(f"AGENT_ONBOARDING.md missing '{required}'")

    return {"ci_verified": True, "docs_verified": True}


def main() -> int:
    as_json = "--json" in sys.argv[1:]
    try:
        payload = {
            "configs": validate_configs(),
            "make_and_scripts": validate_make_and_scripts(),
            "ci_and_docs": validate_ci_and_docs(),
            "status": "ok",
        }
        if as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("Reliability platform validation: OK")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except ValidationError as exc:
        if as_json:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Reliability platform validation: ERROR\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
