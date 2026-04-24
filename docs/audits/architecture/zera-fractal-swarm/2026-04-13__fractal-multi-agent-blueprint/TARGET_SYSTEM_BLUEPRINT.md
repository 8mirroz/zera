# Target System Blueprint — Fractal Multi-Agent Architecture

> **Wave:** 4 — Target Execution Blueprint
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Wave 0 (Audit Scoping), Wave 1 (State Discovery), Wave 2 (Defect & Debt Catalog)
> **Successor:** Wave 5 (Incremental Migration Plan)

---

## 1. Vision Statement

Replace the current single-threaded sequential orchestration with a **fractal multi-agent execution platform** that:

- Decomposes work across **6 levels** (Mission → Program → Workflow → Task → Subtask → Atomic Action)
- Executes independent branches **in parallel** with deterministic coordination
- Maintains **full backward compatibility** with existing workflows, agents, and CLI tools during a staged migration
- Keeps the orchestration layer **strictly deterministic**; non-determinism is confined to LLM calls

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTROL PLANE                                     │
│                                                                             │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────────────┐  │
│  │  Mission     │  │  Wave         │  │  Policy & Governance             │  │
│  │  Planner     │─▶│  Decomposer   │─▶│  ┌─────────┐ ┌────────────────┐  │  │
│  │  (C4/C5)     │  │  (deterministic│  │  │ Approval│ │ Drift Detector │  │  │
│  └──────────────┘  │  DAG builder) │  │  │ Gates   │ │ Safe-Mode      │  │  │
│                    └───────────────┘  │  │ Engine  │ │ Triggers       │  │  │
│                                       │  └─────────┘ └────────────────┘  │  │
│                                       └──────────────────────────────────┘  │
│                                                    │                        │
│                                                    ▼                        │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     SCHEDULER & DISPATCHER                           │   │
│  │                                                                      │   │
│  │  ┌────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │   │
│  │  │ Lease      │  │ Priority    │  │ Dependency  │  │ Retry &      │ │   │
│  │  │ Manager    │  │ Queue       │  │ Resolver    │  │ Recovery     │ │   │
│  │  └────────────┘  └─────────────┘  └─────────────┘  └──────────────┘ │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                    │                        │
└────────────────────────────────────────────────────┼────────────────────────┘
                                                     │
┌────────────────────────────────────────────────────┼────────────────────────┐
│                           DATA PLANE               │                       │
│                                                    │                        │
│  ┌─────────────────────────────────────────────────┼────────────────────┐   │
│  │                     WORKER POOL                │                     │   │
│  │                                                ▼                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ Worker 1 │ │ Worker 2 │ │ Worker 3 │ │ Worker N │ │ Worker M │   │   │
│  │  │ (agent)  │ │ (agent)  │ │ (agent)  │ │ (agent)  │ │ (agent)  │   │   │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │   │
│  │       │             │             │             │             │       │   │
│  │  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐   │   │
│  │  │ Sandbox  │ │ Sandbox  │ │ Sandbox  │ │ Sandbox  │ │ Sandbox  │   │   │
│  │  │ Process  │ │ Process  │ │ Process  │ │ Process  │ │ Process  │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                    │                        │
│  ┌─────────────────────────────────────────────────┼────────────────────┐   │
│  │                    TOOL REGISTRY               │                     │   │
│  │                                                │                     │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┴───────┐           │   │
│  │  │ MCP      │ │ Shell    │ │ File     │ │ Custom       │           │   │
│  │  │ Servers  │ │ Commands │ │ System   │ │ Plugins      │           │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘           │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                    │                        │
└────────────────────────────────────────────────────┼────────────────────────┘
                                                     │
┌────────────────────────────────────────────────────┼────────────────────────┐
│                 OBSERVABILITY PLANE                │                       │
│                                                    │                        │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────────────────┐  │
│  │ Trace        │  │ Metric        │  │ Artifact                        │  │
│  │ Collector    │  │ Aggregator    │  │ Store                           │  │
│  │ (span/event) │  │ (throughput,  │  │ (artifacts, checkpoints,        │  │
│  │              │  │  latency,     │  │  outputs)                       │  │
│  │              │  │  queue-depth) │  │                                 │  │
│  └──────┬───────┘  └──────┬────────┘  └────────┬────────────────────────┘  │
│         │                  │                     │                           │
│         ▼                  ▼                     ▼                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     .agents/store/  (Canonical State Dir)            │   │
│  │                                                                      │   │
│  │  runs/{run_id}/waves/{wave_id}/workflows/{wf_id}/tasks/{task_id}/   │   │
│  │    events.jsonl   spans.jsonl   artifacts/   checkpoints/            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Descriptions

