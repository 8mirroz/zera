# Wave 3 — Recommended Target Stack

**Audit:** Zera Fractal Multi-Agent Architecture Blueprint
**Wave:** 3 of 4
**Date:** 2026-04-13
**Source:** ARCHITECTURE_OPTIONS_COUNCIL.md + WEIGHTED_DECISION_MATRIX.md

---

## Target Stack Overview

The recommended stack converges on a cohesive architecture: **async Python runtime** with **worker lanes** for parallelism, **SQLite** as the unified persistence layer, **process-isolated tools**, **outcome-weighted routing**, and a **FastAPI dashboard** for observability. Every choice is Option B (Evolutionary) — deliberate, incremental, and mutually reinforcing.

---

## Subsystem Recommendations

### 1. Runtime Execution Engine

**Recommended:** Async Python Runtime with Concurrency Pools
**Technology:** `asyncio` + `AsyncRuntimePool` class, built on existing `runtime_providers/` abstraction
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 2-3 weeks

**Why Not Runner-Up (gRPC Workers):** The gRPC worker pool model scores marginally higher (6.60 vs 6.45) but requires process management infrastructure, gRPC serialization, and cross-process debugging tools. For a 613-file project running on a single machine, the added complexity delivers parallelism the system cannot yet saturate. The async runtime delivers 80% of the benefit at 30% of the cost. When the system needs cross-machine scaling, the async pool interface can be replaced with a gRPC backend without changing calling code.

---

### 2. Coordination Model

**Recommended:** Orchestrator + Worker Lanes
**Technology:** Lane abstraction with file-based event bus (upgradeable to Redis/NATS)
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 2-3 weeks

**Why Not Runner-Up (Actor Model):** The actor model ties on raw score (6.15 each) but loses on reversibility (0.60 vs 0.20) and migration complexity (0.75 vs 0.30). Actors introduce eventual consistency, message loss handling, and distributed debugging — skills the project hasn't built. Lanes are a natural extension of existing workflow concepts: each lane is an independent agent context, and the file-based event bus is a stepping stone. When lane traffic exceeds file-based capacity, swap the event bus for Redis/NATS without changing the lane API.

---

### 3. Memory System

**Recommended:** SQLite + BM25 Hybrid Store
**Technology:** SQLite with FTS5 for BM25 indexing, WAL mode for multi-reader, TTL enforcement via triggers
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 2-3 weeks

**Why Not Runner-Up (Qdrant):** Qdrant ties on raw score (6.35 each) but loses on migration complexity (0.75 vs 0.30), cost efficiency (0.80 vs 0.40), and team readiness (0.35 vs 0.20). Running a vector database service is an operational burden. The `.agent/` vs `.agents/` drift must be resolved first anyway — merging directories and adding idempotency keys is a prerequisite that benefits both options. SQLite delivers ACID semantics immediately; Qdrant can be added later as a sync layer. The path: JSONL → SQLite adapter → Qdrant sync → Qdrant primary (when entry count exceeds 100K or latency exceeds 200ms).

---

### 4. Tool Layer

**Recommended:** Process Isolation Sandbox
**Technology:** Per-tool subprocess with resource limits (CPU, memory, FD), stdin/stdout/stderr isolation, capability registry
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 2 weeks

**Why Not Runner-Up (Harden tool_runner):** Option A scores 5.90 vs 6.45 — a significant gap. Hardening `tool_runner.py` doesn't provide crash isolation (a crashing tool kills the entire process) or resource protection (a runaway tool can consume all memory). Subprocess sandboxing is a well-understood pattern that fits the existing architecture. WASI (Option C, 5.80) is not viable for Python tools.

---

### 5. Routing / Model Selection

**Recommended:** Outcome-Weighted Routing
**Technology:** Outcome tracking database (SQLite), routing weight adjustments, A/B testing framework, YAML baseline with runtime overlay
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 2-3 weeks

**Why Not Runner-Up (Determinism Controls):** Option A scores 6.05 vs 6.50 — a meaningful gap. Adding seeds and `temperature: 0` to LLM calls is table stakes (and should be done anyway) but doesn't improve model selection quality over time. The LLM Meta-Router (Option C, 4.45) is the worst-scoring option across all subsystems — using non-determinism to control non-determinism is architecturally unsound.

