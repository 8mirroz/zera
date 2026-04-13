from __future__ import annotations

import os
import unittest
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


class TestZeraTelemetryContracts(unittest.TestCase):
    def test_command_telemetry_schemas_include_runtime_parity_fields(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        registry = _load_yaml("configs/tooling/zera_command_registry.yaml")

        base_fields = {"command_id", "client_id", "mode", "loop", "decision_reason", "rollback_path"}
        specific_fields = {
            "zera:plan": {"confidence"},
            "zera:research": {"source_count"},
            "zera:branch": {"branch_type"},
            "zera:calibrate": {"personality_axis"},
            "zera:evolve-capability": {"candidate_class"},
            "zera:evolve-personality": {"personality_axis"},
            "zera:governance-check": {"governance_surface"},
            "zera:foundry-ingest": {"source_license", "import_lane"},
        }

        for command_id, extras in specific_fields.items():
            row = registry["commands"][command_id]
            telemetry_fields = set(row["telemetry_schema"]["required_fields"])
            self.assertTrue(base_fields.issubset(telemetry_fields), command_id)
            self.assertTrue(extras.issubset(telemetry_fields), command_id)

            resolved = runtime.resolve_command(command_id=command_id, objective=f"exercise {command_id}", client_id="repo_native")
            self.assertEqual(resolved["command_id"], command_id)
            self.assertEqual(set(resolved["telemetry_schema"]["required_fields"]), telemetry_fields)

    def test_branch_manifests_and_governor_budgets_block_unsafe_promotion(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        branching = _load_yaml("configs/tooling/zera_branching_policy.yaml")
        governance = _load_yaml("configs/tooling/zera_growth_governance.json")

        defaults = branching["defaults"]
        self.assertFalse(defaults["stable_memory_write_allowed"])
        self.assertFalse(defaults["personality_promotion_allowed"])
        self.assertTrue(defaults["merge_requires_candidate_classification"])
        self.assertTrue(branching["branch_types"]["persona_sensitivity_branch"]["requires_persona_review"])

        manifest = runtime.create_branch_manifest(
            command_id="zera:evolve-personality",
            client_id="repo_native",
            branch_type="persona_sensitivity_branch",
            objective="Calibrate tone without drift",
            run_id="run-telemetry-001",
        )
        self.assertEqual(manifest["merge_policy"], "review_only")
        self.assertFalse(manifest["stable_memory_write_allowed"])
        self.assertFalse(manifest["personality_promotion_allowed"])
        self.assertTrue(manifest["requires_persona_review"])

        promotion_rules = governance["promotion_rules"]
        self.assertEqual(promotion_rules["max_significant_personality_deltas_per_cycle"], 1)
        self.assertTrue(promotion_rules["eval_required"])
        self.assertTrue(promotion_rules["rollback_required"])

    def test_import_registry_and_source_cards_preserve_quarantine_boundaries(self) -> None:
        runtime = ZeraCommandOS(ROOT)
        imports = _load_yaml("configs/tooling/zera_external_imports.yaml")["imports"]
        import_by_id = {row["artifact_id"]: row for row in imports}

        claurst = import_by_id["claurst-branching-mechanics"]
        self.assertEqual(claurst["import_lane"], "isolated_optional_component_only")
        self.assertEqual(claurst["review_status"], "quarantined_to_optional_boundary")
        self.assertTrue(claurst["rollback_path"])

        open_code = import_by_id["open-claude-code-workflow-oracle"]
        self.assertEqual(open_code["import_lane"], "concept_reference_quarantine")
        self.assertTrue(open_code["clean_room_required"])
        self.assertEqual(open_code["review_status"], "reference_only")

        source_card = runtime.create_source_card(
            source_id="source-open-claude-code",
            source_name="open-claude-code",
            extracted_components=["workflow_oracle"],
        )
        self.assertEqual(source_card["import_lane"], "concept_reference_quarantine")
        self.assertTrue(source_card["clean_room_required"])

        source_policy = load_source_trust_policy(ROOT)
        blocked = evaluate_source_tier_policy(source_policy, source_tier="Tier C", requests_capability_promotion=True)
        self.assertTrue(blocked["blocked"])

    def test_harness_and_drift_expose_runtime_parity_coverage(self) -> None:
        harness = _load_yaml("configs/tooling/evaluation-harness.yaml")
        drift = _load_yaml("configs/tooling/drift-detection-rules.yaml")

        scenarios = set(harness["scenario_coverage"])
        signals = set(drift["signals"])

        self.assertIn("zera_runtime_telemetry_contract", scenarios)
        self.assertIn("zera_branch_merge_enforcement", scenarios)
        self.assertIn("zera_runtime_telemetry_drift", signals)
        self.assertIn("zera_branch_merge_classification_drift", signals)
        for signal in ("zera_runtime_telemetry_drift", "zera_branch_merge_classification_drift"):
            self.assertIn(signal, drift["responses"])


if __name__ == "__main__":
    unittest.main()