### 3.1 Control Plane

The control plane owns **what to execute**, **in what order**, and **under what constraints**.

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **Mission Planner** | Accepts a high-level mission (C4/C5 classification), decomposes into programs. Uses LLM for creative decomposition but wraps results in a deterministic DAG. | Mission description, context, constraints | Program DAG with dependencies |
| **Wave Decomposer** | Takes a Program and produces a set of Waves, each containing a set of Workflows with a dependency graph. Purely deterministic. | Program DAG | Wave list with workflow dependency graph |
| **Scheduler & Dispatcher** | Owns the execution timeline. Leases tasks to workers, resolves dependencies, manages retries, enforces priorities. | Wave/workflow DAG, available workers | Task assignments, lease grants, retry decisions |
| **Lease Manager** | Issues time-bound leases on tasks. A worker must heartbeat to retain a lease. Expired leases trigger re-dispatch. | Lease requests, heartbeats | Lease grants, lease revocations |
| **Priority Queue** | Orders ready tasks by priority, then by ready-time, then by task ID for determinism. | Ready tasks, priority assignments | Ordered dispatch queue |
| **Dependency Resolver** | Evaluates predecessor completion status. Marks tasks as `ready` when all dependencies are satisfied. | Task dependency graph, predecessor states | Ready/not-ready decisions |
| **Retry & Recovery** | Handles transient failures. Implements exponential backoff with jitter (bounded). Tracks retry budgets per entity. | Failed tasks, retry policies | Retry decisions, escalation events |
| **Policy & Governance Engine** | Evaluates approval gates, detects policy drift, triggers safe-mode on anomaly detection. | State transitions, policy rules | Approve/deny, safe-mode triggers |
| **Approval Gates Engine** | At defined pipeline stages (e.g., pre-merge, pre-production), halts execution and awaits operator approval. | Entity reaching gate stage | Gate pass/fail |
| **Drift Detector** | Compares actual execution metrics against expected baselines. Flags deviations in latency, throughput, failure rate. | Metrics, baselines | Drift alerts |
| **Safe-Mode Triggers** | On critical anomaly (e.g., cascade failure, resource exhaustion), freezes dispatch and forces sequential fallback. | Anomaly signals | Safe-mode activation |

### 3.2 Data Plane

The data plane owns **execution of assigned work** and **collection of results**.

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **Worker Pool** | Set of agent processes. Each worker claims leases, executes assigned tasks in an isolated sandbox, reports results. | Task leases, task definitions | Task results (success/failure), events, artifacts |
| **Sandbox Process** | Per-worker isolated execution environment. Enforces tool budgets, timeout limits, file system boundaries. | Task payload, tool allowlist | Execution output, captured events |
| **Tool Registry** | Catalog of available tools (MCP servers, shell commands, file operations, custom plugins). Workers query for tool capability and authorization. | Tool lookup requests | Tool descriptors, authorization decisions |

### 3.3 Observability Plane

The observability plane owns **recording**, **aggregating**, and **exposing** execution state.

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **Trace Collector** | Receives spans and events from workers. Writes to append-only JSONL files in `.agents/store/`. | Spans, events | Persisted trace files |
| **Metric Aggregator** | Computes throughput, latency percentiles, queue depth, worker utilization. Exposes via query API. | Raw events, periodic snapshots | Metric time series |
| **Artifact Store** | Stores task outputs, generated files, model outputs, checkpoints. Indexed by entity ID and lineage. | Artifacts from workers | Stored artifacts with metadata |
| **Canonical State Dir** | `.agents/store/` — the single source of truth. Structured as `runs/{run_id}/waves/{wave_id}/workflows/{wf_id}/tasks/{task_id}/`. | All observability writes | Durable, queryable state |

---

## 4. Data Flow