---

### 6. Trace Pipeline

**Recommended:** SQLite Trace Store with Schema Enforcement
**Technology:** SQLite with strict v2.1 schema, indexes on task_id/tier/model/status/cost, automatic v1→v2 migration on read
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 1-2 weeks

**Why Not Runner-Up (OpenTelemetry):** OpenTelemetry scores slightly higher (6.30 vs 6.25) but the 0.05 gap is dwarfed by the infrastructure gap: OTel requires a collector, backend (Jaeger/Tempo), and dashboard (Grafana). SQLite gives us queryability, schema enforcement, and indexability with zero new infrastructure. The synergy: memory, traces, evals, queues, and cost all share one SQLite database. When multi-node scaling arrives, add an OTel exporter that reads from SQLite — no data loss, no migration.

---

### 7. Eval Pipeline

**Recommended:** Automated Quality Gate Pipeline
**Technology:** Eval results in SQLite (shared with traces), quality thresholds per tier, trend analysis, dashboard integration
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 2 weeks

**Why Not Runner-Up (Continuous Eval Platform):** Option C scores 6.30 vs 6.15 — the gap is small. But Option C's migration complexity (0.30) and team readiness (0.15) are the real constraints. ML-based anomaly detection requires training data the project doesn't have. Automated rollback on quality degradation requires a deployment pipeline the project doesn't run. Option B gives automated gates and trends with shared SQLite infrastructure. The continuous platform can be layered on top when the statistical maturity exists.

---

### 8. Dashboard UI

**Recommended:** SQLite-Backed FastAPI Web Dashboard
**Technology:** FastAPI + SQLite (read-only), real-time views for task queue, model usage, cost tracking, eval trends
**Migration Complexity:** **S** (small)
**Estimated Effort:** 1-2 weeks

**Why Not Runner-Up (Enhanced Markdown):** Option A scores 5.45 vs 6.05 — a significant gap. Markdown reports are static, non-interactive, and provide no real-time visibility. Grafana (Option C, 5.65) loses because it requires Prometheus metrics the system doesn't emit. FastAPI reads directly from the shared SQLite database — no new data source, no new ETL pipeline. A single-binary deployment that serves a web UI.

---

### 9. Queues / Retries / Durable Execution

**Recommended:** SQLite-Based Durable Execution
**Technology:** Task queue in SQLite, checkpoint-before-execute pattern, retry policies per tier, idempotency keys
**Migration Complexity:** **M** (medium)
**Estimated Effort:** 2-3 weeks

**Why Not Runner-Up (Temporal.io):** Temporal scores highest (6.70 vs 6.15) but at a structural cost: Temporal server infrastructure, a new operational paradigm, workflow definition language changes, and team training. For a single-node agent OS, it's over-engineering. SQLite durable execution gives crash-safe, resumable execution with the same database. The workflow definitions are portable — when scale demands distributed execution, migrate to Temporal with the same logical workflows.

---

### 10. Cost Control

**Recommended:** Runtime Cost Tracker with Budget Enforcement
**Technology:** Token usage parsing from API responses, running totals per profile/day/week, budget enforcement at router level, alert thresholds
**Migration Complexity:** **S** (small)
**Estimated Effort:** 1 week

**Why Not Runner-Up (Router-Level Enforcement):** Option A scores 5.60 vs 6.20 — a clear gap. Pre-call cost estimation is inherently approximate (token count is unknown before the call). Option B tracks actual usage from API responses, maintains running totals, and enforces budgets with accurate data. The multi-tenant quota system (Option C, 5.40) is designed for SaaS billing — premature for a single-user agent OS.

---

## Migration Complexity Summary

| Subsystem | Complexity | Effort | Blockers |
|-----------|:----------:|--------|----------|
| 1. Runtime Execution | M | 2-3 weeks | Async migration of 202 Python files |
| 2. Coordination Model | M | 2-3 weeks | Lane management infrastructure |
| 3. Memory System | M | 2-3 weeks | JSONL → SQLite migration, `.agents/` merge |
| 4. Tool Layer | M | 2 weeks | Sandbox infrastructure, resource limits |
| 5. Routing/Model Selection | M | 2-3 weeks | Outcome tracking, statistical calibration |
| 6. Trace Pipeline | M | 1-2 weeks | JSONL → SQLite, v1→v2 migration |
| 7. Eval Pipeline | M | 2 weeks | Threshold definition, calibration period |
| 8. Dashboard UI | S | 1-2 weeks | Depends on SQLite (traces + evals) |
| 9. Queues/Retries/Durable | M | 2-3 weeks | Checkpoint infrastructure, idempotency |
| 10. Cost Control | S | 1 week | API response parsing, budget integration |

