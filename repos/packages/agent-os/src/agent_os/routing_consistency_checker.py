#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agent_os.yaml_compat import parse_simple_yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(root: Path) -> dict[str, Any]:
    router_yaml_path = root / "configs/orchestrator/router.yaml"
    models_yaml_path = root / "configs/orchestrator/models.yaml"
    model_routing = load_json(root / "configs/tooling/model_routing.json")
    providers = load_json(root / "configs/tooling/model_providers.json")
    mcp_profiles = load_json(root / "configs/tooling/mcp_profiles.json")
    legacy_router_yaml = parse_simple_yaml((root / ".agents/config/model_router.yaml").read_text(encoding="utf-8"))
    v4_router_yaml = parse_simple_yaml(router_yaml_path.read_text(encoding="utf-8")) if router_yaml_path.exists() else {}
    v4_models_yaml = parse_simple_yaml(models_yaml_path.read_text(encoding="utf-8")) if models_yaml_path.exists() else {}

    findings: list[dict[str, str]] = []

    # v4 presence and structure checks (primary source of truth)
    if not router_yaml_path.exists():
        findings.append(
            {
                "severity": "error",
                "code": "V4_ROUTER_MISSING",
                "message": "configs/orchestrator/router.yaml is missing (v4 routing source-of-truth)",
            }
        )
    if not models_yaml_path.exists():
        findings.append(
            {
                "severity": "error",
                "code": "V4_MODELS_MISSING",
                "message": "configs/orchestrator/models.yaml is missing (v4 alias source-of-truth)",
            }
        )

    v4_task_types = ((((v4_router_yaml.get("routing") or {}) if isinstance(v4_router_yaml, dict) else {}).get("task_types")) or {})
    v4_tiers = ((((v4_router_yaml.get("routing") or {}) if isinstance(v4_router_yaml, dict) else {}).get("tiers")) or {})
    if not isinstance(v4_task_types, dict):
        v4_task_types = {}
    if not isinstance(v4_tiers, dict):
        v4_tiers = {}

    expected_task_types = {f"T{i}" for i in range(1, 8)}
    actual_v4_task_types = set(v4_task_types.keys())
    if actual_v4_task_types and actual_v4_task_types != expected_task_types:
        findings.append(
            {
                "severity": "warn",
                "code": "V4_TASK_TYPES_MISMATCH",
                "message": (
                    f"router.yaml task_types={sorted(actual_v4_task_types)} "
                    f"expected={sorted(expected_task_types)}"
                ),
            }
        )

    expected_complexities = {f"C{i}" for i in range(1, 6)}
    actual_v4_complexities = set(v4_tiers.keys())
    if actual_v4_complexities and actual_v4_complexities != expected_complexities:
        findings.append(
            {
                "severity": "warn",
                "code": "V4_TIERS_MISMATCH",
                "message": (
                    f"router.yaml tiers={sorted(actual_v4_complexities)} "
                    f"expected={sorted(expected_complexities)}"
                ),
            }
        )

    v4_models_map = (v4_models_yaml.get("models") if isinstance(v4_models_yaml, dict) else {}) or {}
    if not isinstance(v4_models_map, dict):
        v4_models_map = {}

    def alias_key(raw: Any) -> str | None:
        if not isinstance(raw, str):
            return None
        text = raw.strip()
        if text == "self-verify":
            return None
        if text.startswith("${") and text.endswith("}"):
            return text[2:-1]
        if text.startswith("$"):
            return text[1:]
        return None

    for c_key, row in sorted(v4_tiers.items()):
        if not isinstance(row, dict):
            findings.append(
                {
                    "severity": "error",
                    "code": "V4_TIER_ROW_INVALID",
                    "message": f"router.yaml routing.tiers.{c_key} must be a mapping",
                }
            )
            continue
        for required in ("path", "agents", "max_tools", "model_alias", "human_audit_required"):
            if required not in row:
                findings.append(
                    {
                        "severity": "error",
                        "code": "V4_TIER_FIELD_MISSING",
                        "message": f"router.yaml routing.tiers.{c_key}.{required} missing",
                    }
                )
        for field in ("model_alias", "reviewer_model", "orchestrator_model"):
            if field not in row:
                continue
            a_key = alias_key(row.get(field))
            if a_key and a_key not in v4_models_map:
                findings.append(
                    {
                        "severity": "error",
                        "code": "V4_ALIAS_UNRESOLVED",
                        "message": f"router.yaml routing.tiers.{c_key}.{field} references missing alias {a_key} in models.yaml",
                    }
                )

    def path_to_provider_tier(path_value: str) -> str | None:
        low = path_value.lower()
        if "fast" in low:
            return "free"
        if "quality" in low:
            return "quality"
        if "swarm" in low:
            return "reasoning"
        return None

    v4_exceptions = ((((v4_router_yaml.get("routing") or {}) if isinstance(v4_router_yaml, dict) else {}).get("exceptions")) or {})
    if isinstance(v4_exceptions, dict) and "ui_fast_path" in v4_exceptions:
        ui_fast_path = v4_exceptions.get("ui_fast_path")
        if not isinstance(ui_fast_path, dict):
            findings.append(
                {
                    "severity": "error",
                    "code": "V4_UI_FAST_PATH_INVALID",
                    "message": "router.yaml routing.exceptions.ui_fast_path must be a mapping",
                }
            )
        else:
            for key in ("enabled", "task_type", "preset_cache_file", "force_path"):
                if key not in ui_fast_path:
                    findings.append(
                        {
                            "severity": "warn",
                            "code": "V4_UI_FAST_PATH_FIELD_MISSING",
                            "message": f"router.yaml routing.exceptions.ui_fast_path.{key} missing",
                        }
                    )
            preset_cache_file = ui_fast_path.get("preset_cache_file")
            if isinstance(preset_cache_file, str):
                cache_path = root / preset_cache_file
                if not cache_path.exists():
                    findings.append(
                        {
                            "severity": "warn",
                            "code": "V4_UI_FAST_PATH_CACHE_MISSING",
                            "message": f"ui_fast_path preset_cache_file not found: {preset_cache_file}",
                        }
                    )

    routing_tiers = set(model_routing.get("tiers", []))
    providers_tiers = set(providers.get("tiers", {}).keys())
    yaml_tiers = set((legacy_router_yaml.get("tiers") or {}).keys())

    if routing_tiers != providers_tiers:
        findings.append(
            {
                "severity": "warn",
                "code": "TIER_SET_MISMATCH_JSON",
                "message": f"model_routing tiers={sorted(routing_tiers)} vs model_providers tiers={sorted(providers_tiers)}",
            }
        )
    if routing_tiers != yaml_tiers:
        findings.append(
            {
                "severity": "warn",
                "code": "TIER_SET_MISMATCH_YAML",
                "message": f"model_routing tiers={sorted(routing_tiers)} vs .agents/config/model_router.yaml tiers={sorted(yaml_tiers)}",
            }
        )

    # Check matrix completeness: all task/complexity pairs in T1-7 x C1-5.
    expected_pairs = {(f"T{i}", f"C{j}") for i in range(1, 8) for j in range(1, 6)}
    actual_pairs = {(row.get("task_type"), row.get("complexity")) for row in model_routing.get("routing", [])}
    missing_pairs = sorted(expected_pairs - actual_pairs)
    extra_pairs = sorted(actual_pairs - expected_pairs)
    if missing_pairs:
        findings.append(
            {
                "severity": "error",
                "code": "MODEL_ROUTING_MISSING_PAIRS",
                "message": f"Missing routing pairs: {missing_pairs[:5]}{'...' if len(missing_pairs) > 5 else ''}",
            }
        )
    if extra_pairs:
        findings.append(
            {
                "severity": "warn",
                "code": "MODEL_ROUTING_EXTRA_PAIRS",
                "message": f"Unexpected routing pairs: {extra_pairs[:5]}{'...' if len(extra_pairs) > 5 else ''}",
            }
        )

    # v4 to legacy compatibility drift check: v4 path mapping should match legacy provider-tier matrix where both exist.
    for task_type in sorted(expected_task_types):
        for complexity in sorted(expected_complexities):
            legacy_tier = None
            for row in model_routing.get("routing", []):
                if row.get("task_type") == task_type and row.get("complexity") == complexity:
                    legacy_tier = str(row.get("model_tier"))
                    break
            v4_row = v4_tiers.get(complexity, {}) if isinstance(v4_tiers, dict) else {}
            v4_path = str(v4_row.get("path", "")) if isinstance(v4_row, dict) else ""
            v4_tier = path_to_provider_tier(v4_path) if v4_path else None
            if legacy_tier and v4_tier and legacy_tier != v4_tier:
                findings.append(
                    {
                        "severity": "warn",
                        "code": "V4_LEGACY_TIER_DRIFT",
                        "message": f"{task_type}/{complexity}: v4 path '{v4_path}' -> {v4_tier}, legacy matrix -> {legacy_tier}",
                    }
                )

    # Check mcp profile references used by routing exist.
    defined_profiles = set(mcp_profiles.get("profiles", {}).keys())
    default_profile = mcp_profiles.get("default_profile")
    if default_profile not in defined_profiles:
        findings.append(
            {
                "severity": "error",
                "code": "MCP_DEFAULT_PROFILE_MISSING",
                "message": f"default_profile={default_profile} not present in profiles",
            }
        )
    for row in mcp_profiles.get("routing", []):
        profile = row.get("profile")
        if profile not in defined_profiles:
            findings.append(
                {
                    "severity": "error",
                    "code": "MCP_ROUTING_PROFILE_MISSING",
                    "message": f"routing row references unknown profile={profile}",
                }
            )

    # Check yaml tiers have non-empty models.
    yaml_models: dict[str, list[str]] = {}
    for tier in ("light", "quality", "reasoning"):
        models = (
            (((legacy_router_yaml.get("tiers") or {}).get(tier) or {}).get("models"))
            if isinstance(legacy_router_yaml.get("tiers"), dict)
            else None
        )
        if not isinstance(models, list) or not models:
            findings.append(
                {
                    "severity": "error",
                    "code": "YAML_TIER_MODELS_EMPTY",
                    "message": f"tiers.{tier}.models missing or empty",
                }
            )
            yaml_models[tier] = []
        else:
            yaml_models[tier] = [str(m) for m in models]

    # Cross-mode drift heuristic: hybrid providers vs free-first yaml inventories.
    router_mode_default = providers.get("router_mode_default")
    yaml_strategy = legacy_router_yaml.get("strategy")
    compat_precedence = providers.get("compat_precedence")
    if router_mode_default == "hybrid" and yaml_strategy == "free-first":
        if compat_precedence == "v4-primary":
            findings.append(
                {
                    "severity": "info",
                    "code": "ROUTER_MODE_PRECEDENCE_DECLARED",
                    "message": "compat_precedence=v4-primary explicitly resolves hybrid provider mode vs legacy free-first yaml strategy",
                }
            )
        else:
            findings.append(
                {
                    "severity": "warn",
                    "code": "ROUTER_MODE_PRECEDENCE_UNSPECIFIED",
                    "message": "model_providers.router_mode_default=hybrid while .agents/config/model_router.yaml strategy=free-first; precedence is not machine-readable here",
                }
            )

    severity = "ok"
    if any(f["severity"] == "error" for f in findings):
        severity = "error"
    elif any(f["severity"] == "warn" for f in findings):
        severity = "warn"

    migration_actions = [
        "Keep configs/orchestrator/router.yaml + models.yaml as primary source-of-truth for task/complexity and alias routing",
        "Treat configs/tooling/model_routing.json and .agents/config/model_router.yaml as compatibility layers until agent-os migration is complete",
    ]

    return {
        "severity": severity,
        "summary": {
            "v4_router_present": router_yaml_path.exists(),
            "v4_models_present": models_yaml_path.exists(),
            "v4_task_types": sorted(actual_v4_task_types) if actual_v4_task_types else [],
            "v4_complexities": sorted(actual_v4_complexities) if actual_v4_complexities else [],
            "routing_rows": len(model_routing.get("routing", [])),
            "providers_tiers": sorted(providers_tiers),
            "yaml_tiers": sorted(yaml_tiers),
            "yaml_strategy": yaml_strategy,
            "router_mode_default": router_mode_default,
            "compat_precedence": compat_precedence,
        },
        "findings": findings,
        "migration_actions": migration_actions,
        # Compat alias for one transition cycle.
        "diff_spec_proposals": migration_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only validator for model routing consistency")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    report = build_report(repo_root())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["severity"] != "error" else 1

    print(f"severity={report['severity']}")
    for k, v in report["summary"].items():
        print(f"{k}: {v}")
    if report["findings"]:
        print("findings:")
        for f in report["findings"]:
            print(f"- [{f['severity']}] {f['code']}: {f['message']}")
    else:
        print("findings: -")
    print("migration-actions:")
    for item in report.get("migration_actions", report.get("diff_spec_proposals", [])):
        print(f"- {item}")
    return 0 if report["severity"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
