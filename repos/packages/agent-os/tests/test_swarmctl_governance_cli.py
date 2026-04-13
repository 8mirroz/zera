from __future__ import annotations

import io
import json
import os
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


class TestSwarmctlGovernanceCli(unittest.TestCase):
    def _write_trace(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    def test_scorecard_and_rollout_gate_pass(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace = repo / "logs/agent_traces.jsonl"
            rows = [
                {"ts": "2026-03-11T00:00:00+00:00", "run_id": "run-1", "event_type": "runtime_provider_fallback", "level": "warn", "component": "agent", "status": "warn", "data": {}},
                {"ts": "2026-03-11T00:00:01+00:00", "run_id": "run-1", "event_type": "background_job_started", "level": "info", "component": "agent", "status": "ok", "data": {}},
                {"ts": "2026-03-11T00:00:02+00:00", "run_id": "run-1", "event_type": "background_job_completed", "level": "info", "component": "agent", "status": "completed", "data": {}},
                {"ts": "2026-03-11T00:00:03+00:00", "run_id": "run-1", "event_type": "stop_signal_received", "level": "warn", "component": "policy", "status": "warn", "data": {}},
                {"ts": "2026-03-11T00:00:04+00:00", "run_id": "run-1", "event_type": "stop_signal_honored", "level": "info", "component": "policy", "status": "completed", "data": {}},
                {"ts": "2026-03-11T00:00:05+00:00", "run_id": "run-1", "event_type": "proof_of_action_recorded", "level": "info", "component": "agent", "status": "ok", "data": {}},
                {
                    "ts": "2026-03-11T00:00:06+00:00",
                    "run_id": "run-1",
                    "event_type": "self_reflection_written",
                    "level": "info",
                    "component": "eval",
                    "status": "ok",
                    "data": {"schema_name": "zera_reflection_improvement_protocol", "schema_version": "2026-03-11"},
                },
            ]
            self._write_trace(trace, rows)

            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.dict(
                os.environ, {"AGENT_OS_TRACE_FILE": str(trace)}, clear=False
            ):
                out_scorecard = io.StringIO()
                with redirect_stdout(out_scorecard):
                    rc_scorecard = swarmctl.cmd_scorecard(SimpleNamespace(profile="wave1", strict=True, dimensions=False))
                self.assertEqual(rc_scorecard, 0)
                scorecard_payload = json.loads(out_scorecard.getvalue())
                self.assertEqual(scorecard_payload["overall"], "pass")

                out_rollout = io.StringIO()
                with redirect_stdout(out_rollout):
                    rc_rollout = swarmctl.cmd_rollout_gate(SimpleNamespace(profile="wave1"))
                self.assertEqual(rc_rollout, 0)
                rollout_payload = json.loads(out_rollout.getvalue())
                self.assertEqual(rollout_payload["gate"], "pass")

    def test_incident_report_includes_reflection_and_stop_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace = repo / "logs/agent_traces.jsonl"
            rows = [
                {"ts": "2026-03-11T00:01:00+00:00", "run_id": "run-a", "event_type": "stop_signal_received", "level": "warn", "component": "policy", "status": "warn", "data": {}},
                {"ts": "2026-03-11T00:01:01+00:00", "run_id": "run-b", "event_type": "stop_signal_received", "level": "warn", "component": "policy", "status": "warn", "data": {}},
                {"ts": "2026-03-11T00:01:02+00:00", "run_id": "run-a", "event_type": "stop_signal_honored", "level": "info", "component": "policy", "status": "completed", "data": {}},
                {
                    "ts": "2026-03-11T00:01:03+00:00",
                    "run_id": "run-c",
                    "event_type": "policy_violation_detected",
                    "level": "error",
                    "component": "eval",
                    "status": "error",
                    "data": {"reflection_validation": {"valid": False, "errors": ["missing required field: proposed_change"]}},
                },
            ]
            self._write_trace(trace, rows)

            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.dict(
                os.environ, {"AGENT_OS_TRACE_FILE": str(trace)}, clear=False
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = swarmctl.cmd_incident_report(SimpleNamespace())
                self.assertEqual(rc, 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(payload["self_reflection_rejections"], 1)
                self.assertEqual(payload["stop_not_honored_count"], 1)
                self.assertIn("run-b", payload["stop_not_honored_run_ids"])

    def test_harness_report_aggregates_context_trace_and_doc_drift(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            harness_map = repo / "docs" / "ki" / "AGENT_HARNESS_MAP.md"
            harness_map.parent.mkdir(parents=True, exist_ok=True)
            harness_map.write_text("# Agent Harness Map\n", encoding="utf-8")
            catalog = repo / "configs" / "orchestrator" / "catalog.json"
            catalog.parent.mkdir(parents=True, exist_ok=True)
            catalog.write_text(
                json.dumps(
                    {
                        "skills": [],
                        "rules": [],
                        "workflows": [],
                        "configs": [],
                        "docs": [
                            {
                                "name": "AGENT_HARNESS_MAP",
                                "title": "Agent Harness Map",
                                "path": "docs/ki/AGENT_HARNESS_MAP.md",
                                "status": "canonical",
                                "description": "routing validation observability harness",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            trace = repo / "logs" / "agent_traces.jsonl"
            self._write_trace(
                trace,
                [
                    {
                        "ts": "2026-04-08T00:00:00+00:00",
                        "run_id": "run-harness",
                        "event_type": "harness_evidence_collected",
                        "level": "info",
                        "component": "harness",
                        "status": "ok",
                        "data": {},
                    }
                ],
            )

            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.dict(
                os.environ, {"AGENT_OS_TRACE_FILE": str(trace)}, clear=False
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = swarmctl.cmd_harness_report(SimpleNamespace(task="harness validation observability"))
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertTrue(payload["harness_map"]["exists"])
            self.assertEqual(payload["context_pack"]["doc_refs"][0]["name"], "AGENT_HARNESS_MAP")
            self.assertEqual(payload["trace"]["event_counts"]["harness_evidence_collected"], 1)
            self.assertEqual(payload["doc_drift"]["missing_paths_count"], 0)

    def test_harness_report_reads_nested_benchmark_latest_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            harness_map = repo / "docs" / "ki" / "AGENT_HARNESS_MAP.md"
            harness_map.parent.mkdir(parents=True, exist_ok=True)
            harness_map.write_text("# Agent Harness Map\n", encoding="utf-8")
            catalog = repo / "configs" / "orchestrator" / "catalog.json"
            catalog.parent.mkdir(parents=True, exist_ok=True)
            catalog.write_text(
                json.dumps(
                    {
                        "skills": [],
                        "rules": [],
                        "workflows": [],
                        "configs": [],
                        "docs": [
                            {
                                "name": "AGENT_HARNESS_MAP",
                                "title": "Agent Harness Map",
                                "path": "docs/ki/AGENT_HARNESS_MAP.md",
                                "status": "canonical",
                                "description": "routing validation observability harness",
                            }
                        ],
                        "validation": {"missing_paths": [], "stale_docs": []},
                    }
                ),
                encoding="utf-8",
            )
            benchmark_latest = repo / "docs" / "ki" / "benchmark_latest.json"
            benchmark_latest.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-08T00:00:00+00:00",
                        "run": {"suite_name": "benchmark_suite"},
                        "metrics": {
                            "pass_rate": 0.875,
                            "report_confidence": 1.0,
                            "score": 0.82,
                        },
                        "gate": {"status": "pass"},
                    }
                ),
                encoding="utf-8",
            )
            trace = repo / "logs" / "agent_traces.jsonl"
            self._write_trace(
                trace,
                [
                    {
                        "ts": "2026-04-08T00:00:00+00:00",
                        "run_id": "run-harness",
                        "event_type": "harness_evidence_collected",
                        "level": "info",
                        "component": "harness",
                        "status": "ok",
                        "data": {},
                    }
                ],
            )

            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.dict(
                os.environ, {"AGENT_OS_TRACE_FILE": str(trace)}, clear=False
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = swarmctl.cmd_harness_report(SimpleNamespace(task="harness validation observability"))
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["benchmark_latest"]["status"], "ok")
            self.assertEqual(payload["benchmark_latest"]["suite_name"], "benchmark_suite")
            self.assertEqual(payload["benchmark_latest"]["pass_rate"], 0.875)
            self.assertEqual(payload["benchmark_latest"]["report_confidence"], 1.0)
            self.assertEqual(payload["benchmark_latest"]["score"], 0.82)

    def test_harness_gardening_report_emits_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            catalog = repo / "configs" / "orchestrator" / "catalog.json"
            catalog.parent.mkdir(parents=True, exist_ok=True)
            catalog.write_text(
                json.dumps(
                    {
                        "skills": [],
                        "rules": [],
                        "workflows": [],
                        "configs": [],
                        "docs": [
                            {
                                "name": "BROKEN_DOC",
                                "title": "Broken Doc",
                                "path": "docs/ki/MISSING.md",
                                "status": "stale",
                                "description": "missing doc",
                            }
                        ],
                        "validation": {
                            "missing_paths": [{"category": "docs", "path": "docs/ki/MISSING.md"}],
                            "stale_docs": [{"name": "BROKEN_DOC", "path": "docs/ki/MISSING.md"}],
                        },
                    }
                ),
                encoding="utf-8",
            )
            trace = repo / "logs" / "agent_traces.jsonl"
            self._write_trace(
                trace,
                [
                    {
                        "ts": "2026-04-08T00:00:00+00:00",
                        "run_id": "run-harness",
                        "event_type": "harness_validation_started",
                        "level": "info",
                        "component": "harness",
                        "status": "ok",
                        "data": {},
                    }
                ],
            )
            benchmark_latest = repo / "docs" / "ki" / "benchmark_latest.json"
            benchmark_latest.parent.mkdir(parents=True, exist_ok=True)
            benchmark_latest.write_text(json.dumps({"status": "ok", "pass_rate": 0.5}), encoding="utf-8")

            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.dict(
                os.environ, {"AGENT_OS_TRACE_FILE": str(trace)}, clear=False
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = swarmctl.cmd_harness_gardening_report(SimpleNamespace(task="harness validation observability"))
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["status"], "warn")
            candidate_ids = {row["id"] for row in payload["candidates"]}
            self.assertIn("missing-harness-map", candidate_ids)
            self.assertIn("catalog-doc-drift", candidate_ids)
            self.assertIn("missing-doc-refs", candidate_ids)
            self.assertIn("missing-harness-evidence", candidate_ids)
            self.assertIn("low-benchmark-pass-rate", candidate_ids)

    def test_harness_gardening_report_ok_when_signals_are_clean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            harness_map = repo / "docs" / "ki" / "AGENT_HARNESS_MAP.md"
            harness_map.parent.mkdir(parents=True, exist_ok=True)
            harness_map.write_text("# Agent Harness Map\n", encoding="utf-8")
            benchmark_latest = repo / "docs" / "ki" / "benchmark_latest.json"
            benchmark_latest.write_text(json.dumps({"status": "ok", "pass_rate": 1.0}), encoding="utf-8")
            jobs = repo / "configs" / "tooling" / "background_jobs.yaml"
            jobs.parent.mkdir(parents=True, exist_ok=True)
            jobs.write_text(
                "jobs:\n"
                "  harness_gardening:\n"
                "    mode: diagnostic_only\n"
                "    escalation_rule: queue_review\n",
                encoding="utf-8",
            )
            catalog = repo / "configs" / "orchestrator" / "catalog.json"
            catalog.parent.mkdir(parents=True, exist_ok=True)
            catalog.write_text(
                json.dumps(
                    {
                        "skills": [],
                        "rules": [],
                        "workflows": [],
                        "configs": [],
                        "docs": [
                            {
                                "name": "AGENT_HARNESS_MAP",
                                "title": "Agent Harness Map",
                                "path": "docs/ki/AGENT_HARNESS_MAP.md",
                                "status": "canonical",
                                "description": "routing validation observability harness",
                            }
                        ],
                        "validation": {"missing_paths": [], "stale_docs": []},
                    }
                ),
                encoding="utf-8",
            )
            trace = repo / "logs" / "agent_traces.jsonl"
            self._write_trace(
                trace,
                [
                    {
                        "ts": "2026-04-08T00:00:00+00:00",
                        "run_id": "run-harness",
                        "event_type": "harness_validation_started",
                        "level": "info",
                        "component": "harness",
                        "status": "ok",
                        "data": {},
                    },
                    {
                        "ts": "2026-04-08T00:00:01+00:00",
                        "run_id": "run-harness",
                        "event_type": "harness_evidence_collected",
                        "level": "info",
                        "component": "harness",
                        "status": "ok",
                        "data": {},
                    },
                    {
                        "ts": "2026-04-08T00:00:02+00:00",
                        "run_id": "run-harness",
                        "event_type": "harness_validation_completed",
                        "level": "info",
                        "component": "harness",
                        "status": "completed",
                        "data": {},
                    },
                ],
            )

            with patch.object(swarmctl, "_repo_root", return_value=repo), patch.dict(
                os.environ, {"AGENT_OS_TRACE_FILE": str(trace)}, clear=False
            ):
                out = io.StringIO()
                with redirect_stdout(out):
                    rc = swarmctl.cmd_harness_gardening_report(SimpleNamespace(task="harness validation observability"))
            self.assertEqual(rc, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["candidate_count"], 0)
            self.assertEqual(payload["candidates"], [])


if __name__ == "__main__":
    unittest.main()