**Total Estimated Effort:** 17-24 weeks (4-6 months) for a single developer + AI agents. Parallel workstreams can reduce this to 12-16 weeks.

---

## Dependency Order — Build Sequence

The subsystems are not independent. The build order is determined by data dependencies, infrastructure requirements, and risk mitigation.

### Phase 1: Foundation (Weeks 1-4)

**Priority 1: Resolve `.agent/` vs `.agents/` Drift** (not a subsystem, but a prerequisite)
- Canonical directory: `.agent/`
- Merge `.agents/` content into `.agent/`
- Update all references across 613 files
- Duration: 1 week
- Risk: High — reference updates must be exhaustive

**Priority 2: SQLite Core** (subsystem 3, partial)
- Create SQLite schema for memory, traces, evals, queues, cost
- Implement SQLite adapter layer
- Migrate JSONL memory writes to SQLite
- Duration: 2 weeks
- Dependency: Priority 1 (directory consolidation)

**Priority 3: Trace Pipeline** (subsystem 6)
- SQLite trace store with v2.1 schema enforcement
- Migrate existing JSONL traces
- Duration: 1-2 weeks (overlaps with Priority 2)
- Dependency: Priority 2 (SQLite core)

### Phase 2: Execution Backbone (Weeks 5-10)

**Priority 4: Async Runtime** (subsystem 1)
- Add async layer on top of existing sync providers
- Migrate C1/C2 to async pools first (lowest risk)
- Migrate C3/C4/C5 incrementally
- Duration: 3 weeks
- Dependency: None (can start Week 3, parallel with Phase 1)

**Priority 5: Coordination Model** (subsystem 2)
- Implement lane abstraction
- File-based event bus
- Integrate with async runtime
- Duration: 2-3 weeks
- Dependency: Priority 4 (async runtime)

**Priority 6: Tool Sandbox** (subsystem 4)
- Per-tool subprocess isolation
- Resource limits, capability registry
- Duration: 2 weeks
- Dependency: Priority 4 (async runtime — sandbox runs in subprocess)

### Phase 3: Intelligence Layer (Weeks 11-14)

**Priority 7: Outcome-Weighted Routing** (subsystem 5)
- Outcome tracking in SQLite
- Routing weight adjustments
- A/B testing framework
- Duration: 2-3 weeks
- Dependency: Priority 2 (SQLite), Priority 3 (traces for outcome data)

**Priority 8: Eval Pipeline** (subsystem 7)
- Eval results in SQLite
- Quality thresholds, trend analysis
- Duration: 2 weeks
- Dependency: Priority 2 (SQLite), Priority 7 (routing outcomes)

**Priority 9: Cost Control** (subsystem 10)
- Token usage tracking
- Budget enforcement
- Alert thresholds
- Duration: 1 week
- Dependency: Priority 7 (routing — cost tracked per call)

### Phase 4: Visibility & Durability (Weeks 15-18)

**Priority 10: Dashboard UI** (subsystem 8)
- FastAPI web dashboard
- Real-time views
- Duration: 1-2 weeks
- Dependency: Priority 2 (SQLite), Priority 3 (traces), Priority 8 (evals)

**Priority 11: Durable Execution** (subsystem 9)
- Task queue in SQLite
- Checkpoint-before-execute
- Retry policies, idempotency keys
- Duration: 2-3 weeks
- Dependency: Priority 2 (SQLite), Priority 4 (async runtime)

### Dependency Graph

