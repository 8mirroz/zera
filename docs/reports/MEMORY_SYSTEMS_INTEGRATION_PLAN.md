# Memory Systems Integration — Audit & Plan

**Date:** 2026-04-09  
**Scope:** Obsidian, NotebookLM, LightRAG, BM25 Memory, Design Memory, LightGraph  
**Status:** Audit Complete → Integration Plan

---

## 1. AUDIT — Current State

### 1.1 LightRAG — ✅ INTEGRATED (mature)

| Aspect | Status | Details |
|--------|--------|---------|
| MCP Server | ✅ Running | `repos/mcp/lightrag/` — built, with 4 tools |
| MCP Config | ✅ Configured | `configs/tooling/mcpServers/lightrag.json` |
| Router Integration | ✅ Active | `router.yaml` → `semantic_backend: "lightrag"` |
| Zera Integration | ✅ Mode-dependent | researcher/strategist/analysis modes use LightRAG |
| Hermes Integration | ✅ Two-layer memory | long_term_memory + knowledge_retrieval |
| Skills | ✅ `lightrag-query` skill exists | `configs/skills/lightrag-query.md` |
| Documentation | ✅ Complete | `docs/ki/LIGHTRAG_INTEGRATION.md` |
| Ingestion | ✅ Growth loop | C4+ tasks auto-ingest via `zera:foundry-ingest` |
| Tests | ✅ Tested | Part of reliability test suite |

**Gaps:**
- ❌ Not connected to Design Memory Bank (new system)
- ❌ Not connected to Visual QA results
- ❌ Not connected to Design Evolution learnings
- ❌ Design decisions not auto-ingested into LightRAG

### 1.2 Obsidian — ⚠️ PARTIALLY INTEGRATED

| Aspect | Status | Details |
|--------|--------|---------|
| Vault Template | ✅ Exists | `templates/obsidian-vault/` with structure |
| Integration Script | ✅ Exists | `scripts/zera-obsidian-integration.sh` |
| Auto Sync | ✅ Exists | `scripts/obsidian_auto_sync.py` |
| Post-Task Sync | ✅ Exists | `scripts/obsidian_post_task.py` |
| Skill | ✅ Exists | `obsidian-dna-inject` skill |
| Knowledge Import | ✅ Partial | Nano Banana 2 prompt feed auto-imports |
| Project Script | ✅ Exists | `scripts/obsidian_project.py` |

**Gaps:**
- ❌ No semantic bridge to LightRAG (Obsidian ↔ LightRAG not synced)
- ❌ Design decisions not exported to Obsidian vault
- ❌ No automated sync of design memory → Obsidian
- ❌ No Obsidian → Design Memory import pipeline
- ❌ Canvas/graph visualization not connected to system

### 1.3 NotebookLM — ⚠️ PARTIALLY INTEGRATED

| Aspect | Status | Details |
|--------|--------|---------|
| Integration Config | ✅ Exists | `configs/tooling/notebooklm_integration.json` |
| Router Templates | ✅ Exists | `configs/tooling/notebooklm_agent_router_templates.json` |
| Python Package | ✅ Installed | `notebooklm-py[browser,cookies]==0.3.4` |
| Doctor Check | ✅ Exists | `notebooklm-doctor` validates health |
| Tests | ✅ Exists | `test_notebooklm_router_prompt.py`, `test_swarmctl_notebooklm_router.py` |
| Documentation | ✅ Exists | `docs/guides/NOTEBOOKLM_PY_INTEGRATION_2026-03-11.md` |

**Gaps:**
- ❌ Not connected to design system knowledge
- ❌ No automated research pipeline for design decisions
- ❌ No NotebookLM → Design Memory feedback loop
- ❌ Auth bootstrap requires manual intervention

### 1.4 BM25 Memory — ✅ INTEGRATED (core)

| Aspect | Status | Details |
|--------|--------|---------|
| Memory Store | ✅ Active | `.agent/memory/memory.jsonl` — 228+ entries |
| Repo Catalog | ✅ Indexed | `repos-catalog/indexes/` — aliases, repos |
| Router Integration | ✅ Active | `router.yaml` → retrieval engine |
| Hybrid Retrieval | ✅ Configured | `engine: "hybrid"`, `semantic_backend: "lightrag"` |

**Gaps:**
- ❌ Design decisions not in BM25 memory
- ❌ Visual QA reports not indexed
- ❌ No cross-referencing between BM25 and LightRAG

### 1.5 Design Memory — ✅ NEW (not connected to external)

| Aspect | Status | Details |
|--------|--------|---------|
| Decision Store | ✅ Created | `repos/packages/design-memory/src/store/` |
| Query Engine | ✅ Created | BM25 via lunr.js |
| Advisor | ✅ Created | DecisionAdvisor + FailureWarner |
| Seed Entries | ✅ 4 entries | AnimatedReveal, StaggerList, PremiumMotion, ReducedMotionGate |

**Gaps:**
- ❌ Not connected to LightRAG (no cross-querying)
- ❌ Not connected to Obsidian (no export/import)
- ❌ Not connected to NotebookLM (no research pipeline)
- ❌ No auto-ingestion into external memory systems

---

## 2. INTEGRATION ARCHITECTURE

### Target State

