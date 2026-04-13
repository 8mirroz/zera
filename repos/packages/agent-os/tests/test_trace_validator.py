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

import trace_validator


class TestTraceValidator(unittest.TestCase):
    def test_validates_v2_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "trace.jsonl"
            trace_file.write_text(
                json.dumps(
                    {
                        "ts": "2026-02-23T23:00:00+00:00",
                        "run_id": "run-1",
                        "event_type": "triage_decision",
                        "level": "info",
                        "component": "triage",
                        "task_type": "T3",
                        "complexity": "C3",
                        "model_tier": "quality",
                        "data": {},
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            out = trace_validator.validate_trace_file(
                trace_file,
                schema_path=ROOT / "configs/tooling/trace_schema.json",
                allow_legacy=False,
            )
            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["v2_valid_count"], 1)
            self.assertEqual(out["errors_count"], 0)

    def test_accepts_legacy_rows_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "trace.jsonl"
            trace_file.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "entry": {
                            "timestamp": "2026-02-23T23:00:00Z",
                            "run_id": "legacy-1",
                            "task_type": "T3",
                            "complexity": "C3",
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            out = trace_validator.validate_trace_file(
                trace_file,
                schema_path=ROOT / "configs/tooling/trace_schema.json",
                allow_legacy=True,
            )
            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["legacy_valid_count"], 1)
            self.assertEqual(out["errors_count"], 0)

    def test_accepts_harness_events(self) -> None:
        schema = json.loads((ROOT / "configs/tooling/trace_schema.json").read_text(encoding="utf-8"))
        for event_type in [
            "harness_validation_started",
            "harness_validation_completed",
            "harness_evidence_collected",
            "doc_gardening_issue_found",
        ]:
            self.assertIn(event_type, schema["event_types"])

        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "trace.jsonl"
            rows = [
                {
                    "ts": "2026-04-08T00:00:00+00:00",
                    "run_id": "run-harness",
                    "event_type": "harness_validation_started",
                    "level": "info",
                    "component": "eval",
                    "status": "ok",
                    "data": {"gate": "C4"},
                },
                {
                    "ts": "2026-04-08T00:00:01+00:00",
                    "run_id": "run-harness",
                    "event_type": "harness_evidence_collected",
                    "level": "info",
                    "component": "eval",
                    "status": "ok",
                    "data": {"evidence_type": "worktree_validation"},
                },
                {
                    "ts": "2026-04-08T00:00:02+00:00",
                    "run_id": "run-harness",
                    "event_type": "doc_gardening_issue_found",
                    "level": "warn",
                    "component": "eval",
                    "status": "warn",
                    "data": {"path": "docs/ki/STALE.md"},
                },
            ]
            trace_file.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

            out = trace_validator.validate_trace_file(
                trace_file,
                schema_path=ROOT / "configs/tooling/trace_schema.json",
                allow_legacy=False,
            )

            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["v2_valid_count"], 3)
            self.assertEqual(out["errors_count"], 0)


if __name__ == "__main__":
    unittest.main()
