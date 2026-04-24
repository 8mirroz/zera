from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
import sys
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.wiki_core import WikiCore


class TestWikiCore(unittest.TestCase):
    def _repo(self) -> tempfile.TemporaryDirectory[str]:
        td = tempfile.TemporaryDirectory()
        repo = Path(td.name)
        (repo / "configs/tooling").mkdir(parents=True)
        (repo / "repos/data/knowledge/wiki-core/raw/inbox").mkdir(parents=True)
        (repo / "repos/data/knowledge/wiki-core/wiki/_briefs").mkdir(parents=True)
        (repo / "repos/data/knowledge/wiki-core/manifests").mkdir(parents=True)
        (repo / "configs/tooling/wiki_core.yaml").write_text(
            """
version: "1.0"
enabled: true
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
    command: "qmd"
    collection: "antigravity-wiki-core"
writeback:
  default_target: "wiki/_briefs"
  allowed_page_types: [brief, entity, concept, project, comparison, decision, log]
""".strip()
            + "\n",
            encoding="utf-8",
        )
        return td

    def test_load_config_and_resolve_paths(self) -> None:
        with self._repo() as td:
            core = WikiCore(Path(td))
            self.assertEqual(core.config["paths"]["root"], "repos/data/knowledge/wiki-core")
            self.assertTrue(core.paths.wiki.is_absolute())
            self.assertTrue(str(core.paths.raw).endswith("repos/data/knowledge/wiki-core/raw"))

    def test_ingest_dry_run_does_not_write_manifest(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            src = repo / "repos/data/knowledge/wiki-core/raw/inbox/source.md"
            src.write_text("# Source\n\nImportant wiki fact.", encoding="utf-8")
            core = WikiCore(repo)

            result = core.ingest_source(src, dry_run=True)

            self.assertEqual(result["status"], "dry_run")
            self.assertFalse((repo / "repos/data/knowledge/wiki-core/manifests/sources.csv").exists())
            self.assertFalse(Path(result["wiki_path"]).exists())

    def test_ingest_updates_manifest_and_detects_duplicate(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            src = repo / "repos/data/knowledge/wiki-core/raw/inbox/source.md"
            src.write_text("# Source\n\nImportant wiki fact.", encoding="utf-8")
            core = WikiCore(repo)

            first = core.ingest_source(src)
            second = core.ingest_source(src)

            self.assertEqual(first["status"], "ok")
            self.assertEqual(second["status"], "duplicate")
            self.assertTrue((repo / "repos/data/knowledge/wiki-core/manifests/sources.csv").exists())
            self.assertTrue(Path(first["wiki_path"]).exists())

    def test_writeback_blocks_raw_targets(self) -> None:
        with self._repo() as td:
            core = WikiCore(Path(td))
            with self.assertRaises(ValueError):
                core.writeback_answer("bad", "body", page_type="brief", target="raw/inbox/bad.md")

    def test_writeback_writes_frontmatter(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            core = WikiCore(repo)

            result = core.writeback_answer("Decision Note", "Use wiki-core.", page_type="decision", tags=["wiki-core"])

            path = Path(result["path"])
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("page_type: decision", text)
            self.assertIn("source: wiki-core-writeback", text)
            self.assertIn("Use wiki-core.", text)

    def test_query_falls_back_to_local_search_when_qmd_missing(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            page = repo / "repos/data/knowledge/wiki-core/wiki/_briefs/qmd-fallback.md"
            page.write_text("# QMD fallback\n\nLocal semantic fallback search target.", encoding="utf-8")
            core = WikiCore(repo, qmd_which=lambda _cmd: None)

            result = core.query("semantic fallback", limit=3)

            self.assertEqual(result["backend"], "tfidf")
            self.assertEqual(result["results"][0]["title"], "QMD fallback")


if __name__ == "__main__":
    unittest.main()
