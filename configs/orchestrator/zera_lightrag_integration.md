# Zera — LightRAG Integration
# Version: 2026-04-09
# Integration doc (not source of truth for Zera commands).
# Zera command SoT: configs/tooling/zera_command_registry.yaml
# Memory policy SoT: configs/global/memory_policy.yaml

## Overview

Zera uses LightRAG as a knowledge retrieval layer to enhance research quality and provide grounded answers. Integration is mode-dependent.

## Mode-Specific Behavior

| Mode | LightRAG | Query Strategy |
|------|----------|----------------|
| researcher | enabled | Auto-query with debug=true, cite sources, flag gaps |
| analysis | enabled | Historical context, compare with current state |
| strategist | enabled | Query for historical context, inform strategy |
| plan | enabled | Knowledge-seeking queries only |
| love | disabled | Pure personal interaction |
| muse | disabled | Creative mode, no context constraints |
| hard_truth | enabled | Query for evidence to support honest assessment |

## Research Mode Flow (Primary Integration)

```
Research query received
  ↓
Query LightRAG with debug=true
  ↓
Evaluate retrieved chunks (scores, relevance)
  ↓
If scores > 0.5: use as primary source
  ↓
If scores < 0.3: note knowledge gap
  ↓
Synthesize answer with citations
```

**Research Registry config (configs/tooling/zera_research_registry.yaml):**
```yaml
lightrag:
  enabled: true
  default_topK: 5
  min_confidence: 0.3
  cite_sources: true
  show_debug: true
  max_context_chunks: 7
```

## Zera Commands (canonical: zera_command_registry.yaml)

| Command | Action |
|---------|--------|
| `zera:research <topic>` | Query LightRAG, produce detailed research output with citations |
| `zera:context <topic>` | Quick context lookup with source citations |
| `zera:foundry-ingest <content>` | Ingest new knowledge into LightRAG |
| `zera:knowledge-stats` | Show LightRAG index statistics |

## System Prompt Integration

```
When asked factual questions:
1. First check knowledge base (LightRAG)
2. If relevant context found (score > 0.3): cite it explicitly
3. If no context: say "I don't have specific information about this"
4. Never fabricate sources or context
5. Use confidence scores to qualify answers
```

## Growth Loop

```
Complete task (C4+)
  ↓
Extract learnings
  ↓
Format as structured document
  ↓
Call zera:foundry-ingest
  ↓
LightRAG indexes new knowledge
  ↓
Future tasks benefit from accumulated knowledge
```

This creates a compounding knowledge base that improves Zera's capabilities over time. Auto-ingest is enabled for C4+ tasks per memory write-back policy.

## Error Handling

| Error | Behavior |
|-------|----------|
| LightRAG unavailable | Degrade to general knowledge, log warning |
| Low confidence (< 0.3) | Flag to user, do not suppress |
| Ingestion failure | Retry 3x, then log to .agents/memory/errors/ |
