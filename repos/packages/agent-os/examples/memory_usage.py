"""Example usage of the Agent OS memory system."""
from pathlib import Path
from datetime import datetime
from agent_os.memory import (
    WorkingMemory,
    MemoryEntry,
    MemoryPruner,
    PruningConfig,
    BM25Retriever,
)


def example_working_memory():
    """Demonstrate working memory with TTL and capacity limits."""
    print("=== Working Memory Example ===")
    
    wm = WorkingMemory(Path(".agents/memory/working_memory.json"))
    
    wm.add(MemoryEntry(
        content="Implemented routing system with 3-tier architecture",
        created_at=datetime.now().isoformat(),
        relevance=0.9,
        entry_type="task_trace"
    ))
    
    results = wm.get_relevant("routing", top_k=5)
    print(f"Found {len(results)} relevant entries")
    
    wm.save()
    print(f"Saved {len(wm.entries)} entries")


def example_pruning():
    """Demonstrate memory pruning with retention policies."""
    print("\n=== Memory Pruning Example ===")
    
    config = PruningConfig(
        default_ttl_days=30,
        half_life_days=7,
        min_relevance_score=0.3,
        archive_before_delete=True,
        archive_path=".agents/memory/archive/"
    )
    pruner = MemoryPruner(config)
    
    entries = [
        {"type": "ki_capture", "created_at": "2025-01-01T00:00:00", "content": "Important", "relevance": 0.2},
        {"type": "session_data", "created_at": "2026-01-01T00:00:00", "content": "Temp", "relevance": 0.8},
    ]
    
    kept, pruned = pruner.prune(entries)
    print(f"Kept: {len(kept)}, Pruned: {len(pruned)}")


def example_bm25_retrieval():
    """Demonstrate BM25 semantic retrieval."""
    print("\n=== BM25 Retrieval Example ===")
    
    try:
        retriever = BM25Retriever(Path(".agents/memory/indexes"))
        entries = [
            {"content": "Routing configuration for model selection"},
            {"content": "Memory pruning with TTL policies"},
        ]
        
        retriever.build_index(entries)
        results = retriever.retrieve("routing model", top_k=2, min_score=0.5)
        print(f"Found {len(results)} results")
        
    except ImportError:
        print("⚠️  rank-bm25 not installed")


if __name__ == "__main__":
    example_working_memory()
    example_pruning()
    example_bm25_retrieval()
