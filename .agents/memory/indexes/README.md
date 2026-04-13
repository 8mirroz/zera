# Memory Indexes

Auto-generated indexes for semantic retrieval. Do not edit manually.

- `bm25_index.pkl` — BM25 keyword index (pickled)
- `corpus.json` — Indexed corpus entries
- `topic_index.json` — Topic-based grouping index (future)

These are rebuilt automatically when >20% of entries change.

## Rebuild Trigger
The system monitors the ratio of new/modified entries to total entries.
When this exceeds 0.20 (20%), the index is automatically rebuilt.

## Manual Rebuild
If needed, delete the index files and they will be regenerated on next retrieval.
