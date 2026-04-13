from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import swarmctl


class TestSwarmctlBenchmark(unittest.TestCase):
    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_cmd_benchmark_success_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            suite_path = repo / "suite.json"
            out_path = repo / "out" / "benchmark.json"
            self._write_json(
                suite_path,
                {
                    "test_cases": [
                        {
                            "id": "case-ok",
                            "task_type": "T3",
                            "complexity": "C3",
                            "description": "Implement endpoint and tests",
                            "expected_path": "Quality Path",
                            "max_tools": 10,
                            "max_duration_seconds": 30,
                            "success_criteria": ["no_escalation", "retro_written"],
                        }
                    ]
                },
            )

            route_ctx = {
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Quality Path",
                    "max_tools": 3,
                    "telemetry": {"max_total_tokens": 1000, "v4_max_tools": 3},
                },
                "mcp_profile": "core",
                "cost_budget": 0.2,
            }
            run_payload = {"agent": {"status": "completed"}}
            metrics = {
                "total_duration_ms": 1200,
                "token_usage": {"input_tokens": 120, "output_tokens": 80},
                "cost_estimate_usd": 0.0,
                "summary_data": {"retro_written": True},
            }

            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "_default_budgets", return_value=(1000, 0.2)
            ), patch.object(swarmctl, "resolve_route_context", return_value=route_ctx), patch.object(
                swarmctl, "_run_agent_pipeline", return_value=(run_payload, metrics)
            ), patch.object(
                swarmctl, "emit_event"
            ), redirect_stdout(
                out
            ):
                rc = swarmctl.cmd_benchmark(
                    SimpleNamespace(suite=str(suite_path), mode=None, fail_fast=False, out=str(out_path))
                )

            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["cases_total"], 1)
            self.assertEqual(payload["cases_passed"], 1)
            self.assertEqual(payload["pass_rate"], 1.0)
            self.assertIn("axis_scores", payload)
            self.assertIsNotNone(payload["axis_scores"]["performance"])
            self.assertTrue(out_path.exists())
            written = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(written["run_id"], payload["run_id"])

    def test_cmd_benchmark_tags_variant_repeat_and_disqualifies_missing_verification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            suite_path = repo / "suite.json"
            self._write_json(
                suite_path,
                {
                    "test_cases": [
                        {
                            "id": "case-self-verify",
                            "task_type": "T3",
                            "complexity": "C3",
                            "description": "Implement endpoint and tests",
                            "expected_path": "Quality Path",
                            "max_tools": 10,
                            "max_duration_seconds": 30,
                            "success_criteria": [],
                        }
                    ]
                },
            )

            route_ctx = {
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Quality Path",
                    "max_tools": 3,
                    "telemetry": {"max_total_tokens": 1000, "v4_max_tools": 3},
                },
                "mcp_profile": "core",
                "cost_budget": 0.2,
            }
            run_payload = {"agent": {"status": "completed"}}
            metrics = {
                "total_duration_ms": 1200,
                "token_usage": {"input_tokens": 120, "output_tokens": 80},
                "cost_estimate_usd": 0.0,
                "summary_data": {"verification_status": "not-run"},
            }

            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "_default_budgets", return_value=(1000, 0.2)
            ), patch.object(swarmctl, "resolve_route_context", return_value=route_ctx), patch.object(
                swarmctl, "_run_agent_pipeline", return_value=(run_payload, metrics)
            ) as pipeline_mock, patch.object(
                swarmctl, "emit_event"
            ), redirect_stdout(
                out
            ):
                rc = swarmctl.cmd_benchmark(
                    SimpleNamespace(
                        suite=str(suite_path),
                        mode=None,
                        fail_fast=False,
                        out=None,
                        algorithm_variant="self_verify_gate",
                        matrix=None,
                        repeat=2,
                        real_trace_sample=0,
                        execution_channel="auto",
                    )
                )

            self.assertEqual(rc, 2)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["algorithm_variant"], "self_verify_gate")
            self.assertEqual(payload["repeat"], 2)
            self.assertEqual(payload["cases_total"], 2)
            self.assertEqual(payload["cases_passed"], 0)
            self.assertTrue(payload["promotion_gate"]["disqualified"])
            self.assertIn("pass_rate_below_threshold", payload["promotion_gate"]["reasons"])
            self.assertEqual(pipeline_mock.call_count, 2)
            self.assertFalse(payload["results"][0]["checks"]["self_verify_gate"])

    def test_cmd_benchmark_adds_real_trace_sample_cases(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            suite_path = repo / "suite.json"
            trace_path = repo / "logs" / "agent_traces.jsonl"
            self._write_json(
                suite_path,
                {
                    "test_cases": [
                        {
                            "id": "case-suite",
                            "task_type": "T3",
                            "complexity": "C3",
                            "description": "Suite task",
                            "expected_path": "Quality Path",
                            "max_tools": 10,
                            "max_duration_seconds": 30,
                            "success_criteria": [],
                        }
                    ]
                },
            )
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text(
                json.dumps(
                    {
                        "event_type": "task_run_summary",
                        "run_id": "trace-run-1",
                        "component": "agent",
                        "status": "completed",
                        "task_type": "T2",
                        "complexity": "C2",
                        "data": {"objective": "Fix trace-derived lint issue"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            route_ctx = {
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Quality Path",
                    "max_tools": 3,
                    "telemetry": {"max_total_tokens": 1000, "v4_max_tools": 3},
                },
                "mcp_profile": "core",
                "cost_budget": 0.2,
            }
            run_payload = {"agent": {"status": "completed"}}
            metrics = {
                "total_duration_ms": 1200,
                "token_usage": {"input_tokens": 120, "output_tokens": 80},
                "cost_estimate_usd": 0.0,
                "summary_data": {"verification_status": "passed"},
            }

            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "_default_budgets", return_value=(1000, 0.2)
            ), patch.object(swarmctl, "resolve_route_context", return_value=route_ctx), patch.object(
                swarmctl, "_run_agent_pipeline", return_value=(run_payload, metrics)
            ), patch.object(
                swarmctl, "emit_event"
            ), redirect_stdout(
                out
            ):
                rc = swarmctl.cmd_benchmark(
                    SimpleNamespace(
                        suite=str(suite_path),
                        mode=None,
                        fail_fast=False,
                        out=None,
                        algorithm_variant="spec_to_contract_gate",
                        matrix=None,
                        repeat=1,
                        real_trace_sample=1,
                        execution_channel="auto",
                    )
                )

            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["cases_total"], 2)
            self.assertEqual(payload["real_trace_sample"]["added_cases"], 1)
            self.assertIn("real-trace-", payload["results"][1]["id"])

    def test_confidence_weighted_variant_prefers_cli_qwen_channel(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            suite_path = repo / "suite.json"
            self._write_json(
                suite_path,
                {
                    "test_cases": [
                        {
                            "id": "case-confidence",
                            "task_type": "T4",
                            "complexity": "C4",
                            "description": "Architect a service with contracts",
                            "expected_path": "Swarm Path",
                            "max_tools": 30,
                            "max_duration_seconds": 60,
                            "success_criteria": [],
                        }
                    ]
                },
            )
            route_ctx = {
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Swarm Path",
                    "max_tools": 3,
                    "telemetry": {"max_total_tokens": 1000, "v4_max_tools": 3},
                },
                "mcp_profile": "core",
                "cost_budget": 0.2,
            }
            run_payload = {"agent": {"status": "completed"}}
            metrics = {
                "total_duration_ms": 1200,
                "token_usage": {"input_tokens": 120, "output_tokens": 80},
                "cost_estimate_usd": 0.0,
                "summary_data": {"verification_status": "passed"},
            }

            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "_default_budgets", return_value=(1000, 0.2)
            ), patch.object(swarmctl, "resolve_route_context", return_value=route_ctx) as route_mock, patch.object(
                swarmctl, "_run_agent_pipeline", return_value=(run_payload, metrics)
            ), patch.object(
                swarmctl, "emit_event"
            ), redirect_stdout(
                out
            ):
                rc = swarmctl.cmd_benchmark(
                    SimpleNamespace(
                        suite=str(suite_path),
                        mode=None,
                        fail_fast=False,
                        out=None,
                        algorithm_variant="confidence_weighted_escalation",
                        matrix=None,
                        repeat=1,
                        real_trace_sample=0,
                        execution_channel="auto",
                    )
                )

            self.assertEqual(rc, 0)
            self.assertEqual(route_mock.call_args.kwargs["execution_channel"], "cli_qwen")
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["openrouter_fallbacks_allowed"], 1)

    def test_cmd_benchmark_fail_fast_stops_on_first_failed_case(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            suite_path = repo / "suite.json"
            self._write_json(
                suite_path,
                {
                    "test_cases": [
                        {
                            "id": "case-fail",
                            "task_type": "T3",
                            "complexity": "C3",
                            "description": "First case",
                            "expected_path": "Quality Path",
                            "max_tools": 10,
                            "max_duration_seconds": 30,
                            "success_criteria": ["retro_written"],
                        },
                        {
                            "id": "case-skip",
                            "task_type": "T3",
                            "complexity": "C3",
                            "description": "Second case",
                            "expected_path": "Quality Path",
                            "max_tools": 10,
                            "max_duration_seconds": 30,
                            "success_criteria": ["retro_written"],
                        },
                    ]
                },
            )

            route_ctx = {
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Quality Path",
                    "max_tools": 3,
                    "telemetry": {"max_total_tokens": 1000, "v4_max_tools": 3},
                },
                "mcp_profile": "core",
                "cost_budget": 0.2,
            }
            failing_payload = {"agent": {"status": "completed"}}
            failing_metrics = {
                "total_duration_ms": 1000,
                "token_usage": {"input_tokens": 100, "output_tokens": 100},
                "cost_estimate_usd": 0.0,
                "summary_data": {"retro_written": False},
            }

            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "_default_budgets", return_value=(1000, 0.2)
            ), patch.object(swarmctl, "resolve_route_context", return_value=route_ctx) as route_mock, patch.object(
                swarmctl, "_run_agent_pipeline", return_value=(failing_payload, failing_metrics)
            ) as pipeline_mock, patch.object(
                swarmctl, "emit_event"
            ), redirect_stdout(
                out
            ):
                rc = swarmctl.cmd_benchmark(SimpleNamespace(suite=str(suite_path), mode=None, fail_fast=True, out=None))

            self.assertEqual(rc, 2)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["cases_total"], 1)
            self.assertEqual(payload["cases_passed"], 0)
            self.assertEqual(route_mock.call_count, 1)
            self.assertEqual(pipeline_mock.call_count, 1)

    def test_cmd_benchmark_blocks_tier_c_capability_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            suite_path = repo / "suite.json"
            self._write_json(
                suite_path,
                {
                    "test_cases": [
                        {
                            "id": "case-tier-c-promotion",
                            "task_type": "T7",
                            "complexity": "C2",
                            "description": "Unsafe promotion scenario",
                            "expected_path": "Fast Path",
                            "max_tools": 10,
                            "max_duration_seconds": 30,
                            "source_tier": "Tier C",
                            "requests_capability_promotion": True,
                            "success_criteria": [],
                        }
                    ]
                },
            )
            source_policy = repo / "configs/tooling/source_trust_policy.yaml"
            source_policy.parent.mkdir(parents=True, exist_ok=True)
            source_policy.write_text(
                "\n".join(
                    [
                        "default_tier: \"Tier C\"",
                        "tiers:",
                        "  Tier A:",
                        "    allowed_for_capability_promotion: true",
                        "  Tier B:",
                        "    allowed_for_capability_promotion: true",
                        "  Tier C:",
                        "    allowed_for_capability_promotion: false",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            route_ctx = {
                "route": {
                    "primary_model": "ollama/qwen3:4b",
                    "orchestration_path": "Fast Path",
                    "max_tools": 3,
                    "telemetry": {"max_total_tokens": 1000, "v4_max_tools": 3},
                },
                "mcp_profile": "core",
                "cost_budget": 0.2,
            }
            run_payload = {"agent": {"status": "completed"}}
            metrics = {
                "total_duration_ms": 900,
                "token_usage": {"input_tokens": 100, "output_tokens": 100},
                "cost_estimate_usd": 0.0,
                "summary_data": {},
            }

            out = io.StringIO()
            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.object(
                swarmctl, "_default_budgets", return_value=(1000, 0.2)
            ), patch.object(swarmctl, "resolve_route_context", return_value=route_ctx), patch.object(
                swarmctl, "_run_agent_pipeline", return_value=(run_payload, metrics)
            ), patch.object(swarmctl, "emit_event"), redirect_stdout(out):
                rc = swarmctl.cmd_benchmark(SimpleNamespace(suite=str(suite_path), mode=None, fail_fast=False, out=None))

            self.assertEqual(rc, 2)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["cases_total"], 1)
            self.assertEqual(payload["cases_passed"], 0)
            self.assertEqual(payload["source_policy"]["blocked_cases"], 1)
            self.assertFalse(payload["results"][0]["checks"]["source_tier_policy"])


if __name__ == "__main__":
    unittest.main()
