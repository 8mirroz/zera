from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


class TestZeraHardeningAssets(unittest.TestCase):
    def test_governance_config_has_required_candidate_classes(self) -> None:
        path = ROOT / "configs" / "tooling" / "zera_growth_governance.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        classes = set(data.get("candidate_classes", {}))
        required = {
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
        self.assertTrue(required.issubset(classes))

    def test_eval_cases_cover_required_categories(self) -> None:
        path = ROOT / "configs" / "personas" / "zera" / "eval_cases.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        counts: dict[str, int] = {}
        for case in data["cases"]:
            counts[case["category"]] = counts.get(case["category"], 0) + 1

        self.assertGreaterEqual(counts.get("persona_stability", 0), 5)
        self.assertGreaterEqual(counts.get("autonomy_governance", 0), 5)
        self.assertGreaterEqual(counts.get("dual_loop_safety", 0), 5)
        self.assertGreaterEqual(counts.get("adversarial", 0), 5)
        self.assertGreaterEqual(counts.get("long_horizon_coherence", 0), 4)

    def test_scripts_reference_governance_controls(self) -> None:
        expectations = {
            ROOT / "scripts" / "zera-self-evolution.sh": ["GOVERNANCE_CONFIG=", "FREEZE_FILE=", "event_log"],
            ROOT / "scripts" / "zera-evolve.sh": ["GOVERNANCE_CONFIG=", "FREEZE_FILE=", "LOOPS_DIR=\"$VAULT/loops\"", "Run exactly one bounded self-evolution cycle."],
            ROOT / "scripts" / "zera-agent-intelligence.sh": ["PROMOTE_MEMORY=false", "GOVERNANCE_CONFIG=", "Stable persona-memory promotion is disabled by default"],
        }
        for path, snippets in expectations.items():
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for snippet in snippets:
                    self.assertIn(snippet, text)


if __name__ == "__main__":
    unittest.main()
