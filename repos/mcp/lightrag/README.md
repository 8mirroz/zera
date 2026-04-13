# LightRAG — Lightweight RAG for Antigravity Core

Low-latency, minimal-resource RAG system optimized for Mac M1 / 16GB.

## Architecture

Hexagonal architecture with clear separation:
- **Ports** (interfaces) in `src/*/types.ts`
- **Adapters** (implementations) in `src/*/`
- **Pipeline** orchestrates flow in `src/pipelines/`

## Features

- Semantic + token-based chunking with overlap
- Pluggable embeddings (local bge/e5/nomic + API OpenAI/Gemini)
- JSONL + in-memory index (default), SQLite optional
- Cosine similarity retrieval with hybrid keyword fallback
- Multi-provider LLM generation (OpenAI/Gemini/Ollama/Qwen)
- Embedding cache for performance
- Incremental ingestion
- MCP server integration
- CLI tools for ingest/query/debug

## Quick Start

```bash
npm install
npm run build

# Ingest documents
npm run ingest -- --file docs/my-doc.md --metadata '{"source":"manual"}'

# Query knowledge
npm run query -- "How does the routing system work?" --debug

# Run as MCP server
npm start
```

## Performance Targets

- Local retrieval: <200ms
- Embedding cache hit: <10ms
- Full query pipeline: <500ms (local models)

## Integration

- Hermes AI: exposes `long_term_memory` and `knowledge_retrieval` layers
- Zera: mode-aware querying via `zera-researcher` pipeline
- Agent OS: skill-based access via `lightrag-query`
