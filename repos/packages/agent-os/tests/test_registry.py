from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.registry import AssetRegistry


class TestAssetRegistryWikiCore(unittest.TestCase):
    def test_context_pack_includes_wiki_core_results_when_config_exists(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            catalog_path = repo / "configs/orchestrator/catalog.json"
            catalog_path.parent.mkdir(parents=True)
            catalog_path.write_text(json.dumps({"skills": [], "rules": [], "workflows": [], "configs": [], "docs": []}), encoding="utf-8")
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
  local_skill_target: ".agent/skills"
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
            page.write_text("# Wiki Retrieval\n\nqmd fallback retrieval context", encoding="utf-8")

            pack = AssetRegistry(catalog_path).generate_context_pack("fallback retrieval")

            self.assertEqual(pack["wiki_core"]["backend"], "tfidf")
            self.assertEqual(pack["wiki_core"]["results"][0]["title"], "Wiki Retrieval")


if __name__ == "__main__":
    unittest.main()
