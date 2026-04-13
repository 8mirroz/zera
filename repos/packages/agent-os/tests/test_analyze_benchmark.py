from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TOOLING = ROOT / "configs" / "tooling"
if str(TOOLING) not in os.sys.path:
    os.sys.path.insert(0, str(TOOLING))

import analyze_benchmark as ab


class TestAnalyzeBenchmark(unittest.TestCase):
    def test_load_suite_manifest_accepts_benchmark_suite_schema(self) -> None:
        manifest_path = ROOT / "configs" / "tooling" / "benchmark_suite.json"
        manifest = ab.load_suite_manifest(manifest_path)

        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["suite_name"], "benchmark_suite")
        self.assertIn("bench-c1-config", manifest["expected_case_ids"])
        self.assertIn("bench-approval-gate", manifest["expected_case_ids"])

    def test_reconstruct_run_links_case_run_summary_and_reports_duplicates(self) -> None:
        events = [
            {
                "ts": "2026-03-11T10:00:00+00:00",
                "run_id": "bench-1",
                "event_type": "benchmark_run_completed",
                "status": "error",
                "data": {
                    "case_id": "case_001",
                    "case_run_id": "case-run-1",
                    "duration": 12.0,
                    "token_total": 300,
                    "error": "Timeout while waiting on tool",
                },
            },
            {
                "ts": "2026-03-11T10:00:01+00:00",
                "run_id": "bench-1",
                "event_type": "benchmark_run_completed",
                "status": "error",
                "data": {
                    "case_id": "case_001",
                    "case_run_id": "case-run-1",
                    "duration": 12.5,
                    "token_total": 300,
                },
            },
            {
                "ts": "2026-03-11T10:00:02+00:00",
                "run_id": "case-run-1",
                "event_type": "task_run_summary",
                "status": "completed",
                "data": {
                    "attempts": 2,
                    "escalation_reason": "tool timeout",
                    "token_usage": {"input_tokens": 120, "output_tokens": 180},
                },
            },
        ]

        run = ab.reconstruct_run(
            run_id="bench-1",
            run_events=[events[0], events[1]],
            all_events=events,
            total_lines=3,
            malformed=0,
        )
        metrics = ab.compute_metrics(run, ab.default_config(ROOT), ["case_001", "case_002"])
        suite_diag = ab.suite_diagnostics(run, ["case_001", "case_002"])

        self.assertEqual(len(run.cases), 1)
        case = run.cases[0]
        self.assertEqual(case.attempts, 2)
        self.assertTrue(case.escalated)
        self.assertEqual(case.input_tokens, 120)
        self.assertEqual(case.output_tokens, 180)
        self.assertEqual(case.total_tokens, 300)
        self.assertEqual(case.failure_mode, "timeout")
        self.assertEqual(metrics["coverage"], 0.5)
        self.assertEqual(suite_diag["duplicate_cases"], ["case_001"])
        self.assertEqual(suite_diag["missing_cases"], ["case_002"])

    def test_evaluate_gate_fails_on_unexpected_and_real_trace_cases(self) -> None:
        metrics = {
            "score": 0.95,
            "pass_rate": 1.0,
            "p95_duration": 0.1,
            "report_confidence": 1.0,
            "coverage": 1.0,
        }
        thresholds = {
            "score_min": 0.7,
            "pass_rate_min": 0.8,
            "p95_duration_max": 40.0,
            "report_confidence_min": 0.75,
        }
        suite_diag = {
            "missing_cases": [],
            "unexpected_cases": ["real-trace-abc"],
            "duplicate_cases": [],
            "real_trace_cases": ["real-trace-abc"],
        }
        gate = ab.evaluate_gate(metrics, thresholds, suite_diag)
        self.assertEqual(gate["status"], "fail")
        self.assertIn("unexpected_cases", gate["failed_metrics"])
        self.assertIn("real_trace_case_mix", gate["failed_metrics"])

    def test_canonical_repeat_ids_do_not_inflate_coverage(self) -> None:
        events = [
            {
                "ts": "2026-03-11T10:00:00+00:00",
                "run_id": "bench-repeat",
                "event_type": "benchmark_run_completed",
                "status": "ok",
                "data": {"case_id": "case_001::r1"},
            },
            {
                "ts": "2026-03-11T10:00:01+00:00",
                "run_id": "bench-repeat",
                "event_type": "benchmark_run_completed",
                "status": "ok",
                "data": {"case_id": "case_001::r2"},
            },
        ]
        run = ab.reconstruct_run(
            run_id="bench-repeat",
            run_events=events,
            all_events=events,
            total_lines=2,
            malformed=0,
        )
        metrics = ab.compute_metrics(run, ab.default_config(ROOT), ["case_001", "case_002"])
        suite_diag = ab.suite_diagnostics(run, ["case_001", "case_002"])
        self.assertEqual(metrics["coverage"], 0.5)
        self.assertEqual(metrics["total_cases"], 1)
        self.assertEqual(suite_diag["duplicate_cases"], ["case_001"])

    def test_main_writes_latest_json_markdown_and_anomalies(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace_file = root / "logs" / "agent_traces.jsonl"
            docs_dir = root / "docs" / "ki"
            config_path = root / "configs" / "tooling" / "benchmark_config.json"
            manifest_path = root / "configs" / "tooling" / "suite_manifest.json"
            trace_file.parent.mkdir(parents=True, exist_ok=True)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            rows = [
                {
                    "ts": "2026-03-11T11:00:00+00:00",
                    "run_id": "bench-2",
                    "event_type": "benchmark_run_completed",
                    "status": "ok",
                    "data": {
                        "case_id": "case_001",
                        "case_run_id": "case-run-2",
                        "duration": 5.0,
                        "token_total": 90,
                    },
                },
                {
                    "ts": "2026-03-11T11:00:01+00:00",
                    "run_id": "case-run-2",
                    "event_type": "task_run_summary",
                    "status": "completed",
                    "data": {
                        "token_usage": {"input_tokens": 40, "output_tokens": 50},
                    },
                },
            ]
            trace_file.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "trace_file": "logs/agent_traces.jsonl",
                        "docs_dir": "docs/ki",
                        "reports_subdir": "benchmark_reports",
                        "history_file": "benchmark_history.json",
                        "latest_md_file": "benchmark_latest.md",
                        "latest_json_file": "benchmark_latest.json",
                        "anomalies_file": "benchmark_anomalies.json",
                        "expected_cases_default": 1,
                        "latency_bad_threshold_sec": 30.0,
                        "latency_warn_threshold_sec": 20.0,
                        "token_ideal_total": 5000,
                        "token_bad_total": 25000,
                        "gate_file": "benchmark_gate.json",
                        "gate_thresholds": {
                            "score_min": 0.70,
                            "pass_rate_min": 0.80,
                            "p95_duration_max": 40.0,
                            "report_confidence_min": 0.75,
                        },
                        "weights": {
                            "pass_rate": 0.30,
                            "first_pass_success": 0.20,
                            "non_escalation": 0.20,
                            "latency_efficiency": 0.15,
                            "token_efficiency": 0.15,
                        },
                    }
                ),
                encoding="utf-8",
            )
            manifest_path.write_text(
                json.dumps({"suite_name": "temp_suite", "expected_case_ids": ["case_001"]}),
                encoding="utf-8",
            )

            rc = ab.main([
                "--config",
                str(config_path),
                "--suite-manifest",
                str(manifest_path),
                "--repo-root",
                str(root),
            ])

            self.assertEqual(rc, 0)
            latest_json = json.loads((docs_dir / "benchmark_latest.json").read_text(encoding="utf-8"))
            anomalies = json.loads((docs_dir / "benchmark_anomalies.json").read_text(encoding="utf-8"))
            latest_md = (docs_dir / "benchmark_latest.md").read_text(encoding="utf-8")
            history = json.loads((docs_dir / "benchmark_history.json").read_text(encoding="utf-8"))

            self.assertEqual(latest_json["status"], "ok")
            self.assertEqual(latest_json["suite_name"], "temp_suite")
            self.assertEqual(latest_json["pass_rate"], 1.0)
            self.assertEqual(latest_json["report_confidence"], 1.0)
            self.assertIn("score", latest_json)
            self.assertEqual(latest_json["metrics"]["pass_rate"], 1.0)
            self.assertEqual(latest_json["cases"][0]["total_tokens"], 90)
            self.assertEqual(anomalies, [])
            self.assertIn("Report Confidence", latest_md)
            self.assertEqual(len(history), 1)
            gate = json.loads((docs_dir / "benchmark_gate.json").read_text(encoding="utf-8"))
            self.assertEqual(gate["status"], "pass")

    def test_strict_gate_returns_non_zero_when_threshold_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace_file = root / "logs" / "agent_traces.jsonl"
            docs_dir = root / "docs" / "ki"
            config_path = root / "configs" / "tooling" / "benchmark_config.json"
            manifest_path = root / "configs" / "tooling" / "suite_manifest.json"
            trace_file.parent.mkdir(parents=True, exist_ok=True)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            rows = [
                {
                    "ts": "2026-03-11T11:00:00+00:00",
                    "run_id": "bench-3",
                    "event_type": "benchmark_run_completed",
                    "status": "ok",
                    "data": {
                        "case_id": "case_001",
                        "case_run_id": "case-run-3",
                        "duration": 2.0,
                        "token_total": 60,
                    },
                },
                {
                    "ts": "2026-03-11T11:00:01+00:00",
                    "run_id": "case-run-3",
                    "event_type": "task_run_summary",
                    "status": "completed",
                    "data": {
                        "token_usage": {"input_tokens": 30, "output_tokens": 30},
                    },
                },
            ]
            trace_file.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "trace_file": "logs/agent_traces.jsonl",
                        "docs_dir": "docs/ki",
                        "reports_subdir": "benchmark_reports",
                        "history_file": "benchmark_history.json",
                        "latest_md_file": "benchmark_latest.md",
                        "latest_json_file": "benchmark_latest.json",
                        "anomalies_file": "benchmark_anomalies.json",
                        "gate_file": "benchmark_gate.json",
                        "expected_cases_default": 1,
                        "latency_bad_threshold_sec": 30.0,
                        "latency_warn_threshold_sec": 20.0,
                        "token_ideal_total": 5000,
                        "token_bad_total": 25000,
                        "weights": {
                            "pass_rate": 0.30,
                            "first_pass_success": 0.20,
                            "non_escalation": 0.20,
                            "latency_efficiency": 0.15,
                            "token_efficiency": 0.15,
                        },
                    }
                ),
                encoding="utf-8",
            )
            manifest_path.write_text(
                json.dumps({"suite_name": "temp_suite", "expected_case_ids": ["case_001"]}),
                encoding="utf-8",
            )

            rc_ok = ab.main([
                "--config",
                str(config_path),
                "--suite-manifest",
                str(manifest_path),
                "--repo-root",
                str(root),
                "--strict",
            ])
            self.assertEqual(rc_ok, 0)

            rc_fail = ab.main([
                "--config",
                str(config_path),
                "--suite-manifest",
                str(manifest_path),
                "--repo-root",
                str(root),
                "--strict",
                "--min-report-confidence",
                "1.01",
            ])
            self.assertEqual(rc_fail, 2)
            gate = json.loads((docs_dir / "benchmark_gate.json").read_text(encoding="utf-8"))
            self.assertEqual(gate["status"], "fail")
            self.assertIn("report_confidence", gate["failed_metrics"])


if __name__ == "__main__":
    unittest.main()