```
                    ┌─────────────────────┐
                    │  P1: .agent/ Merge  │  Week 1
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │  P2: SQLite Core    │  Weeks 2-3
                    └──────┬──┬──┬───────┘
                           │  │  │
              ┌────────────┘  │  └─────────────┐
              │               │                │
    ┌─────────▼───────┐ ┌────▼────┐  ┌────────▼────────┐
    │ P3: Trace Store │ │ P7:     │  │ P8: Eval Pipeline│
    │   Weeks 3-4     │ │ Routing │  │   Weeks 12-13   │
    └────────┬────────┘ │Weeks 11 │  └────────┬────────┘
             │          │  -12    │           │
             │          └────┬────┘     ┌─────▼──────┐
             │               │          │ P10: Dash  │
    ┌────────▼────────┐ ┌────▼────┐     │Weeks 15-16 │
    │ P4: Async Runtime│ │P10:Cost │     └────────────┘
    │   Weeks 5-7     │ │Week 14  │
    └────────┬────────┘ └─────────┘
             │
    ┌────────▼────────┐
    │ P5: Coord Lanes │
    │   Weeks 8-10    │
    └────────┬────────┘
             │
    ┌────────▼────────┐  ┌───────────────┐
    │ P6: Tool Sandbox│  │P11: Durable   │
    │   Weeks 8-9     │  │  Weeks 16-18  │
    └─────────────────┘  └───────────────┘
```

### Critical Path

The critical path is: **P1 → P2 → P4 → P5 → P11** (10-12 weeks minimum).

All other subsystems can be built in parallel with the critical path. With parallel workstreams, the total timeline compresses to 12-16 weeks.

---

## Infrastructure Footprint — Before vs After

| Component | Before | After | New Dependencies |
|-----------|--------|-------|------------------|
| Execution model | Sync subprocess | Async pools | None (stdlib asyncio) |
| Coordination | Sequential YAML | Lanes + event bus | None (file-based) |
| Memory | JSONL + fragmented dirs | SQLite + FTS5 | None (stdlib sqlite3) |
| Tools | tool_runner.py | Subprocess sandbox | None (stdlib subprocess) |
| Routing | Static YAML | YAML + outcome overlay | None |
| Traces | Append-only JSONL | SQLite with schema | None |
| Evals | File-based | SQLite with thresholds | None |
| Dashboard | Bash + markdown | FastAPI web UI | fastapi, uvicorn |
| Queues | None | SQLite-based | None |
| Cost | Declarative YAML | Runtime enforcement | None |

**New external dependencies:** 2 (fastapi, uvicorn) — both are lightweight, well-maintained, and already in the Python ecosystem.

**New infrastructure to operate:** 1 (SQLite database file) — already part of Python standard library.

This is the defining characteristic of the recommended stack: **maximal architectural improvement, minimal new infrastructure**. Every persistence subsystem converges on SQLite. The only new dependency is FastAPI for the dashboard — and even that can be served as a single binary with no production database requirement.

---

## Upgrade Paths

Each recommended option has a clear upgrade path to more powerful infrastructure when scale demands it:

| Subsystem | Current Target | Upgrade Path | Trigger |
|-----------|---------------|--------------|---------|
| Runtime | Async pools | gRPC workers | Cross-machine scaling needed |
| Coordination | File event bus | Redis/NATS | Lane event rate > 100/sec |
| Memory | SQLite + BM25 | Qdrant vectors | Entry count > 100K or latency > 200ms |
| Tools | Subprocess sandbox | WASI runtime | Python WASI matures, security requirements increase |
| Routing | Outcome-weighted | LLM meta-router | Sufficient outcome data, deterministic router proven insufficient |
| Traces | SQLite | OpenTelemetry | Multi-node scaling, need distributed traces |
| Evals | SQLite gates | ML anomaly detection | Sufficient historical eval data |
| Dashboard | FastAPI | Grafana + Prometheus | Need SLO tracking, alerting |
| Queues | SQLite durable | Temporal.io | Multi-node execution, need workflow orchestration |
| Cost | Runtime tracker | Multi-tenant quotas | Multi-user platform, billing required |

The key insight: **none of these upgrades require throwing away the current implementation.** Each upgrade path preserves the abstraction layer and swaps the implementation. The SQLite schema becomes the OTel data source. The lane API stays the same when the event bus moves to Redis. The workflow definitions are portable to Temporal.

This is the evolutionary strategy: build the right architecture for today, designed to evolve into tomorrow's architecture without a rewrite.
