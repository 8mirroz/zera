from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in os.sys.path:
    os.sys.path.insert(0, str(SRC))

from agent_os.contracts import MemoryStoreInput, RetrieverInput
from agent_os.memory_store import MemoryStore
from agent_os.retriever import Retriever


class TestMemoryRetriever(unittest.TestCase):
    def test_memory_write_read_search(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            old = os.environ.get("MEMORY_FILE_PATH")
            os.environ["MEMORY_FILE_PATH"] = str(Path(td) / "memory.jsonl")
            try:
                mem = MemoryStore(ROOT)
                write_out = mem.operate(MemoryStoreInput(op="write", key="unit:test", payload={"hello": "world"}))
                self.assertEqual(len(write_out.memory_ids), 1)

                read_out = mem.operate(MemoryStoreInput(op="read", key="unit:test", payload={}))
                self.assertGreaterEqual(len(read_out.result.get("items", [])), 1)

                search_out = mem.operate(MemoryStoreInput(op="search", key="world", payload={}))
                self.assertGreaterEqual(len(search_out.result.get("items", [])), 1)
            finally:
                if old is None:
                    os.environ.pop("MEMORY_FILE_PATH", None)
                else:
                    os.environ["MEMORY_FILE_PATH"] = old

    def test_retriever_returns_chunks(self) -> None:
        retriever = Retriever(ROOT)
        out = retriever.query(RetrieverInput(query="Agent OS", sources=["docs"], max_chunks=2, freshness="workspace"))
        self.assertLessEqual(len(out.chunks), 2)
        self.assertGreaterEqual(out.retrieval_ms, 0)

    def test_retriever_can_use_wiki_core_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "configs/tooling").mkdir(parents=True)
            (repo / "configs/tooling/wiki_core.yaml").write_text(
                """
version: "1.0"
paths:
  root: "repos/data/knowledge/wiki-core"
  raw: "repos/data/knowledge/wiki-core/raw"
  wiki: "repos/data/knowledge/wiki-core/wiki"
  manifests: "repos/data/knowledge/wiki-core/manifests"
  skills: "repos/data/knowledge/wiki-core/.skills"
  local_skill_target: ".agents/skills"
search:
  primary_backend: "qmd"
  fallback_backend: "tfidf"
  qmd:
    command: "definitely-not-qmd"
writeback:
  default_target: "wiki/_briefs"
  allowed_page_types: [brief]
""".strip()
                + "\n",
                encoding="utf-8",
            )
            page = repo / "repos/data/knowledge/wiki-core/wiki/_briefs/retrieval.md"
            page.parent.mkdir(parents=True)
            page.write_text("# Retrieval Note\n\nwiki core retriever result", encoding="utf-8")

            retriever = Retriever(repo)
            out = retriever.query(RetrieverInput(query="retriever result", sources=["wiki_core"], max_chunks=2, freshness="workspace"))

            self.assertEqual(len(out.chunks), 1)
            self.assertIn("retrieval.md", out.chunks[0]["source"])
            self.assertIn(":wiki", out.citations[0])


if __name__ == "__main__":
    unittest.main()
