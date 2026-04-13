#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "configs" / "tooling" / "zera_growth_governance.json"
EVAL_CASES = ROOT / "configs" / "personas" / "zera" / "eval_cases.json"
COMMAND_REGISTRY = ROOT / "configs" / "tooling" / "zera_command_registry.yaml"
CLIENT_PROFILES = ROOT / "configs" / "tooling" / "zera_client_profiles.yaml"
BRANCH_POLICY = ROOT / "configs" / "tooling" / "zera_branching_policy.yaml"
RESEARCH_REGISTRY = ROOT / "configs" / "tooling" / "zera_research_registry.yaml"
SKILL_FOUNDRY = ROOT / "configs" / "tooling" / "zera_skill_foundry.yaml"
EXTERNAL_IMPORTS = ROOT / "configs" / "tooling" / "zera_external_imports.yaml"
ADAPTER = ROOT / "configs" / "adapters" / "hermes" / "adapter.yaml"
AGENT_MAP = ROOT / "configs" / "adapters" / "hermes" / "agent-map.yaml"
IMPORT_GOVERNANCE = ROOT / "configs" / "policies" / "import_governance.yaml"
SOURCE_TRUST = ROOT / "configs" / "tooling" / "source_trust_policy.yaml"
HARNESS = ROOT / "configs" / "tooling" / "evaluation-harness.yaml"
DRIFT_RULES = ROOT / "configs" / "tooling" / "drift-detection-rules.yaml"
HERMES_PROFILE = Path.home() / ".hermes" / "profiles" / "zera" / "config.yaml"
GEMINI_CONFIG = Path.home() / ".gemini" / "zera" / "mcp_config.json"
TARGET_SCRIPTS = {
    "scripts/zera-self-evolution.sh": [
        "GOVERNANCE_CONFIG=",
        "FREEZE_FILE=",
        "event_log",
        "Candidate template refreshed",
    ],
    "scripts/zera-evolve.sh": [
        "GOVERNANCE_CONFIG=",
        "FREEZE_FILE=",
        "COMMAND_BRIDGE=",
        "LOOPS_DIR=\"$VAULT/loops\"",
        "Run exactly one bounded self-evolution cycle.",
        "Do not promote personality deltas.",
    ],
    "scripts/zera-agent-intelligence.sh": [
        "PROMOTE_MEMORY=false",
        "GOVERNANCE_CONFIG=",
        "COMMAND_BRIDGE=",
        "Stable persona-memory promotion is disabled by default",
        "agent-intelligence-review-",
    ],
}

REQUIRED_CANDIDATE_CLASSES = {
    "skill_refinement",
    "tool_usage_refinement",
    "workflow_improvement",
    "orchestration_pattern_update",
    "memory_policy_refinement",
    "tone_calibration",
    "boundary_tightening",
    "proactivity_adjustment",
    "refusal_behavior_adjustment",
    "autonomy_behavior_adjustment",
    "governance_affecting_candidate",
    "mixed_ambiguous_candidate",
}

REQUIRED_GOVERNANCE_SURFACES = {
    "constitution",
    "safety",
    "relationship_boundaries",
    "autonomy_policy",
    "approval_boundaries",
    "memory_retention_rules",
    "promotion_rules",
    "rollback_rules",
}

REQUIRED_FREEZE_CONDITIONS = {
    "governance_surface_touched_without_approval",
    "unclassified_candidate",
    "missing_rollback_path",
    "missing_eval_suite",
    "missing_telemetry",
    "personality_delta_budget_breach",
}

REQUIRED_TELEMETRY_FIELDS = {
    "ts",
    "run_id",
    "event_type",
    "candidate_id",
    "candidate_class",
    "loop",
    "target_layer",
    "risk_level",
    "governance_impact",
    "decision",
    "eval_suite",
    "rollback_path",
    "source",
}

REQUIRED_CATEGORIES = {
    "persona_stability": 5,
    "autonomy_governance": 5,
    "dual_loop_safety": 5,
    "adversarial": 5,
    "long_horizon_coherence": 4,
}

REQUIRED_COMMANDS = {
    "zera:plan",
    "zera:research",
    "zera:architect",
    "zera:branch",
    "zera:critic",
    "zera:calibrate",
    "zera:evolve-capability",
    "zera:evolve-personality",
    "zera:governance-check",
    "zera:retro",
    "zera:foundry-ingest",
}

