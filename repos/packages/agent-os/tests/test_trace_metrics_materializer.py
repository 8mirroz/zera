from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS))

import trace_metrics_materializer as tmm


class TestTraceMetricsMaterializer(unittest.TestCase):
    def test_materializes_v2_metrics(self) -> None:
        rows = [
            {
                "ts": "2026-02-23T23:00:00+00:00",
                "run_id": "run-a",
                "event_type": "triage_decision",
                "level": "info",
                "component": "triage",
                "task_type": "T3",
                "complexity": "C3",
                "model_tier": "quality",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:01+00:00",
                "run_id": "run-a",
                "event_type": "verification_result",
                "level": "info",
                "component": "verifier",
                "status": "pass",
                "task_type": "T3",
                "complexity": "C3",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:02+00:00",
                "run_id": "run-a",
                "event_type": "tool_call",
                "level": "info",
                "component": "tool",
                "tool_name": "filesystem",
                "status": "ok",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:03+00:00",
                "run_id": "run-a",
                "event_type": "tool_call",
                "level": "info",
                "component": "tool",
                "tool_name": "pytest",
                "status": "error",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:04+00:00",
                "run_id": "run-a",
                "event_type": "retro_written",
                "level": "info",
                "component": "retro",
                "status": "ok",
                "task_type": "T3",
                "complexity": "C3",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:05+00:00",
                "run_id": "run-a",
                "event_type": "ralph_iteration_scored",
                "level": "info",
                "component": "ralph",
                "status": "ok",
                "task_type": "T3",
                "complexity": "C3",
                "data": {"weighted_total": 0.71},
            },
            {
                "ts": "2026-02-23T23:00:06+00:00",
                "run_id": "run-a",
                "event_type": "ralph_iteration_scored",
                "level": "info",
                "component": "ralph",
                "status": "ok",
                "task_type": "T3",
                "complexity": "C3",
                "data": {"weighted_total": 0.83},
            },
            {
                "ts": "2026-02-23T23:00:07+00:00",
                "run_id": "run-a",
                "event_type": "task_run_summary",
                "level": "info",
                "component": "agent",
                "status": "success",
                "task_type": "T3",
                "complexity": "C3",
                "data": {"tool_calls_total": 2, "tool_calls_success": 1},
            },
            {
                "ts": "2026-02-23T23:00:08+00:00",
                "run_id": "run-a",
                "event_type": "runtime_provider_fallback",
                "level": "warn",
                "component": "agent",
                "runtime_provider": "agent_os_python",
                "status": "warn",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:09+00:00",
                "run_id": "run-a",
                "event_type": "background_job_started",
                "level": "info",
                "component": "agent",
                "background_job_type": "goal_review",
                "status": "ok",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:10+00:00",
                "run_id": "run-a",
                "event_type": "background_job_completed",
                "level": "info",
                "component": "agent",
                "background_job_type": "goal_review",
                "status": "completed",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:11+00:00",
                "run_id": "run-a",
                "event_type": "persona_eval_scored",
                "level": "info",
                "component": "eval",
                "status": "pass",
                "data": {"persona_version": "zera-v1"},
            },
            {
                "ts": "2026-02-23T23:00:12+00:00",
                "run_id": "run-a",
                "event_type": "memory_retrieval_scored",
                "level": "info",
                "component": "memory",
                "status": "ok",
                "data": {"hits": 2},
            },
            {
                "ts": "2026-02-23T23:00:13+00:00",
                "run_id": "run-a",
                "event_type": "autonomy_decision",
                "level": "info",
                "component": "policy",
                "status": "ok",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:14+00:00",
                "run_id": "run-a",
                "event_type": "approval_gate_triggered",
                "level": "warn",
                "component": "policy",
                "status": "warn",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:15+00:00",
                "run_id": "run-a",
                "event_type": "stop_signal_received",
                "level": "warn",
                "component": "policy",
                "status": "warn",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:16+00:00",
                "run_id": "run-a",
                "event_type": "stop_signal_honored",
                "level": "info",
                "component": "policy",
                "status": "completed",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:17+00:00",
                "run_id": "run-a",
                "event_type": "proof_of_action_recorded",
                "level": "info",
                "component": "agent",
                "status": "ok",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:18+00:00",
                "run_id": "run-a",
                "event_type": "budget_limit_hit",
                "level": "warn",
                "component": "policy",
                "status": "warn",
                "data": {},
            },
            {
                "ts": "2026-02-23T23:00:19+00:00",
                "run_id": "run-a",
                "event_type": "self_reflection_written",
                "level": "info",
                "component": "eval",
                "status": "ok",
                "data": {
                    "schema_name": "zera_reflection_improvement_protocol",
                    "schema_version": "2026-03-11",
                },
            },
            {
                "ts": "2026-02-23T23:00:20+00:00",
                "run_id": "run-a",
                "event_type": "policy_violation_detected",
                "level": "error",
                "component": "eval",
                "status": "error",
                "data": {
                    "reflection_validation": {
                        "valid": False,
                        "errors": ["missing required field: proposed_change"],
                    }
                },
            },
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "trace.jsonl"
            p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            out = tmm.materialize_metrics(p, allow_legacy=False)

        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["normalization"]["v2_rows"], len(rows))
        self.assertEqual(out["kpis"]["pass_rate"]["value"], 1.0)
        self.assertEqual(out["kpis"]["tool_success_rate"]["value"], 0.5)
        self.assertEqual(out["kpis"]["capture_coverage"]["value"], 1.0)
        self.assertEqual(out["kpis"]["ralph_best_of_n_uplift"]["value"], 0.12)
        self.assertEqual(out["kpis"]["background_job_success_rate"]["value"], 1.0)
        self.assertEqual(out["kpis"]["persona_eval_pass_rate"]["value"], 1.0)
        self.assertEqual(out["kpis"]["memory_retrieval_hit_rate"]["value"], 1.0)
        self.assertEqual(out["kpis"]["autonomy_gate_rate"]["value"], 1.0)
        self.assertEqual(out["kpis"]["stop_signal_compliance"]["value"], 1.0)
        self.assertEqual(out["kpis"]["proof_of_action_coverage"]["value"], 1.0)
        self.assertEqual(out["kpis"]["budget_limit_hit_rate"]["value"], 1.0)
        self.assertEqual(out["kpis"]["self_reflection_valid_rate"]["value"], 0.5)
        self.assertEqual(out["kpis"]["self_reflection_rejection_rate"]["value"], 0.5)
        self.assertEqual(out["kpis"]["self_reflection_schema_coverage"]["value"], 1.0)

    def test_materializes_legacy_rows_when_enabled(self) -> None:
        legacy = {
            "schema_version": "1.0",
            "entry": {
                "timestamp": "2026-02-23T23:00:00Z",
                "run_id": "legacy-1",
                "task_type": "T4",
                "complexity": "C4",
                "path": "swarm",
                "ralph_loop": {
                    "enabled": True,
                    "iteration": 1,
                    "total_iterations": 3,
                    "model_used": "deepseek-v3-free",
                    "score": {"weighted_total": 0.88},
                    "selected_as_best": True,
                },
                "tool_calls_total": 5,
                "tool_calls_success": 4,
                "outcome": "success",
                "ki_generated": True,
                "pattern_extracted": True,
            },
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "trace.jsonl"
            p.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
            out = tmm.materialize_metrics(p, allow_legacy=True)

        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["normalization"]["legacy_rows"], 1)
        self.assertEqual(out["event_counts"]["task_run_summary"], 1)
        self.assertEqual(out["event_counts"]["retro_written"], 1)
        self.assertEqual(out["event_counts"]["ralph_iteration_scored"], 1)
        self.assertEqual(out["kpis"]["pass_rate"]["source"], "task_run_summary_fallback")
        self.assertEqual(out["kpis"]["pass_rate"]["value"], 1.0)
        self.assertEqual(out["kpis"]["tool_success_rate"]["source"], "task_run_summary_fallback")
        self.assertEqual(out["kpis"]["tool_success_rate"]["value"], 0.8)


if __name__ == "__main__":
    unittest.main()
