from __future__ import annotations

import unittest
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.source_trust import evaluate_source_tier_policy, load_source_trust_policy
from agent_os.zera_command_os import ZeraCommandOS


def _load_yaml(rel_path: str) -> dict:
    path = ROOT / rel_path
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), f"{rel_path} must parse to a mapping"
    return data


def _merge_rule_entries(rules: list[object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for row in rules:
        if isinstance(row, dict):
            merged.update(row)
    return merged


class TestZeraHermesCommandParity(unittest.TestCase):
    def test_command_registry_and_client_profiles_are_complete(self) -> None:
        registry = _load_yaml("configs/tooling/zera_command_registry.yaml")
        clients = _load_yaml("configs/tooling/zera_client_profiles.yaml")
        branching = _load_yaml("configs/tooling/zera_branching_policy.yaml")

        commands = registry["commands"]
        required = {
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
        self.assertTrue(required.issubset(set(commands)))
        for command_id in required:
            row = commands[command_id]
            for key in ("intent_class", "mode_binding", "loop_binding", "allowed_clients", "approval_route", "rollback_path"):
                self.assertIn(key, row, f"{command_id} missing {key}")

        self.assertTrue({"repo_native", "hermes", "gemini"}.issubset(set(clients["clients"])))
        self.assertTrue(
            {
                "strategy_branch",
                "research_branch",
                "red_team_branch",
                "execution_branch",
                "persona_sensitivity_branch",
            }.issubset(set(branching["branch_types"]))
        )

    def test_hermes_adapter_binds_canonical_command_registry(self) -> None:
        adapter = _load_yaml("configs/adapters/hermes/adapter.yaml")
        self.assertEqual(adapter["command_registry_ref"], "configs/tooling/zera_command_registry.yaml")
        self.assertEqual(adapter["default_command_profile"], "zera:plan")
        self.assertEqual(adapter["command_resolution"]["source_of_truth"], "configs/tooling/zera_command_registry.yaml")
        self.assertEqual(adapter["command_resolution"]["fallback_router"], "configs/tooling/zera_mode_router.json")

        allowed = set(adapter["command_resolution"]["allowed_auto_selection"])
        disallowed = set(adapter["command_resolution"]["disallowed_auto_selection"])
        self.assertTrue({"zera:plan", "zera:research", "zera:critic"}.issubset(allowed))
        self.assertTrue({"zera:branch", "zera:evolve-capability", "zera:evolve-personality", "zera:governance-check", "zera:foundry-ingest"}.issubset(disallowed))
        self.assertTrue({"planner", "reviewer", "orchestrator", "brancher", "researcher", "governor"}.issubset(set(adapter["execution_modes"])))

    def test_hermes_agent_map_command_ids_align_with_registry(self) -> None:
        agent_map = _load_yaml("configs/adapters/hermes/agent-map.yaml")
        self.assertEqual(agent_map["command_registry_ref"], "configs/tooling/zera_command_registry.yaml")
        self.assertEqual(agent_map["research-repo-scout"]["command_id"], "zera:research")
        self.assertEqual(agent_map["execution-builder"]["command_id"], "zera:architect")
        self.assertEqual(agent_map["review-critic"]["command_id"], "zera:critic")

    def test_command_runtime_resolves_and_degrades_clients_consistently(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        repo_plan = runtime.resolve_command(command_id="zera:plan", objective="Собери план", client_id="repo_native")
        hermes_plan = runtime.resolve_command(command_id="zera:plan", objective="Собери план", client_id="hermes")
        gemini_evolve = runtime.resolve_command(
            command_id="zera:evolve-capability",
            objective="Запусти bounded capability evolution",
            client_id="gemini",
        )

        self.assertEqual(repo_plan["command_id"], "zera:plan")
        self.assertEqual(hermes_plan["command_id"], "zera:plan")
        self.assertTrue(gemini_evolve["degraded"])
        self.assertEqual(gemini_evolve["command_id"], "zera:research")

    def test_command_runtime_creates_branch_manifest_with_guardrails(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        manifest = runtime.create_branch_manifest(
            command_id="zera:evolve-personality",
            client_id="repo_native",
            branch_type="persona_sensitivity_branch",
            objective="Calibrate warmth without drift",
            run_id="run-123",
        )
        self.assertEqual(manifest["branch_type"], "persona_sensitivity_branch")
        self.assertFalse(manifest["stable_memory_write_allowed"])
        self.assertFalse(manifest["personality_promotion_allowed"])
        self.assertTrue(manifest["requires_persona_review"])


class TestZeraImportAndSourceSafety(unittest.TestCase):
    def test_import_governance_requires_quarantine_and_review_metadata(self) -> None:
        policy = _load_yaml("configs/policies/import_governance.yaml")
        phases = policy["phases"]
        for phase in ("quarantine", "review", "activation"):
            self.assertIn(phase, phases)

        quarantine_rules = _merge_rule_entries(phases["quarantine"]["rules"])
        self.assertEqual(quarantine_rules["status_must_be"], "quarantined")
        self.assertTrue(quarantine_rules["must_run_collision_check"])
        self.assertIn("import_status.yaml", quarantine_rules["must_create"])

        requirements = set(policy["import_requirements"])
        self.assertTrue({"import_status_yaml", "collision_report", "source_attribution", "agent_count", "review_status"}.issubset(requirements))

    def test_source_trust_policy_blocks_tier_c_promotion(self) -> None:
        policy = load_source_trust_policy(ROOT)
        self.assertEqual(policy["default_tier"], "Tier C")
        self.assertTrue(policy["tiers"]["Tier A"]["allowed_for_capability_promotion"])
        self.assertTrue(policy["tiers"]["Tier B"]["allowed_for_capability_promotion"])
        self.assertFalse(policy["tiers"]["Tier C"]["allowed_for_capability_promotion"])

        blocked = evaluate_source_tier_policy(policy, source_tier="Tier C", requests_capability_promotion=True)
        allowed = evaluate_source_tier_policy(policy, source_tier="Tier A", requests_capability_promotion=True)
        self.assertTrue(blocked["blocked"])
        self.assertFalse(allowed["blocked"])
        self.assertEqual(policy["rules"]["official_docs"], "Tier A")
        self.assertEqual(policy["rules"]["github_repo"], "Tier A")

    def test_external_import_registry_tracks_expected_sources(self) -> None:
        imports = _load_yaml("configs/tooling/zera_external_imports.yaml")
        rows = imports["imports"]
        artifact_ids = {row["artifact_id"] for row in rows}
        self.assertTrue(
            {
                "superclaude-framework-command-taxonomy",
                "claude-code-open-provider-bridge-patterns",
                "claurst-branching-mechanics",
                "open-claude-code-workflow-oracle",
                "awesome-claude-code-discovery-feed",
            }.issubset(artifact_ids)
        )

    def test_research_registry_has_required_source_card_fields(self) -> None:
        registry = _load_yaml("configs/tooling/zera_research_registry.yaml")
        fields = set(registry["source_card"]["required_fields"])
        self.assertTrue(
            {
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
            }.issubset(fields)
        )


class TestZeraReliabilityScenarios(unittest.TestCase):
    def test_evaluation_harness_covers_hybrid_pilot_scenarios(self) -> None:
        harness = _load_yaml("configs/tooling/evaluation-harness.yaml")
        scenarios = set(harness["scenario_coverage"])
        required = {
            "zera_command_registry_parity",
            "zera_branch_lifecycle",
            "zera_client_parity",
            "zera_governor_budget",
            "zera_source_import_foundry_safety",
        }
        self.assertTrue(required.issubset(scenarios))

    def test_drift_rules_cover_hybrid_pilot_signals(self) -> None:
        drift = _load_yaml("configs/tooling/drift-detection-rules.yaml")
        signals = set(drift["signals"])
        required = {
            "zera_command_registry_drift",
            "zera_branch_policy_drift",
            "zera_client_parity_drift",
            "zera_governor_budget_breach",
            "zera_source_import_foundry_drift",
        }
        self.assertTrue(required.issubset(signals))
        for signal in required:
            self.assertIn(signal, drift["responses"])


if __name__ == "__main__":
    unittest.main()