### 4.1 Mission-to-Completion Flow

```
Mission
  │
  │  [1] Mission Planner (LLM-assisted, deterministic DAG output)
  ▼
Program DAG
  │
  │  [2] Wave Decomposer (deterministic)
  ▼
Wave 1 ─── Wave 2 ─── Wave 3 ─── ...  (waves execute sequentially)
  │
  │  [3] Each wave contains workflows (parallel within wave)
  ▼
Workflow A    Workflow B    Workflow C  (parallel within wave, DAG between)
  │
  │  [4] Each workflow contains tasks (parallel where no dependency)
  ▼
Task 1    Task 2    Task 3   ...   (leased to workers, parallel execution)
  │
  │  [5] Each task may decompose into subtasks → actions → tool_calls
  ▼
Subtask 1.1    Subtask 1.2    ...
  │
  │  [6] Each action invokes a tool
  ▼
tool_call( MCP:stitch )    tool_call( shell:pytest )   ...
  │
  │  [7] Each tool_call produces a span (start/end) and events
  ▼
Span(open)  ───  Span(close)  ───  Event(tool_call_result)
  │
  │  [8] Results propagate upward; task completes when all subtasks complete
  ▼
Task completed ─── Artifacts written ─── Events emitted ─── State persisted
  │
  │  [9] Dependency resolver marks dependents as ready
  ▼
Next tasks dispatched
```

### 4.2 State Write Authority

```
┌─────────────┐          ┌─────────────┐          ┌─────────────┐
│ Control     │          │ Data        │          │ Observ.     │
│ Plane       │          │ Plane       │          │ Plane       │
├─────────────┤          ├─────────────┤          ├─────────────┤
│ MAY write:  │          │ MAY write:  │          │ MAY write:  │
│ - task      │          │ - spans     │          │ - spans     │
│   state     │          │ - events    │          │   (received │
│ - leases    │          │ - artifacts │          │   from      │
│ - queue     │          │ - tool_call │          │   workers)  │
│   state     │          │   results   │          │ - metrics   │
│             │          │             │          │ - artifact  │
│             │          │             │          │   metadata  │
└─────────────┘          └─────────────┘          └─────────────┘
```

**Rule:** No component writes outside its authority boundary. Workers (data plane) MUST NOT mutate task state directly; they report results via events, and the control plane transitions task state based on those events.

### 4.3 Cross-Plane Communication

```
Control Plane ──(lease grant)──▶ Worker
Control Plane ◀──(heartbeat)─── Worker
Control Plane ◀──(result event)─ Worker
Worker ──(span/event write)──▶ Trace Collector
Worker ──(artifact write)──▶ Artifact Store
Scheduler ◀──(dependency satisfied)── Dependency Resolver
Policy Engine ◀──(state transition event)── Control Plane
Policy Engine ──(safe-mode trigger)──▶ Scheduler
```

---

## 5. Deployment Model

### 5.1 Phase 1: Single-Process (Migration Target)

**Target:** Single Python process running the scheduler, workers (as threads/async tasks), and trace collection in-process.

```
┌─────────────────────────────────────────────────────┐
│  Single Python Process (asyncio event loop)         │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Control     │  │ Worker Pool │  │ Observ.     │  │
│  │ Plane       │  │ (asyncio    │  │ Plane       │  │
│  │ (coroutines)│  │  Tasks)     │  │ (in-proc)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                     │
│  Shared state via asyncio primitives:               │
│    - Lock (lease management)                        │
│    - Queue (task dispatch)                          │
│    - Event (dependency resolution)                  │
│                                                     │
│  File system: .agents/store/                        │
└─────────────────────────────────────────────────────┘
```

**Rationale:** Eliminates distributed-systems complexity during migration. Deterministic execution within a single process. Easy to test and debug.

### 5.2 Phase 2: Multi-Process (Future)

**Target:** Scheduler as a dedicated process, workers as separate processes (potentially on different machines), state via shared SQLite/PostgreSQL.

```
┌──────────────┐          ┌──────────────┐
│ Scheduler    │◀────────▶│ Worker Pool  │
│ Process      │  gRPC/   │ (separate    │
│              │  HTTP    │  processes)  │
└──────┬───────┘          └──────┬───────┘
       │                         │
       ▼                         ▼
┌──────────────┐          ┌──────────────┐
│ Shared DB    │          │ Shared FS    │
│ (SQLite/PG)  │          │ (.agents/)   │
└──────────────┘          └──────────────┘
```

