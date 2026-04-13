from __future__ import annotations

import io
import json
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


class TestSwarmctlWiki(unittest.TestCase):
    def _repo(self) -> tempfile.TemporaryDirectory[str]:
        td = tempfile.TemporaryDirectory()
        repo = Path(td.name)
        (repo / "configs/tooling").mkdir(parents=True)
        (repo / "configs/registry/workflows").mkdir(parents=True)
        (repo / "configs/registry/skills").mkdir(parents=True)
        (repo / "repos/data/knowledge/wiki-core/raw/inbox").mkdir(parents=True)
        (repo / "repos/data/knowledge/wiki-core/wiki/_briefs").mkdir(parents=True)
        (repo / "repos/data/knowledge/wiki-core/.skills/ingest-source").mkdir(parents=True)
        (repo / "repos/data/knowledge/wiki-core/.skills/ingest-source/SKILL.md").write_text(
            "---\nname: ingest-source\ndescription: test\n---\n# ingest-source\n",
            encoding="utf-8",
        )
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
    command: "qmd"
writeback:
  default_target: "wiki/_briefs"
  allowed_page_types: [brief, decision, log]
""".strip()
            + "\n",
            encoding="utf-8",
        )
        (repo / "configs/registry/workflows/path-swarm.yaml").write_text(
            """
id: swarm-path-to-completion
name: Swarm Path (C4-C5)
handoff_skill: dynamic-handoff
iteration_skill: ralph-loop-execute
knowledge_policy:
  pre_search: true
  writeback: true
stages:
  - id: plan
    agent: architecture-systems-architect
""".strip()
            + "\n",
            encoding="utf-8",
        )
        (repo / "configs/registry/skills/dynamic-handoff.yaml").write_text(
            """
id: dynamic-handoff
outputs: [handoff_contract]
contract_fields: [objective, evidence]
""".strip()
            + "\n",
            encoding="utf-8",
        )
        (repo / "configs/registry/skills/ralph-loop-execute.yaml").write_text(
            """