```
┌─────────────────────────────────────────────────────────────────────┐
│                    UNIFIED MEMORY FABRIC                             │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Design  │  │  Visual  │  │  Motion  │  │  Design  │           │
│  │  Memory  │  │   QA     │  │  System  │  │Evolution │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │             │              │                  │
│       └──────────────┴──────┬──────┴──────────────┘                  │
│                             │                                        │
│                    ┌────────▼────────┐                               │
│                    │  Memory Bridge  │ ← NEW: Cross-system sync      │
│                    │  (unified API)  │                               │
│                    └────────┬────────┘                               │
│                             │                                        │
│       ┌─────────────────────┼─────────────────────┐                 │
│       │                     │                      │                 │
│  ┌────▼────┐         ┌─────▼─────┐         ┌──────▼──────┐         │
│  │ LightRAG│◄───────►│   BM25    │◄───────►│  Obsidian   │         │
│  │  (MCP)  │  sync   │  Memory   │  sync   │    Vault    │         │
│  └────┬────┘         └─────┬─────┘         └──────┬──────┘         │
│       │                    │                       │                 │
│  ┌────▼────┐         ┌─────▼─────┐                │                 │
│  │NotebookLM│        │LightGraph │                │                 │
│  │Research │         │(planned)  │                │                 │
│  └─────────┘         └───────────┘                │                 │
│                                                    │                 │
│       ┌────────────────────────────────────────────┘                 │
│       │                                                              │
│  ┌────▼─────────────────────────────────────────────┐               │
│  │              Agent OS Router                      │               │
│  │  router.yaml → retrieval → memory_bridge → agents │               │
│  └───────────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
```

### Integration Points

| From | To | Method | Direction | Priority |
|------|-----|--------|-----------|----------|
| Design Memory | LightRAG | Auto-ingest decisions | → | P0 |
| Design Memory | Obsidian | Export as markdown notes | → | P0 |
| LightRAG | Design Memory | Query for past decisions | ← | P0 |
| Visual QA | LightRAG | Ingest QA reports | → | P1 |
| Visual QA | Obsidian | Export reports as notes | → | P1 |
| NotebookLM | Design Memory | Research → decision record | ← | P1 |
| Design Evolution | LightRAG | Ingest evolution records | → | P1 |
| Design Evolution | Obsidian | Export evolution plans | → | P2 |
| BM25 | LightRAG | Cross-index design memory | ↔ | P1 |
| Obsidian | Design Memory | Import vault notes | ← | P2 |

---

## 3. IMPLEMENTATION PLAN

### Phase 1: Memory Bridge (P0)

Create unified API that bridges all memory systems:

```
repos/packages/memory-bridge/
├── src/
│   ├── adapters/
│   │   ├── lightRagAdapter.ts      — LightRAG MCP client
│   │   ├── designMemoryAdapter.ts  — Design Memory client
│   │   ├── obsidianAdapter.ts      — Obsidian vault sync
│   │   ├── notebooklmAdapter.ts    — NotebookLM research
│   │   └── bm25Adapter.ts          — BM25 memory client
│   ├── bridge/
│   │   ├── memoryBridge.ts         — Unified API
│   │   ├── syncEngine.ts           — Cross-system sync
│   │   └── conflictResolver.ts     — Handle conflicts
│   └── types.ts
├── scripts/
│   ├── sync_all.sh                 — Full sync across systems
│   ├── ingest_design_memory.sh     — Design Memory → LightRAG
│   └── export_to_obsidian.sh       — Design Memory → Obsidian
└── configs/
    └── memory_bridge.yaml          — Bridge configuration
```

### Phase 2: Auto-Ingestion Pipelines (P1)

```
# When design decision recorded → auto-ingest to LightRAG
DesignDecision recorded
  → Memory Bridge intercepts
  → Format for LightRAG ingestion
  → lightrag_ingest_documents called
  → Format for Obsidian export
  → Markdown note created in vault
  → Index in BM25 memory

# When Visual QA report generated → auto-store
VisualQAReport generated
  → Memory Bridge stores report
  → Ingest summary to LightRAG
  → Export full report to Obsidian
```

### Phase 3: Cross-Query System (P1)

```
Agent query: "How should I build animated card?"
  → Memory Bridge queries ALL systems:
    1. Design Memory → Past decisions about cards
    2. LightRAG → Related knowledge
    3. BM25 → Indexed memories
    4. Obsidian → Vault notes
  → Aggregates results
  → Removes duplicates
  → Ranks by relevance
  → Returns unified answer
```

### Phase 4: Obsidian Bidirectional Sync (P2)

```
Design Memory → Obsidian:
  - Export decisions as markdown notes
  - Create canvas connections
  - Tag and organize by category

Obsidian → Design Memory:
  - Import new notes as decisions
  - Extract patterns from vault
  - Update decision records
```

---

## 4. FILES TO CREATE

| File | Purpose | Priority |
|------|---------|----------|
| `repos/packages/memory-bridge/src/index.ts` | Unified memory API | P0 |
| `repos/packages/memory-bridge/src/adapters/*` | 5 adapters | P0 |
| `repos/packages/memory-bridge/src/bridge/memoryBridge.ts` | Bridge core | P0 |
| `repos/packages/memory-bridge/src/bridge/syncEngine.ts` | Sync orchestrator | P0 |
| `repos/packages/memory-bridge/package.json` | Package definition | P0 |
| `repos/packages/memory-bridge/scripts/sync_all.sh` | Full sync script | P0 |
| `repos/packages/memory-bridge/scripts/ingest_design_memory.sh` | Design→LightRAG | P0 |
| `repos/packages/memory-bridge/scripts/export_to_obsidian.sh` | Design→Obsidian | P0 |
| `repos/packages/memory-bridge/configs/memory_bridge.yaml` | Configuration | P0 |
| `.agent/skills/memory-bridge.md` | Bridge usage skill | P1 |
| `.agent/workflows/memory-sync.md` | Sync workflow | P1 |

---

## 5. ROLLBACK PLAN

If integration causes issues:
1. Disable sync engine → systems work independently
2. Each system has its own storage (no shared state)
3. Bridge is additive, not modifying existing data
4. All sync operations are idempotent

---

*Plan version: 1.0.0 | Created: 2026-04-09*
