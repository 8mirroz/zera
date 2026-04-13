from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claw_code_baseline_report


class TestClawCodeBaselineReport(unittest.TestCase):
    def _write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_build_baseline_report_counts_fallback_and_recovery(self) -> None:
        rows = [
            {"event_type": "runtime_provider_selected", "runtime_provider": "claw_code", "runtime_profile": "claw-t3-local", "run_id": "r1", "task_type": "T3"},
            {"event_type": "runtime_recovery_attempted", "runtime_provider": "claw_code", "run_id": "r1", "data": {"failure_type": "stdio_json_failure"}},
            {"event_type": "runtime_degraded_mode_entered", "runtime_provider": "claw_code", "run_id": "r1"},
            {"event_type": "runtime_provider_fallback", "runtime_provider": "claw_code", "run_id": "r1"},
            {"event_type": "agent_run_completed", "runtime_provider": "claw_code", "run_id": "r1", "duration_ms": 1200},
            {"event_type": "agent_run_completed", "runtime_provider": "claw_code", "run_id": "r1", "duration_ms": 800},
            {"event_type": "runtime_provider_selected", "runtime_provider": "agent_os_python"},
        ]
        matrix = {
            "profiles": {
                "claw-code-t3-implement-local": {
                    "runtime_provider": "claw_code",
                    "runtime_profile": "claw-t3-local",
                    "task_types": ["T3"],
                    "max_chain_length": 3,
                    "max_cost_usd_per_run": 0.03,
                }
            }
        }
        report = claw_code_baseline_report.build_baseline_report(rows, matrix)

        self.assertEqual(report["summary"]["claw_code_selected_runs"], 1)
        self.assertEqual(report["summary"]["claw_code_fallback_runs"], 1)
        self.assertEqual(report["summary"]["fallback_rate"], 1.0)
        self.assertEqual(report["summary"]["degraded_mode_entries"], 1)
        self.assertEqual(report["summary"]["avg_duration_ms"], 1000.0)
        self.assertEqual(report["recovery_by_failure_type"]["stdio_json_failure"], 1)
        self.assertEqual(report["runtime_profile_usage"]["claw-t3-local"], 1)
        self.assertEqual(report["recommended_profiles"][0]["profile_id"], "claw-code-t3-implement-local")
        self.assertIn("task_type_observations", report)
        self.assertIn("experimental_candidates", report)
        self.assertEqual(report["task_type_observations"]["T3"]["selected_runs"], 1)
        self.assertEqual(report["experimental_candidates"][1]["task_type"], "T3")

    def test_main_writes_report_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace_file = root / "logs" / "agent_traces.jsonl"
            matrix_file = root / "runtime_benchmark_matrix.json"
            out_file = root / "report.json"
            self._write_jsonl(
                trace_file,
                [
                    {"event_type": "runtime_provider_selected", "runtime_provider": "claw_code"},
                ],
            )
            self._write_json(matrix_file, {"profiles": {}})

            old_argv = sys.argv
            try:
                sys.argv = [
                    "claw_code_baseline_report.py",
                    "--trace-file",
                    str(trace_file),
                    "--matrix",
                    str(matrix_file),
                    "--out",
                    str(out_file),
                ]
                rc = claw_code_baseline_report.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 0)
            payload = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertIn("summary", payload)


if __name__ == "__main__":
    unittest.main()
