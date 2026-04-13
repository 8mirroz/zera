"""Tests for LayeredMemoryRetriever."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.memory.layered_retriever import LayeredMemoryRetriever, LayeredResult


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in entries), encoding="utf-8")


def _make_repo(tmp_path: Path) -> Path:
    """Create minimal repo structure with memory layers."""
    # session layer
    _write_jsonl(
        tmp_path / ".agent/memory/session/session.jsonl",
        [{"content": "user prefers dark mode interface", "id": "s1"}],
    )
    # project layer
    _write_jsonl(
        tmp_path / ".agent/memory/projects/project.jsonl",
        [{"content": "project uses Python 3.12 and FastAPI", "id": "p1"}],
    )
    # workspace layer
    _write_jsonl(
        tmp_path / ".agent/memory/build-library/global/workspace.jsonl",
        [{"content": "global convention: always write tests", "id": "w1"}],
    )
    # policy config
    (tmp_path / "configs/global").mkdir(parents=True)
    (tmp_path / "configs/global/memory_policy.yaml").write_text(
        """version: 1
memory_layers:
  session:
    path: .agent/memory/session/
  project:
    path: .agent/memory/projects/
  workspace:
    path: .agent/memory/build-library/global/
  user_preferences:
    path: .agent/memory/build-library/global/
""",
        encoding="utf-8",
    )
    return tmp_path


class TestLayeredMemoryRetriever:
    def test_retrieve_finds_session_entry(self, tmp_path):
        repo = _make_repo(tmp_path)
        r = LayeredMemoryRetriever(repo)
        results = r.retrieve("dark mode", top_k=5, min_score=0.0)
        contents = [res.content for res in results]
        assert any("dark mode" in c for c in contents)

    def test_retrieve_finds_project_entry(self, tmp_path):
        repo = _make_repo(tmp_path)
        r = LayeredMemoryRetriever(repo)
        results = r.retrieve("Python FastAPI", top_k=5, min_score=0.0)
        contents = [res.content for res in results]
        assert any("Python" in c for c in contents)

    def test_session_layer_scores_higher_than_workspace(self, tmp_path):
        """Session layer weight (1.0) > workspace weight (0.70)."""
        # Put same content in both layers
        _write_jsonl(
            tmp_path / ".agent/memory/session/s2.jsonl",
            [{"content": "routing policy test entry", "id": "s2"}],
        )
        _write_jsonl(
            tmp_path / ".agent/memory/build-library/global/w2.jsonl",
            [{"content": "routing policy test entry", "id": "w2"}],
        )
        repo = _make_repo(tmp_path)
        r = LayeredMemoryRetriever(repo)
        results = r.retrieve("routing policy test entry", top_k=10, min_score=0.0)
        # After dedup, only one entry survives — it should be from session
        routing_results = [res for res in results if "routing policy" in res.content]
        if routing_results:
            assert routing_results[0].source_layer == "session"

    def test_retrieve_from_single_layer(self, tmp_path):
        repo = _make_repo(tmp_path)
        r = LayeredMemoryRetriever(repo)
        results = r.retrieve_from_layer("project", "Python", top_k=5)
        assert all(res.source_layer == "project" for res in results)

    def test_empty_layers_return_empty(self, tmp_path):
        (tmp_path / "configs/global").mkdir(parents=True)
        (tmp_path / "configs/global/memory_policy.yaml").write_text(
            "version: 1\nmemory_layers:\n  session:\n    path: .agent/memory/session/\n"
        )
        r = LayeredMemoryRetriever(tmp_path)
        results = r.retrieve("anything", top_k=5, min_score=0.0)
        assert results == []

    def test_deduplication_keeps_highest_score(self, tmp_path):
        """Same content in two layers — only one result after dedup."""
        content = "unique dedup test content"
        _write_jsonl(tmp_path / ".agent/memory/session/d1.jsonl", [{"content": content, "id": "d1"}])
        _write_jsonl(tmp_path / ".agent/memory/projects/d2.jsonl", [{"content": content, "id": "d2"}])
        repo = _make_repo(tmp_path)
        r = LayeredMemoryRetriever(repo)
        results = r.retrieve(content, top_k=10, min_score=0.0)
        matching = [res for res in results if content in res.content]
        assert len(matching) == 1

    def test_result_has_required_fields(self, tmp_path):
        repo = _make_repo(tmp_path)
        r = LayeredMemoryRetriever(repo)
        results = r.retrieve("dark mode", top_k=5, min_score=0.0)
        if results:
            res = results[0]
            assert isinstance(res, LayeredResult)
            assert res.source_layer in {"session", "project", "workspace", "user_preferences"}
            assert isinstance(res.final_score, float)
            assert isinstance(res.content, str)

    def test_layer_restriction(self, tmp_path):
        repo = _make_repo(tmp_path)
        r = LayeredMemoryRetriever(repo)
        results = r.retrieve("mode", top_k=5, min_score=0.0, layers=["session"])
        assert all(res.source_layer == "session" for res in results)