REQUIRED_HARNESS_SCENARIOS = {
    "zera_persona_boundary",
    "zera_autonomy_governance",
    "zera_dual_loop_candidate_routing",
    "zera_prompt_injection_self_evolution",
    "zera_personality_delta_budget",
    "zera_memory_restraint",
    "zera_rollback_rehearsal",
    "zera_command_registry_parity",
    "zera_branch_lifecycle",
    "zera_client_parity",
    "zera_governor_budget",
    "zera_source_import_foundry_safety",
    "zera_runtime_telemetry_contract",
    "zera_branch_merge_enforcement",
}

REQUIRED_DRIFT_SIGNALS = {
    "persona_boundary_drift",
    "governance_mutation_attempt_increase",
    "unclassified_candidate_rate_increase",
    "personality_delta_budget_breach",
    "memory_hoarding_increase",
    "zera_command_registry_drift",
    "zera_branch_policy_drift",
    "zera_client_parity_drift",
    "zera_governor_budget_breach",
    "zera_source_import_foundry_drift",
    "zera_runtime_telemetry_drift",
    "zera_branch_merge_classification_drift",
}

REQUIRED_BRANCH_TYPES = {
    "strategy_branch",
    "research_branch",
    "red_team_branch",
    "execution_branch",
    "persona_sensitivity_branch",
}


