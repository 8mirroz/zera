"""Tests for memory system: WorkingMemory, MemoryPruner, BM25Retriever."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_os.memory import (
    WorkingMemory,
    MemoryEntry,
    MemoryPruner,
    PruningConfig,
    RetentionPolicy,
    BM25Retriever,
)


class TestWorkingMemory:
    def test_capacity_limit(self, tmp_path):
        """Adding >50 entries should evict lowest relevance"""
        wm = WorkingMemory(tmp_path / "wm.json")
        for i in range(60):
            wm.add(MemoryEntry(
                content=f"entry_{i}",
                relevance=i / 60,
                created_at=datetime.now().isoformat()
            ))
        assert len(wm.entries) <= 50
        # Highest relevance entries should remain
        assert all(e.relevance >= 10/60 for e in wm.entries)

    def test_ttl_expiration(self, tmp_path):
        """Entries older than TTL should be cleared"""
        wm = WorkingMemory(tmp_path / "wm.json")
        
        # Add old entry
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        wm.add(MemoryEntry(content="old", created_at=old_time, relevance=0.8))
        
        # Add recent entry
        recent_time = datetime.now().isoformat()
        wm.add(MemoryEntry(content="recent", created_at=recent_time, relevance=0.5))
        
        removed = wm.clear_expired()
        assert removed == 1
        assert len(wm.entries) == 1
        assert wm.entries[0].content == "recent"

    def test_persistence(self, tmp_path):
        """Save and load should preserve entries"""
        path = tmp_path / "wm.json"
        wm1 = WorkingMemory(path)
        wm1.add(MemoryEntry(content="test1", created_at=datetime.now().isoformat()))
        wm1.add(MemoryEntry(content="test2", created_at=datetime.now().isoformat()))
        wm1.save()
        
        wm2 = WorkingMemory(path)
        assert len(wm2.entries) == 2
        assert wm2.entries[0].content == "test1"

    def test_get_relevant(self, tmp_path):
        """Query should return relevant entries"""
        wm = WorkingMemory(tmp_path / "wm.json")
        wm.add(MemoryEntry(content="routing configuration", created_at=datetime.now().isoformat(), relevance=0.7))
        wm.add(MemoryEntry(content="memory system", created_at=datetime.now().isoformat(), relevance=0.6))
        wm.add(MemoryEntry(content="routing model", created_at=datetime.now().isoformat(), relevance=0.5))
        
        results = wm.get_relevant("routing", top_k=2)
        assert len(results) == 2
        assert "routing" in results[0].content


class TestPruner:
    def test_permanent_entries_never_pruned(self, tmp_path):
        """ki_capture entries should never be pruned regardless of age"""
        pruner = MemoryPruner(PruningConfig(archive_path=str(tmp_path / "archive")))
        old_date = (datetime.now() - timedelta(days=365)).isoformat()
        entries = [
            {"type": "ki_capture", "created_at": old_date, "content": "important", "relevance": 0.1}
        ]
        kept, pruned = pruner.prune(entries)
        assert len(kept) == 1
        assert len(pruned) == 0

    def test_expired_entries_pruned(self, tmp_path):
        """task_trace entries older than 30 days should be pruned"""
        pruner = MemoryPruner(PruningConfig(archive_path=str(tmp_path / "archive")))
        old_date = (datetime.now() - timedelta(days=35)).isoformat()
        entries = [
            {"type": "task_trace", "created_at": old_date, "content": "old task", "relevance": 0.8}
        ]
        kept, pruned = pruner.prune(entries)
        assert len(kept) == 0
        assert len(pruned) == 1

    def test_archive_before_delete(self, tmp_path):
        """Pruned entries should be saved to archive directory"""
        archive_path = tmp_path / "archive"
        pruner = MemoryPruner(PruningConfig(
            archive_path=str(archive_path),
            archive_before_delete=True
        ))
        old_date = (datetime.now() - timedelta(days=35)).isoformat()
        entries = [
            {"type": "session_data", "created_at": old_date, "content": "old", "relevance": 0.5}
        ]
        kept, pruned = pruner.prune(entries)
        
        # Check archive was created
        archive_files = list(archive_path.glob("pruned_*.json"))
        assert len(archive_files) == 1
        archived = json.loads(archive_files[0].read_text())
        assert len(archived) == 1
        assert archived[0]["content"] == "old"

    def test_temporal_decay_scoring(self):
        """Older entries should have lower relevance scores"""
        pruner = MemoryPruner(PruningConfig(half_life_days=7))
        
        recent = {"created_at": datetime.now().isoformat(), "relevance": 1.0}
        old = {"created_at": (datetime.now() - timedelta(days=14)).isoformat(), "relevance": 1.0}
        
        recent_score = pruner.compute_relevance(recent, datetime.now().timestamp())
        old_score = pruner.compute_relevance(old, datetime.now().timestamp())
        
        assert recent_score > old_score
        # After 14 days (2 half-lives), score should be ~0.25
        assert 0.2 < old_score < 0.3

    def test_retention_policy_classification(self):
        """Different entry types should get correct retention policies"""
        pruner = MemoryPruner(PruningConfig())
        
        assert pruner.classify_retention({"type": "ki_capture"}) == RetentionPolicy.PERMANENT
        assert pruner.classify_retention({"type": "adr"}) == RetentionPolicy.PERMANENT
        assert pruner.classify_retention({"type": "pattern"}) == RetentionPolicy.LONG_TERM
        assert pruner.classify_retention({"type": "retro"}) == RetentionPolicy.LONG_TERM
        assert pruner.classify_retention({"type": "task_trace"}) == RetentionPolicy.MEDIUM_TERM
        assert pruner.classify_retention({"type": "session_data"}) == RetentionPolicy.SHORT_TERM


class TestBM25Retriever:
    def test_basic_retrieval(self, tmp_path):
        """Query should return relevant entries"""
        try:
            retriever = BM25Retriever(tmp_path / "idx")
            entries = [
                {"content": "routing configuration for model selection"},
                {"content": "memory pruning and TTL settings"},
                {"content": "security hardening with path validation"},
            ]
            retriever.build_index(entries)
            results = retriever.retrieve("routing model", top_k=2, min_score=0.0)
            assert len(results) > 0
            assert "routing" in results[0]["content"]
        except ImportError:
            pytest.skip("rank-bm25 not installed")

    def test_retrieval_latency(self, tmp_path):
        """Retrieval should complete in <100ms for 1000 entries"""
        try:
            retriever = BM25Retriever(tmp_path / "idx")
            entries = [
                {"content": f"test entry number {i} about topic {i%10}"}
                for i in range(1000)
            ]
            retriever.build_index(entries)
            
            start = time.perf_counter()
            retriever.retrieve("topic 5", top_k=5, min_score=0.0)
            elapsed_ms = (time.perf_counter() - start) * 1000
            
            assert elapsed_ms < 100, f"Retrieval took {elapsed_ms:.2f}ms, exceeds 100ms target"
        except ImportError:
            pytest.skip("rank-bm25 not installed")

    def test_min_score_filtering(self, tmp_path):
        """Results below min_score should be excluded"""
        try:
            retriever = BM25Retriever(tmp_path / "idx")
            entries = [
                {"content": "exact match query"},
                {"content": "completely unrelated content about something else"},
            ]
            retriever.build_index(entries)
            
            results = retriever.retrieve("exact match query", top_k=10, min_score=0.8)
            assert len(results) == 1
            assert "exact match" in results[0]["content"]
        except ImportError:
            pytest.skip("rank-bm25 not installed")

    def test_index_persistence(self, tmp_path):
        """Index should save and reload correctly"""
        try:
            idx_path = tmp_path / "idx"
            retriever1 = BM25Retriever(idx_path)
            entries = [
                {"content": "test entry one"},
                {"content": "test entry two"},
            ]
            retriever1.build_index(entries)
            retriever1.save_index()
            
            retriever2 = BM25Retriever(idx_path)
            loaded = retriever2.load_index()
            assert loaded is True
            assert len(retriever2.corpus) == 2
            
            results = retriever2.retrieve("test entry", top_k=2, min_score=0.0)
            assert len(results) == 2
        except ImportError:
            pytest.skip("rank-bm25 not installed")

    def test_retrieve_by_topic(self, tmp_path):
        """Topic-based retrieval should work"""
        try:
            retriever = BM25Retriever(tmp_path / "idx")
            entries = [
                {"content": "routing system architecture"},
                {"content": "routing configuration details"},
                {"content": "memory system design"},
            ]
            retriever.build_index(entries)
            
            results = retriever.retrieve_by_topic("routing", top_k=10)
            assert len(results) >= 2
            assert all("routing" in r["content"] for r in results)
        except ImportError:
            pytest.skip("rank-bm25 not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
