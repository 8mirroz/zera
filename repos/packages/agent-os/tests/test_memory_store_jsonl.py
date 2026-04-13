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

from agent_os.contracts import MemoryStoreInput
from agent_os.memory_store import MemoryStore


class TestMemoryStoreJsonl(unittest.TestCase):
    def test_dedupes_identical_write_and_searches_ranked_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            trace_file = repo / "logs/agent_traces.jsonl"
            os.environ["AGENT_OS_TRACE_FILE"] = str(trace_file)
            try:
                store = MemoryStore(repo)
                first = store.operate(
                    MemoryStoreInput(
                        op="write",
                        key="user:pref",
                        payload={"value": "likes precise planning"},
                        options={
                            "memory_class": "stable_preference",
                            "confidence": 0.9,
                            "source_confidence": 0.95,
                            "promotion_state": "approved_long_term",
                            "user_scope": "zera-user",
                            "evidence_refs": ["trace:run-search"],
                        },
                    )
                )
                second = store.operate(
                    MemoryStoreInput(
                        op="write",
                        key="user:pref",
                        payload={"value": "likes precise planning"},
                        options={
                            "memory_class": "stable_preference",
                            "confidence": 0.9,
                            "source_confidence": 0.95,
                            "promotion_state": "approved_long_term",
                            "user_scope": "zera-user",
                            "evidence_refs": ["trace:run-search"],
                        },
                    )
                )
                search = store.operate(
                    MemoryStoreInput(
                        op="search",
                        key="precise planning",
                        payload={},
                        correlation_id="run-search",
                    )
                )
            finally:
                os.environ.pop("AGENT_OS_TRACE_FILE", None)

            self.assertEqual(first.memory_ids, second.memory_ids)
            items = search.result.get("items", [])
            self.assertGreaterEqual(len(items), 1)
            self.assertEqual(items[0]["key"], "user:pref")
            self.assertEqual(first.result["promotion_state"], "approved_long_term")
            self.assertEqual(first.result["user_scope"], "zera-user")
            rows = [json.loads(line) for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(rows[-1]["event_type"], "memory_retrieval_scored")


if __name__ == "__main__":
    unittest.main()