class ValidationError(Exception):
    pass


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise ValidationError(f"Missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise ValidationError(f"Missing file: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValidationError(f"YAML file must parse to mapping: {path}")
    return data


def _ref_matches(path_value: object, required_suffix: str) -> bool:
    if not isinstance(path_value, str) or not path_value.strip():
        return False
    normalized = path_value.replace("\\", "/")
    return normalized.endswith(required_suffix)


def _assert_secret_hygiene(text: str, file_label: str) -> None:
    patterns = {
        "openai": r"sk-[A-Za-z0-9]{20,}",
        "supabase": r"sbp_[0-9a-f]{20,}",
        "google": r"AIza[0-9A-Za-z_-]{20,}",
        "slack": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    }
    for token_name, pattern in patterns.items():
        if re.search(pattern, text):
            raise ValidationError(f"{file_label} contains potential inline secret token ({token_name})")


def validate_governance() -> dict[str, object]:
    data = _load_json(GOVERNANCE)
    classes = set(data.get("candidate_classes", {}).keys())
    missing_classes = sorted(REQUIRED_CANDIDATE_CLASSES - classes)
    if missing_classes:
        raise ValidationError(f"Governance config missing candidate classes: {', '.join(missing_classes)}")

    surfaces = set(data.get("control_plane", {}).get("governance_surfaces", []))
    missing_surfaces = sorted(REQUIRED_GOVERNANCE_SURFACES - surfaces)
    if missing_surfaces:
        raise ValidationError(f"Governance config missing governance surfaces: {', '.join(missing_surfaces)}")

    freeze_conditions = set(data.get("freeze_conditions", []))
    missing_freeze = sorted(REQUIRED_FREEZE_CONDITIONS - freeze_conditions)
    if missing_freeze:
        raise ValidationError(f"Governance config missing freeze conditions: {', '.join(missing_freeze)}")

    telemetry = set(data.get("required_telemetry_fields", []))
    missing_telemetry = sorted(REQUIRED_TELEMETRY_FIELDS - telemetry)
    if missing_telemetry:
        raise ValidationError(f"Governance config missing telemetry fields: {', '.join(missing_telemetry)}")

    promotion = data.get("promotion_rules", {})
    if not promotion.get("eval_required"):
        raise ValidationError("Governance config must require eval before promotion")
    if not promotion.get("rollback_required"):
        raise ValidationError("Governance config must require rollback before promotion")
    if promotion.get("max_significant_personality_deltas_per_cycle") != 1:
        raise ValidationError("Governance config must cap significant personality deltas per cycle at 1")

    return {
        "candidate_classes": len(classes),
        "governance_surfaces": len(surfaces),
        "freeze_conditions": len(freeze_conditions),
    }


def validate_evals() -> dict[str, object]:
    data = _load_json(EVAL_CASES)
    cases = data.get("cases", [])
    if not cases:
        raise ValidationError("No eval cases found")

    counts: dict[str, int] = {}
    for case in cases:
        category = case.get("category")
        counts[category] = counts.get(category, 0) + 1
        for field in ("id", "prompt", "must_include", "must_not_include", "failure_signals"):
            if field not in case:
                raise ValidationError(f"Eval case missing '{field}': {case.get('id', '<unknown>')}")

    for category, minimum in REQUIRED_CATEGORIES.items():
        if counts.get(category, 0) < minimum:
            raise ValidationError(
                f"Eval coverage too small for '{category}': {counts.get(category, 0)} < {minimum}"
            )
    return {
        "case_count": len(cases),
        "category_counts": counts,
    }


def validate_adapter_contracts() -> dict[str, object]:
    adapter = _load_yaml(ADAPTER)
    agent_map = _load_yaml(AGENT_MAP)

    if adapter.get("command_registry_ref") != "configs/tooling/zera_command_registry.yaml":
        raise ValidationError("Hermes adapter must point command_registry_ref at canonical Zera registry")
    if adapter.get("default_command_profile") != "zera:plan":
        raise ValidationError("Hermes adapter must default to zera:plan")

    command_resolution = adapter.get("command_resolution", {})
    if not isinstance(command_resolution, dict):
        raise ValidationError("Hermes adapter command_resolution must be a mapping")
    if command_resolution.get("source_of_truth") != "configs/tooling/zera_command_registry.yaml":
        raise ValidationError("Hermes adapter command_resolution must use the canonical command registry")
    if command_resolution.get("fallback_router") != "configs/tooling/zera_mode_router.json":
        raise ValidationError("Hermes adapter command_resolution must fall back to zera_mode_router.json")

    allowed_auto = set(command_resolution.get("allowed_auto_selection", []))
    disallowed_auto = set(command_resolution.get("disallowed_auto_selection", []))
    required_allowed = {"zera:plan", "zera:research", "zera:critic"}
    required_disallowed = {"zera:branch", "zera:evolve-capability", "zera:evolve-personality", "zera:governance-check", "zera:foundry-ingest"}
    if not required_allowed.issubset(allowed_auto):
        raise ValidationError("Hermes adapter missing required allowed_auto_selection commands")
    if not required_disallowed.issubset(disallowed_auto):
        raise ValidationError("Hermes adapter missing required disallowed_auto_selection commands")

    execution_modes = set(adapter.get("execution_modes", []))
    if not {"planner", "reviewer", "orchestrator", "brancher", "researcher", "governor"}.issubset(execution_modes):
        raise ValidationError("Hermes adapter missing required execution modes")

    for key in ("research-repo-scout", "execution-builder", "review-critic"):
        if key not in agent_map:
            raise ValidationError(f"Hermes agent map missing '{key}'")
    if agent_map.get("command_registry_ref") != "configs/tooling/zera_command_registry.yaml":
        raise ValidationError("Hermes agent map must reference canonical Zera registry")
    if agent_map["research-repo-scout"].get("command_id") != "zera:research":
        raise ValidationError("research-repo-scout must map to zera:research")
    if agent_map["execution-builder"].get("command_id") != "zera:architect":
        raise ValidationError("execution-builder must map to zera:architect")
    if agent_map["review-critic"].get("command_id") != "zera:critic":
        raise ValidationError("review-critic must map to zera:critic")

    return {
        "allowed_auto_selection": sorted(allowed_auto),
        "disallowed_auto_selection": sorted(disallowed_auto),
        "execution_modes": sorted(execution_modes),
    }


def validate_command_os_contracts() -> dict[str, object]:
    registry = _load_yaml(COMMAND_REGISTRY)
    clients = _load_yaml(CLIENT_PROFILES)
    branching = _load_yaml(BRANCH_POLICY)
    research = _load_yaml(RESEARCH_REGISTRY)
    foundry = _load_yaml(SKILL_FOUNDRY)
    imports = _load_yaml(EXTERNAL_IMPORTS)

    if registry.get("operator_model") != "mixed":
        raise ValidationError("Zera command registry must remain mixed-operator")
    ambient = registry.get("ambient_auto_suggestion", {})
    if not isinstance(ambient, dict):
        raise ValidationError("Zera command registry ambient_auto_suggestion must be a mapping")
    if not ambient.get("enabled") or not ambient.get("require_visible_explanation") or not ambient.get("require_telemetry"):
        raise ValidationError("Zera command registry must require visible, telemetry-backed ambient suggestions")
    only_for = set(ambient.get("only_for_risk_levels", []))
    if not {"low", "medium"}.issubset(only_for):
        raise ValidationError("Zera command registry ambient auto suggestion must be limited to low/medium risk levels")

    commands = registry.get("commands", {})
    if not isinstance(commands, dict):
        raise ValidationError("Zera command registry commands must be a mapping")
    missing_commands = sorted(REQUIRED_COMMANDS - set(commands))
    if missing_commands:
        raise ValidationError(f"Zera command registry missing commands: {', '.join(missing_commands)}")
    base_telemetry_fields = {"command_id", "client_id", "mode", "loop", "decision_reason", "rollback_path"}
    for command_id, row in commands.items():
        if not isinstance(row, dict):
            raise ValidationError(f"Command row must be a mapping: {command_id}")
        for key in (
            "intent_class",
            "mode_binding",
            "loop_binding",
            "action_class_expectation",
            "tool_profile",
            "model_transport_tier",
            "allowed_clients",
            "approval_route",
            "telemetry_schema",
            "rollback_path",
        ):
            if key not in row:
                raise ValidationError(f"{command_id} missing '{key}'")
        telemetry = row.get("telemetry_schema", {})
        if not isinstance(telemetry, dict):
            raise ValidationError(f"{command_id} telemetry_schema must be a mapping")
        required_fields = set(telemetry.get("required_fields", []))
        if not base_telemetry_fields.issubset(required_fields):
            raise ValidationError(f"{command_id} telemetry_schema missing base telemetry fields")
        if command_id in {"zera:branch", "zera:governance-check", "zera:foundry-ingest", "zera:evolve-capability", "zera:evolve-personality"}:
            specific_requirements = {
                "zera:branch": {"branch_type"},
                "zera:governance-check": {"governance_surface"},
                "zera:foundry-ingest": {"source_license", "import_lane"},
                "zera:evolve-capability": {"candidate_class"},
                "zera:evolve-personality": {"personality_axis"},
            }[command_id]
            if not specific_requirements.issubset(required_fields):
                raise ValidationError(f"{command_id} telemetry_schema missing command-specific fields: {', '.join(sorted(specific_requirements - required_fields))}")

    client_rows = clients.get("clients", {})
    if not isinstance(client_rows, dict):
        raise ValidationError("zera_client_profiles clients must be a mapping")
    for client_id in ("repo_native", "hermes", "gemini"):
        if client_id not in client_rows:
            raise ValidationError(f"zera_client_profiles missing {client_id}")
    secret_policy = clients.get("secret_policy", {})
    if not isinstance(secret_policy, dict):
        raise ValidationError("zera_client_profiles secret_policy must be a mapping")
    if not secret_policy.get("env_ref_only") or not secret_policy.get("inline_secret_forbidden") or not secret_policy.get("client_configs_must_not_define_command_semantics"):
        raise ValidationError("zera_client_profiles must enforce env-only secrets and command semantics isolation")

    branch_types = branching.get("branch_types", {})
    if not isinstance(branch_types, dict):
        raise ValidationError("zera_branching_policy branch_types must be a mapping")
    missing_branches = sorted(REQUIRED_BRANCH_TYPES - set(branch_types))
    if missing_branches:
        raise ValidationError(f"zera_branching_policy missing branch types: {', '.join(missing_branches)}")
    defaults = branching.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValidationError("zera_branching_policy defaults must be a mapping")
    if defaults.get("stable_memory_write_allowed") is not False:
        raise ValidationError("zera_branching_policy must forbid stable memory writes by default")
    if defaults.get("personality_promotion_allowed") is not False:
        raise ValidationError("zera_branching_policy must forbid personality promotion by default")
    if defaults.get("merge_requires_candidate_classification") is not True:
        raise ValidationError("zera_branching_policy must require candidate classification before merge")
    manifest_fields = set(branching.get("required_manifest_fields", []))
    if not {"branch_id", "branch_type", "parent_run_id", "source_command", "origin_prompt", "allowed_tools", "max_turns", "ttl_minutes", "merge_policy", "candidate_emission_allowed", "stable_memory_write_allowed", "personality_promotion_allowed"}.issubset(manifest_fields):
        raise ValidationError("zera_branching_policy missing required manifest fields")
    persona_branch = branch_types.get("persona_sensitivity_branch", {})
    if not isinstance(persona_branch, dict) or not persona_branch.get("requires_persona_review"):
        raise ValidationError("persona_sensitivity_branch must require persona review")

    source_card = research.get("source_card", {})
    required_source_fields = {
        "source_id",
        "source_url",
        "source_type",
        "license",
        "import_lane",
        "trust_score",
        "reverse_engineered_risk",
        "clean_room_required",
        "extracted_components",
        "allowed_usage_scope",
    }
    source_fields = set(source_card.get("required_fields", [])) if isinstance(source_card, dict) else set()
    if not required_source_fields.issubset(source_fields):
        raise ValidationError("zera_research_registry missing required source card fields")
    research_modes = research.get("research_modes", {})
    if not isinstance(research_modes, dict):
        raise ValidationError("zera_research_registry research_modes must be a mapping")
    if not {"zera:research", "zera:foundry-ingest"}.issubset(set(research_modes.get("ecosystem_mining", {}).get("allowed_commands", []))):
        raise ValidationError("zera_research_registry ecosystem_mining must include zera:research and zera:foundry-ingest")

    foundry_fields = set(foundry.get("required_candidate_fields", []))
    if not {"candidate_id", "candidate_type", "lane_owner", "provenance", "promotion_gate", "quarantine_status"}.issubset(foundry_fields):
        raise ValidationError("zera_skill_foundry missing required candidate fields")
    foundry_rules = foundry.get("rules", {})
    if not isinstance(foundry_rules, dict):
        raise ValidationError("zera_skill_foundry rules must be a mapping")
    if not foundry_rules.get("require_overlap_check") or not foundry_rules.get("prefer_existing_skill_extension") or not foundry_rules.get("external_code_requires_import_record") or not foundry_rules.get("no_auto_promotion_from_external_code"):
        raise ValidationError("zera_skill_foundry must enforce overlap, extension, import record, and no auto-promotion rules")

    import_rows = imports.get("imports", [])
    if not isinstance(import_rows, list) or len(import_rows) < 5:
        raise ValidationError("zera_external_imports must include at least 5 tracked imports")
    for row in import_rows:
        if not isinstance(row, dict):
            raise ValidationError("zera_external_imports rows must be mappings")
        for key in ("artifact_id", "source_repo", "license", "import_lane", "rollback_path", "owner", "review_status"):
            if key not in row:
                raise ValidationError(f"zera_external_imports row missing '{key}'")
    import_by_id = {row["artifact_id"]: row for row in import_rows if isinstance(row, dict) and "artifact_id" in row}
    if import_by_id.get("claurst-branching-mechanics", {}).get("import_lane") != "isolated_optional_component_only":
        raise ValidationError("claurst import lane must remain isolated_optional_component_only")
    if import_by_id.get("open-claude-code-workflow-oracle", {}).get("clean_room_required") is not True:
        raise ValidationError("open-claude-code import must remain clean-room-required")

    return {
        "commands": sorted(commands),
        "clients": sorted(client_rows),
        "branch_types": sorted(branch_types),
    }


def validate_import_and_source_safety() -> dict[str, object]:
    import_governance = _load_yaml(IMPORT_GOVERNANCE)
    source_trust = _load_yaml(SOURCE_TRUST)

    phases = import_governance.get("phases", {})
    for phase in ("quarantine", "review", "activation"):
        if phase not in phases:
            raise ValidationError(f"Import governance missing '{phase}' phase")
    quarantine_rules = phases["quarantine"].get("rules", [])
    if not isinstance(quarantine_rules, list):
        raise ValidationError("Import governance quarantine rules must be a list")
    flattened: dict[str, object] = {}
    for row in quarantine_rules:
        if isinstance(row, dict):
            flattened.update(row)
    if flattened.get("status_must_be") != "quarantined":
        raise ValidationError("Import governance must require quarantined status")
    if not str(flattened.get("must_create") or "").startswith("import_status.yaml"):
        raise ValidationError("Import governance must require an import_status.yaml manifest")
    if not flattened.get("must_run_collision_check"):
        raise ValidationError("Import governance must require collision checks")

    import_requirements = set(import_governance.get("import_requirements", []))
    required_import_requirements = {"import_status_yaml", "collision_report", "source_attribution", "agent_count", "review_status"}
    if not required_import_requirements.issubset(import_requirements):
        raise ValidationError("Import governance missing required import requirements")

    tiers = source_trust.get("tiers", {})
    if not isinstance(tiers, dict):
        raise ValidationError("source_trust_policy tiers must be a mapping")
    if source_trust.get("default_tier") != "Tier C":
        raise ValidationError("source_trust_policy default_tier must be Tier C")
    rules = source_trust.get("rules", {})
    if not isinstance(rules, dict):
        raise ValidationError("source_trust_policy rules must be a mapping")
    for tier in ("Tier A", "Tier B", "Tier C"):
        if tier not in tiers:
            raise ValidationError(f"source_trust_policy missing {tier}")
        if "allowed_for_capability_promotion" not in tiers[tier]:
            raise ValidationError(f"source_trust_policy tier {tier} missing allowed_for_capability_promotion")
    if rules.get("official_docs") != "Tier A" or rules.get("github_repo") != "Tier A":
        raise ValidationError("source_trust_policy must treat official docs and GitHub repos as Tier A")
    if rules.get("reddit") != "Tier C" or rules.get("youtube") != "Tier C":
        raise ValidationError("source_trust_policy must treat reddit/youtube as Tier C")

    return {
        "import_phases": sorted(phases),
        "import_requirements": sorted(import_requirements),
        "source_trust_rules": sorted(rules),
    }


def validate_harness_and_drift() -> dict[str, object]:
    harness = _load_yaml(HARNESS)
    drift = _load_yaml(DRIFT_RULES)

    scenarios = set(harness.get("scenario_coverage", []))
    missing_scenarios = sorted(REQUIRED_HARNESS_SCENARIOS - scenarios)
    if missing_scenarios:
        raise ValidationError(f"Evaluation harness missing scenarios: {', '.join(missing_scenarios)}")

    signals = set(drift.get("signals", []))
    missing_signals = sorted(REQUIRED_DRIFT_SIGNALS - signals)
    if missing_signals:
        raise ValidationError(f"Drift rules missing signals: {', '.join(missing_signals)}")

    responses = drift.get("responses", {})
    if not isinstance(responses, dict):
        raise ValidationError("Drift rules responses must be a mapping")
    for required_signal in (
        "zera_command_registry_drift",
        "zera_branch_policy_drift",
        "zera_client_parity_drift",
        "zera_governor_budget_breach",
        "zera_source_import_foundry_drift",
        "zera_runtime_telemetry_drift",
        "zera_branch_merge_classification_drift",
    ):
        if required_signal not in responses:
            raise ValidationError(f"Drift rules missing response for {required_signal}")

    return {
        "scenario_coverage": sorted(scenarios),
        "signals": sorted(signals),
    }


def validate_scripts() -> dict[str, object]:
    results: dict[str, list[str]] = {}
    for rel_path, required_snippets in TARGET_SCRIPTS.items():
        path = ROOT / rel_path
        if not path.exists():
            raise ValidationError(f"Missing script: {rel_path}")
        text = path.read_text(encoding="utf-8")
        missing = [snippet for snippet in required_snippets if snippet not in text]
        if missing:
            raise ValidationError(f"{rel_path} missing required snippets: {', '.join(missing)}")
        results[rel_path] = required_snippets

    evolve_text = (ROOT / "scripts/zera-evolve.sh").read_text(encoding="utf-8")
    if "делай итерации пока не скажу стоп" in evolve_text:
        raise ValidationError("scripts/zera-evolve.sh still contains unbounded iteration wording")
    return {"scripts_checked": list(TARGET_SCRIPTS)}


def validate_client_runtime_profiles() -> dict[str, object]:
    strict = os.getenv("ZERA_REQUIRE_CLIENT_PROFILES", "0") == "1"
    summary: dict[str, object] = {
        "strict_mode": strict,
        "hermes_profile_path": str(HERMES_PROFILE),
        "gemini_config_path": str(GEMINI_CONFIG),
    }

    if not HERMES_PROFILE.exists():
        if strict:
            raise ValidationError(f"Hermes profile not found: {HERMES_PROFILE}")
        summary["hermes_profile"] = "missing_optional"
    else:
        hermes_text = HERMES_PROFILE.read_text(encoding="utf-8")
        _assert_secret_hygiene(hermes_text, "Hermes profile")
        hermes_data = yaml.safe_load(hermes_text)
        if not isinstance(hermes_data, dict):
            raise ValidationError("Hermes profile must parse to a mapping")
        contract = hermes_data.get("zera_adapter_contract", {})
        if not isinstance(contract, dict):
            raise ValidationError("Hermes profile missing zera_adapter_contract mapping")
        required_refs = {
            "command_registry_ref": "configs/tooling/zera_command_registry.yaml",
            "client_profiles_ref": "configs/tooling/zera_client_profiles.yaml",
            "adapter_ref": "configs/adapters/hermes/adapter.yaml",
            "agent_map_ref": "configs/adapters/hermes/agent-map.yaml",
            "mode_router_ref": "configs/tooling/zera_mode_router.json",
            "growth_governance_ref": "configs/tooling/zera_growth_governance.json",
            "branch_policy_ref": "configs/tooling/zera_branching_policy.yaml",
        }
        for key, suffix in required_refs.items():
            if not _ref_matches(contract.get(key), suffix):
                raise ValidationError(f"Hermes zera_adapter_contract.{key} must reference {suffix}")
        if contract.get("semantics_source") != "repo":
            raise ValidationError("Hermes zera_adapter_contract.semantics_source must be 'repo'")
        if contract.get("default_namespace") != "zera:*":
            raise ValidationError("Hermes zera_adapter_contract.default_namespace must be 'zera:*'")
        secret_policy = hermes_data.get("secret_policy", {})
        if not isinstance(secret_policy, dict):
            raise ValidationError("Hermes profile secret_policy must be a mapping")
        if not secret_policy.get("env_ref_only") or not secret_policy.get("inline_secret_forbidden"):
            raise ValidationError("Hermes profile secret_policy must enforce env_ref_only + inline_secret_forbidden")
        summary["hermes_profile"] = "ok"

    if not GEMINI_CONFIG.exists():
        if strict:
            raise ValidationError(f"Gemini config not found: {GEMINI_CONFIG}")
        summary["gemini_config"] = "missing_optional"
    else:
        gemini_text = GEMINI_CONFIG.read_text(encoding="utf-8")
        _assert_secret_hygiene(gemini_text, "Gemini config")
        gemini_data = json.loads(gemini_text)
        if not isinstance(gemini_data, dict):
            raise ValidationError("Gemini config must parse to a mapping")
        control = gemini_data.get("zera_command_control", {})
        if not isinstance(control, dict):
            raise ValidationError("Gemini config missing zera_command_control mapping")
        required_refs = {
            "command_registry": "configs/tooling/zera_command_registry.yaml",
            "client_profiles": "configs/tooling/zera_client_profiles.yaml",
            "branching_policy": "configs/tooling/zera_branching_policy.yaml",
            "mode_router": "configs/tooling/zera_mode_router.json",
            "growth_governance": "configs/tooling/zera_growth_governance.json",
        }
        for key, suffix in required_refs.items():
            if not _ref_matches(control.get(key), suffix):
                raise ValidationError(f"Gemini zera_command_control.{key} must reference {suffix}")
        if control.get("semantics_source") != "repo":
            raise ValidationError("Gemini zera_command_control.semantics_source must be 'repo'")
        if control.get("default_command_namespace") != "zera:*":
            raise ValidationError("Gemini zera_command_control.default_command_namespace must be 'zera:*'")
        secret_policy = gemini_data.get("secret_policy", {})
        if not isinstance(secret_policy, dict):
            raise ValidationError("Gemini config secret_policy must be a mapping")
        if not secret_policy.get("env_ref_only") or not secret_policy.get("inline_secret_forbidden"):
            raise ValidationError("Gemini config secret_policy must enforce env_ref_only + inline_secret_forbidden")
        summary["gemini_config"] = "ok"

    return summary


def main() -> int:
    as_json = "--json" in sys.argv[1:]
    try:
        payload = {
            "governance": validate_governance(),
            "evals": validate_evals(),
            "command_os": validate_command_os_contracts(),
            "adapter_contracts": validate_adapter_contracts(),
            "client_runtime_profiles": validate_client_runtime_profiles(),
            "import_safety": validate_import_and_source_safety(),
            "harness_and_drift": validate_harness_and_drift(),
            "scripts": validate_scripts(),
            "status": "ok",
        }
        if as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("Zera hardening validation: OK")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except ValidationError as exc:
        if as_json:
            print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Zera hardening validation: ERROR\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