**Migration path:** Phase 1 architecture is a strict subset of Phase 2. The interface between control plane and data plane is already process-bound in Phase 1, making the transition to IPC/RPC straightforward.

---

## 6. Backward Compatibility Strategy

### 6.1 Compatibility Goals

| Goal | Mechanism |
|------|-----------|
| Existing workflows continue to run unchanged | Single-adapter shim layer translates legacy workflow format to new entity model |
| `.agents/` (singular) remains readable | Read-compat symlink or dual-read during migration; all writes go to `.agents/` (plural) |
| Existing CLI tools work unchanged | `swarmctl.py` gains a `--v2` flag; default behavior routes through shim |
| Existing trace consumers work unchanged | Trace collector emits v1-compatible events alongside v2 events |

### 6.2 Shim Layer Architecture

```
┌───────────────────────────────────────────────────────┐
│  Legacy Workflow (v1 format)                          │
│  .agents/workflows/*.yaml                              │
└────────────────────┬──────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────┐
│  Shim Adapter                                         │
│  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │ Format          │  │ State Translator            │ │
│  │ Translator      │  │ (v1 state → v2 state        │ │
│  │ (v1 YAML →      │  │  queued/running/done →      │ │
│  │  v2 entity)     │  │  queued/running/completed)   │ │
│  └─────────────────┘  └─────────────────────────────┘ │
│  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │ Trace Bridge    │  │ CLI Router                  │ │
│  │ (v2 events →    │  │ (--v2 → native,             │ │
│  │  v1 event format│  │  default → shim)            │ │
│  │  for existing   │  │                             │ │
│  │  consumers)     │  │                             │ │
│  └─────────────────┘  └─────────────────────────────┘ │
└────────────────────┬──────────────────────────────────┘
                     │
                     ▼
┌───────────────────────────────────────────────────────┐
│  Fractal Execution Engine (v2)                        │
│  .agents/store/                                       │
└───────────────────────────────────────────────────────┘
```

### 6.3 Migration Timeline

| Phase | Duration | Action |
|-------|----------|--------|
| **P0: Shim Development** | 1 sprint | Build shim adapter, validate against 3 existing workflows |
| **P1: Parallel Execution** | 2 sprints | Implement scheduler, lease manager, worker pool (single-process) |
| **P2: Observability** | 1 sprint | Trace collector, artifact store, metric aggregator |
| **P3: Governance** | 1 sprint | Approval gates, drift detection, safe-mode triggers |
| **P4: Dual-Run Validation** | 1 sprint | Run legacy and v2 engines in parallel, compare outputs |
| **P5: Cutover** | 1 sprint | Switch default to v2, keep shim for rollback |

---

## 7. Non-Goals for Wave 4

- Distributed execution across machines (Phase 2)
- Dynamic worker auto-scaling (post-migration)
- LLM-driven decomposition at all levels (only Mission Planner uses LLM; Wave Decomposer is deterministic)
- Multi-tenant support
- WebSocket-based real-time UI (separate initiative)

---

## 8. Key Design Decisions

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| **Single-process Phase 1** | Eliminates distributed-systems complexity during migration; deterministic by construction | Multi-process from day one (too much risk) |
| **Lease-based task claiming** | Simple, well-understood pattern; no coordination database needed | Work-stealing (complex, non-deterministic) |
| **Append-only JSONL traces** | Append-only is crash-safe; JSONL is streamable and grep-friendly | SQLite traces (write contention in single-process) |
| **Deterministic orchestration** | Reproducible execution; debuggable; auditable | Fully LLM-driven orchestration (non-reproducible) |
| **6-level decomposition** | Matches existing workflow hierarchy; sufficient granularity | 4 levels (too coarse), 8 levels (overhead) |
| **`.agents/` as canonical** | Plural form is conventional; avoids collision with existing `.agents/` | Keep `.agents/` (migration complexity) |
| **Read-compat for `.agents/`** | Zero-downtime migration; existing tools continue working | Hard cutover (breaks existing consumers) |
