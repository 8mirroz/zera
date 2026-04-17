# Agent OS Memory System

Production-ready memory system with TTL, pruning, and BM25 semantic retrieval.

## Features

- **Working Memory**: 50-entry capacity with 24-hour TTL
- **Intelligent Pruning**: Retention policies + temporal decay
- **Fast Retrieval**: BM25 keyword search (<100ms for 1000 entries)
- **Safety**: Archive-before-delete, permanent entry protection

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from agent_os.memory import WorkingMemory, MemoryEntry
from datetime import datetime
from pathlib import Path

# Initialize working memory
wm = WorkingMemory(Path(".agents/memory/working_memory.json"))

# Add entry
wm.add(MemoryEntry(
    content="Implemented new feature",
    created_at=datetime.now().isoformat(),
    relevance=0.9,
    entry_type="task_trace"
))

# Query
results = wm.get_relevant("feature", top_k=5)

# Save
wm.save()
```

## Components

### WorkingMemory
Session-scoped memory with capacity limits and TTL.

### MemoryPruner
Prunes entries based on retention policies and temporal decay.

### BM25Retriever
Fast semantic retrieval using BM25 keyword search.

## Configuration

See `configs/orchestrator/router.yaml` for configuration options.

## Testing

```bash
python3 -m pytest tests/test_memory.py -v
```

## Examples

See `examples/memory_usage.py` for complete usage examples.

## Documentation

Full documentation: `audit/110326/PHASE_05_MEMORY_REPORT.md`