id: ralph-loop-execute
outputs: [best_solution, comparison_log]
comparison_mode: score_then_select
verification_required: true
""".strip()
            + "\n",
            encoding="utf-8",
        )
        return td

    def test_cmd_wiki_doctor_reports_fallback(self) -> None:
        with self._repo() as td, patch.object(swarmctl, "_repo_root", return_value=Path(td)):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = swarmctl.cmd_wiki_doctor(SimpleNamespace(config=None, json=True))
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["status"], "warn")
            self.assertEqual(payload["search"]["active_backend"], "tfidf")

    def test_cmd_wiki_ingest_dry_run(self) -> None:
        with self._repo() as td, patch.object(swarmctl, "_repo_root", return_value=Path(td)):
            repo = Path(td)
            src = repo / "repos/data/knowledge/wiki-core/raw/inbox/source.md"
            src.write_text("# Source\n\nBody", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = swarmctl.cmd_wiki_ingest(SimpleNamespace(source=str(src), config=None, dry_run=True))
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["status"], "dry_run")

    def test_cmd_wiki_query(self) -> None:
        with self._repo() as td, patch.object(swarmctl, "_repo_root", return_value=Path(td)):
            repo = Path(td)
            page = repo / "repos/data/knowledge/wiki-core/wiki/_briefs/search.md"
            page.write_text("# Search Note\n\nwiki-core retrieval result", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = swarmctl.cmd_wiki_query(SimpleNamespace(query="retrieval", limit=5, config=None))
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertEqual(payload["backend"], "tfidf")
            self.assertEqual(payload["results"][0]["title"], "Search Note")

    def test_cmd_wiki_publish_skills_local_only(self) -> None:
        with self._repo() as td, patch.object(swarmctl, "_repo_root", return_value=Path(td)):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = swarmctl.cmd_wiki_publish_skills(SimpleNamespace(config=None, global_target=None, mode="copy"))
            payload = json.loads(out.getvalue())
            self.assertEqual(rc, 0)
            self.assertTrue((Path(td) / ".agent/skills/wiki-ingest-source/SKILL.md").exists())
            self.assertEqual(payload["published"][0]["name"], "wiki-ingest-source")

    def test_wiki_core_context_is_c3_plus_only(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            (repo / "configs/orchestrator").mkdir(parents=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
memory:
  retrieval:
    wiki_core:
      enabled: true
      config: "configs/tooling/wiki_core.yaml"
      min_complexity: "C3"
      pre_search_task_types: ["T3"]
  feature_flags:
    wiki_core_pre_search: true
""".strip()
                + "\n",
                encoding="utf-8",
            )
            page = repo / "repos/data/knowledge/wiki-core/wiki/_briefs/context.md"
            page.write_text("# Context Note\n\npre-search wiki context", encoding="utf-8")

            c2 = swarmctl._maybe_wiki_core_context(repo, task_type="T3", complexity="C2", text="wiki context")
            c3 = swarmctl._maybe_wiki_core_context(repo, task_type="T3", complexity="C3", text="wiki context")

            self.assertIsNone(c2)
            self.assertEqual(c3["backend"], "tfidf")
            self.assertEqual(c3["results"][0]["title"], "Context Note")

    def test_wiki_core_writeback_writes_completed_c3_run(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            (repo / "configs/orchestrator").mkdir(parents=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
memory:
  retrieval:
    wiki_core:
      enabled: true
      config: "configs/tooling/wiki_core.yaml"
      min_complexity: "C3"
      pre_search_task_types: ["T3"]
  feature_flags:
    wiki_core_writeback: true
""".strip()
                + "\n",
                encoding="utf-8",
            )
            result = swarmctl._maybe_wiki_core_writeback(
                repo,
                run_id="run-1",
                objective="Implement wiki writeback",
                task_type="T3",
                complexity="C3",
                payload={"agent": {"status": "completed"}, "route": {"primary_model": "qwen", "orchestration_path": "Quality Path"}},
            )

            self.assertEqual(result["status"], "ok")
            path = Path(result["path"])
            self.assertTrue(path.exists())
            self.assertIn("Implement wiki writeback", path.read_text(encoding="utf-8"))

    def test_wiki_core_defaults_work_without_router_wiki_section(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            (repo / "configs/orchestrator").mkdir(parents=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
version: "4.2"
routing:
  tiers:
    C3:
      name: "Medium"
memory:
  retrieval:
    engine: "hybrid"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            page = repo / "repos/data/knowledge/wiki-core/wiki/_briefs/default-context.md"
            page.write_text("# Default Context\n\nwiki core default policy", encoding="utf-8")

            c3 = swarmctl._maybe_wiki_core_context(repo, task_type="T3", complexity="C3", text="default policy")

            self.assertEqual(c3["backend"], "tfidf")
            self.assertEqual(c3["results"][0]["title"], "Default Context")

    def test_registry_workflow_context_enables_swarm_wiki_presearch_for_non_default_task_type(self) -> None:
        with self._repo() as td:
            repo = Path(td)
            (repo / "configs/orchestrator").mkdir(parents=True)
            (repo / "configs/orchestrator/router.yaml").write_text(
                """
version: "4.2"
routing:
  tiers:
    C4:
      name: "Complex"
      path: "Swarm Path"
      workflow: "configs/registry/workflows/path-swarm.yaml"
      ralph_loop:
        enabled: true
        iterations: 5
  handoff_safeguards:
    max_chain_depth: 2
    forbid_cycles: true
    require_contract: true
memory:
  retrieval:
    engine: "hybrid"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            page = repo / "repos/data/knowledge/wiki-core/wiki/_briefs/swarm.md"
            page.write_text("# Swarm Note\n\nwiki context for swarm", encoding="utf-8")

            registry_ctx = swarmctl._resolve_registry_workflow_context(
                repo,
                task_type="T2",
                complexity="C4",
                orchestration_path="Swarm Path",
            )
            result = swarmctl._maybe_wiki_core_context(
                repo,
                task_type="T2",
                complexity="C4",
                text="swarm context",
                registry_workflow_context=registry_ctx,
            )

            self.assertEqual(registry_ctx["workflow_id"], "swarm-path-to-completion")
            self.assertEqual(result["backend"], "tfidf")
            self.assertEqual(result["results"][0]["title"], "Swarm Note")


if __name__ == "__main__":
    unittest.main()
