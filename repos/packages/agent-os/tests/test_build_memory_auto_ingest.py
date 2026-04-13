from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = ROOT / "repos/packages/agent-os/scripts"
if str(SCRIPTS) not in os.sys.path:
    os.sys.path.insert(0, str(SCRIPTS))

import build_memory_auto_ingest as bmai
import build_memory_library as bml

class TestBuildMemoryAutoIngest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.td_path = Path(self.temp_dir.name)
        
        self.trace_file = self.td_path / "traces.jsonl"
        events = [
            {"ts": "2026-02-23T23:00:00+00:00", "run_id": "run-123", "event_type": "route_decision", "model": "gpt-4"},
            {"ts": "2026-02-23T23:00:01+00:00", "run_id": "run-123", "event_type": "task_run_summary", "status": "success", "task_type": "T3", "complexity": "C2", "data": {"duration_seconds": 45}},
            {"ts": "2026-02-23T23:00:02+00:00", "run_id": "run-456", "event_type": "route_decision"},
            {"ts": "2026-02-23T23:00:03+00:00", "run_id": "run-456", "event_type": "task_run_summary", "status": "fail"}
        ]
        self.trace_file.write_text("\n".join(json.dumps(ev) for ev in events) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_extract_valid_candidate(self) -> None:
        candidates = bmai.extract_candidates(self.trace_file, allow_legacy=False)
        self.assertEqual(len(candidates), 1)
        c = candidates[0]
        self.assertEqual(c["trace_refs"], ["run-123"])
        self.assertEqual(c["status"], "candidate")
        self.assertEqual(c["models"], ["gpt-4"])
        self.assertEqual(c["evidence"]["complexity"], "C2")

    def test_no_candidate_for_fail(self) -> None:
        candidates = bmai.extract_candidates(self.trace_file, allow_legacy=False, target_run_id="run-456")
        self.assertEqual(len(candidates), 0)

    def test_require_retro(self) -> None:
        trace_file = self.td_path / "traces2.jsonl"
        events = [
            {"run_id": "run-789", "event_type": "route_decision", "model": "gpt-4"},
            {"run_id": "run-789", "event_type": "task_run_summary", "status": "success", "task_type": "T3"},
            {"run_id": "run-789", "event_type": "retro_written"}
        ]
        trace_file.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        
        candidates = bmai.extract_candidates(trace_file, allow_legacy=False, require_retro=True)
        self.assertEqual(len(candidates), 1)

    def test_require_retro_fails_if_no_retro(self) -> None:
        candidates = bmai.extract_candidates(self.trace_file, allow_legacy=False, require_retro=True)
        self.assertEqual(len(candidates), 0)

    def test_cli_preview_accepts_file_flag_alias(self) -> None:
        args = [
            "preview",
            "--run-id", "run-123",
            "--file", str(self.trace_file),
        ]
        ret = bmai.main(args)
        self.assertEqual(ret, 0)

    def test_register_dedupes_by_fingerprint(self) -> None:
        # Prepare repo root + schema
        schema_dir = self.td_path / "configs/tooling"
        schema_dir.mkdir(parents=True)
        (schema_dir / "build_memory_entry_schema.json").write_text(json.dumps({
            "version": "1",
            "required_fields": ["entry_id", "scope", "kind", "status", "title", "summary", "scores", "provenance"]
        }))

        # Create an existing entry with matching fingerprint
        fp = bmai._fingerprint("run-123", "T3", "C2", "gpt-4")
        existing = {
            "entry_id": "existing-run-123",
            "scope": "global",
            "kind": "build",
            "title": "Existing auto-ingest",
            "summary": "Existing entry with same fingerprint",
            "status": "candidate",
            "scores": {"weighted_total": 0.5, "confidence": 0.5},
            "provenance": {"source": "auto_ingest", "fingerprint": fp},
        }
        lib_root = bml.build_lib_root(self.td_path)
        (lib_root / "global/entries").mkdir(parents=True, exist_ok=True)
        (lib_root / "global/entries/existing-run-123.json").write_text(json.dumps(existing), encoding="utf-8")

        args = [
            "register",
            "--run-id", "run-123",
            "--trace-file", str(self.trace_file),
            "--repo-root", str(self.td_path),
        ]
        ret = bmai.main(args)
        self.assertEqual(ret, 0)
        # Should not create a new auto-run-123 entry due to dedupe
        self.assertFalse((lib_root / "global/entries/auto-run-123.json").exists())

    @patch("build_memory_auto_ingest.repo_root")
    def test_cli_register_flow(self, mock_repo_root) -> None:
        mock_repo_root.return_value = self.td_path
        
        test_root = self.td_path
        # copy schema
        schema_dir = test_root / "configs/tooling"
        schema_dir.mkdir(parents=True)
        (schema_dir / "build_memory_entry_schema.json").write_text(json.dumps({
            "version": "1",
            "required_fields": ["entry_id", "scope", "kind", "status", "title", "summary", "scores", "provenance"]
        }))
        
        # Test full command
        args = [
            "register",
            "--run-id", "run-123",
            "--trace-file", str(self.trace_file),
            "--rebuild-index",
            "--sync-memory"
        ]
        
        ret = bmai.main(args)
        self.assertEqual(ret, 0)
        
        # check entry exists
        lib_root = bml.build_lib_root(test_root)
        files = list((lib_root / "global/entries").glob("auto-run-123.json"))
        self.assertEqual(len(files), 1)
        
        # check indexes where rebuilt
        self.assertTrue((lib_root / "indexes/global_index.json").exists())
        
        # check memory was synced
        mem_file = test_root / ".agent/memory/memory.jsonl"
        self.assertTrue(mem_file.exists())
        
        with mem_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertEqual(entry["payload"]["entry_id"], "auto-run-123")

if __name__ == "__main__":
    unittest.main()
