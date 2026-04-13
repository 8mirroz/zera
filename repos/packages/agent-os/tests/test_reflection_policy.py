from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.reflection_policy import evaluate_reflection_payload


def _base_payload() -> dict[str, object]:
    return {
        "summary": "The assistant repeats a bounded planning preference that should be stored for near-term reuse.",
        "improvement_area": "memory",
        "problem_statement": "Repeated short planning sessions re-collect the same local preference instead of reusing an already bounded memory signal.",
        "root_cause_hypothesis": "The runtime captures the preference in conversation but does not persist it as a short-lived memory tag.",
        "proposed_change": "Create a local memory tag for the repeated planning preference and keep it short-lived.",
        "expected_benefit": "Fewer repeated clarification turns in the next similar session.",
        "risk_assessment": {
            "risk_level": "low",
            "main_risks": [
                "The short-lived memory tag may expire before the next relevant session."
            ],
            "safety_impact": "none",
        },
        "bounded_action": {
            "action_type": "propose_memory_tag",
            "target": "planning.short_session.preference",
            "limit": "Write a short-lived working-memory tag only.",
        },
        "confidence": 0.82,
        "evidence_refs": [
            "trace:planning-session-1"
        ],
        "scope": "local",
        "success_criteria": [
            "A working-memory tag is stored for the next related session."
        ],
    }


class TestReflectionPolicy(unittest.TestCase):
    def test_memory_tag_can_auto_apply(self) -> None:
        result = evaluate_reflection_payload(ROOT, _base_payload(), run_id="run-memory-tag")
        self.assertTrue(result.valid)
        self.assertEqual(result.decision, "auto_apply_memory_tag")
        self.assertIsNotNone(result.memory_update)
        self.assertTrue(str((result.memory_update or {}).get("key") or "").startswith("reflection:run-memory-tag:"))

    def test_low_confidence_routes_to_review(self) -> None:
        payload = _base_payload()
        payload["confidence"] = 0.40
        result = evaluate_reflection_payload(ROOT, payload, run_id="run-low-confidence")
        self.assertTrue(result.valid)
        self.assertEqual(result.decision, "review_required")
        self.assertIn("confidence below 0.45 requires operator review", result.review_reasons)

    def test_high_risk_without_rollback_is_invalid(self) -> None:
        payload = _base_payload()
        payload["risk_assessment"] = {
            "risk_level": "high",
            "main_risks": [
                "The change could affect multiple response pathways."
            ],
            "safety_impact": "limited",
        }
        payload["validation_plan"] = {
            "method": "offline_eval",
            "checks": [
                "Measure regression rate in related traces."
            ],
        }
        result = evaluate_reflection_payload(ROOT, payload, run_id="run-high-risk")
        self.assertFalse(result.valid)
        self.assertEqual(result.decision, "invalid")
        self.assertTrue(any("rollback_plan" in error for error in result.errors))

    def test_extra_field_is_invalid(self) -> None:
        payload = _base_payload()
        payload["unexpected_field"] = "not allowed"
        result = evaluate_reflection_payload(ROOT, payload, run_id="run-extra-field")
        self.assertFalse(result.valid)
        self.assertEqual(result.decision, "invalid")
        self.assertTrue(any("additional properties" in error.lower() for error in result.errors))

    def test_evaluation_only_requires_request_operator_review(self) -> None:
        payload = _base_payload()
        payload["change_type"] = "evaluation_only"
        result = evaluate_reflection_payload(ROOT, payload, run_id="run-evaluation-only")
        self.assertFalse(result.valid)
        self.assertEqual(result.decision, "invalid")
        self.assertTrue(any("request_operator_review" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
