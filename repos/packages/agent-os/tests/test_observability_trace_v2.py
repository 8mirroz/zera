from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.observability import emit_event


class TestObservabilityTraceV2(unittest.TestCase):
    def test_emit_event_writes_v2_envelope_and_keeps_extra_payload_in_data(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "trace.jsonl"
            prev = os.environ.get("AGENT_OS_TRACE_FILE")
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                emit_event(
                    "route_decision",
                    {
                        "component": "router",
                        "run_id": "run-123",
                        "task_type": "T3",
                        "complexity": "C3",
                        "model_tier": "quality",
                        "model": "demo-model",
                        "message": "route selected",
                        "route_reason": "quality lane",
                    },
                )
            finally:
                if prev is None:
                    os.environ.pop("AGENT_OS_TRACE_FILE", None)
                else:
                    os.environ["AGENT_OS_TRACE_FILE"] = prev

            rows = [json.loads(x) for x in trace_file.read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["event_type"], "route_decision")
            self.assertEqual(row["run_id"], "run-123")
            self.assertEqual(row["component"], "router")
            self.assertEqual(row["task_type"], "T3")
            self.assertEqual(row["complexity"], "C3")
            self.assertEqual(row["model_tier"], "quality")
            self.assertEqual(row["model"], "demo-model")
            self.assertEqual(row["message"], "route selected")
            self.assertIsInstance(row["ts"], str)
            self.assertIsInstance(row["data"], dict)
            self.assertEqual(row["data"]["route_reason"], "quality lane")

    def test_emit_event_generates_run_id_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "trace.jsonl"
            prev = os.environ.get("AGENT_OS_TRACE_FILE")
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                emit_event("retro_written", {"status": "ok"})
            finally:
                if prev is None:
                    os.environ.pop("AGENT_OS_TRACE_FILE", None)
                else:
                    os.environ["AGENT_OS_TRACE_FILE"] = prev
            row = json.loads(trace_file.read_text(encoding="utf-8").strip())
            self.assertTrue(row.get("run_id"))
            self.assertEqual(row.get("event_type"), "retro_written")
            self.assertEqual(row.get("component"), "retro")
            self.assertEqual(row.get("status"), "ok")

    def test_algorithm_eval_metadata_stays_inside_v2_data(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trace_file = Path(td) / "trace.jsonl"
            prev = os.environ.get("AGENT_OS_TRACE_FILE")
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                emit_event(
                    "eval_run_completed",
                    {
                        "run_id": "eval-123",
                        "component": "eval",
                        "status": "ok",
                        "message": "benchmark suite completed",
                        "data": {
                            "algorithm_variant": "spec_to_contract_gate",
                            "promotion_gate": {"disqualified": False},
                        },
                    },
                )
            finally:
                if prev is None:
                    os.environ.pop("AGENT_OS_TRACE_FILE", None)
                else:
                    os.environ["AGENT_OS_TRACE_FILE"] = prev

            row = json.loads(trace_file.read_text(encoding="utf-8").strip())
            self.assertEqual(row["event_type"], "eval_run_completed")
            self.assertNotIn("algorithm_variant", row)
            self.assertEqual(row["data"]["algorithm_variant"], "spec_to_contract_gate")
            self.assertFalse(row["data"]["promotion_gate"]["disqualified"])


if __name__ == "__main__":
    unittest.main()
