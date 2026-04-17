# Wave 3 — Architecture Options Council

**Audit:** Zera Fractal Multi-Agent Architecture Blueprint
**Wave:** 3 of 4 (Options Council → Decision Matrix → Target Stack → Migration Plan)
**Date:** 2026-04-13
**Author:** Architecture Audit Agent
**Scope:** 10 subsystems evaluated across 3 options each (conservative / evolutionary / revolutionary)
**Inputs:** Wave 0 (scope & baseline), Wave 1 (fractal decomposition), Wave 2 (drift & gap analysis)

---

## Executive Summary

This document presents architecture options for each of the 10 subsystems identified during Waves 0-2. The current system operates as a single-threaded sequential orchestration with no true parallel agents, no lease/heartbeat mechanism, no idempotency on writes, fragmented memory directories (`.agents/` vs `.agents/`), and no distributed locking. Each subsystem below is evaluated on three axes: what exists today, what could replace it, and which path we recommend.

---

## 1. Runtime Execution Engine

**Current:** Sequential Python subprocess orchestration via `agent_os_python` runtime. 202 Python files in `repos/packages/agent-os/`. Entry points through `agent_runtime.py`, `tool_runner.py`, and runtime providers (`base.py`, `agent_os_python.py`, `zeroclaw.py`, `mlx_provider.py`).

### Option A — Conservative: Harden Sequential Runtime
Keep the existing Python subprocess model. Add error isolation per subprocess, structured logging, graceful shutdown, and retry policies. Wrap `tool_runner.py` with circuit breakers.

**Pros:** Zero migration cost, incremental improvement, no new dependencies, preserves all existing behavior.
**Cons:** No parallelism ceiling, single point of failure, cannot scale beyond one process.
**Risks:** Technical debt compounds as features multiply; becomes the bottleneck for any C4/C5 task.

### Option B — Evolutionary: Async Python Runtime with Concurrency Pools
Migrate to `asyncio`-based execution with configurable concurrency pools per tier. C1-C2 run in parallel pools of 4, C3 gets 2-agent parallel lanes, C4-C5 get orchestrator-controlled sequential. Uses existing `runtime_providers/` directory; adds `AsyncRuntimePool` class.

**Pros:** Real parallelism for independent tasks, backward-compatible runtime interface, leverages existing provider abstraction, no new infrastructure.
**Cons:** Python asyncio has a learning curve and debugging complexity, not truly distributed (still single-process), GIL limits CPU-bound parallelism.
**Risks:** Migration of 202 Python files to async-aware patterns is a multi-week effort; subtle deadlocks possible if not carefully designed.

### Option C — Revolutionary: Multi-Process Worker Pool with gRPC
Replace with a worker pool model: one orchestrator process spawns worker processes that communicate via gRPC. Each worker runs in its own process space with resource limits. Workers register via heartbeat. Supports cross-machine scaling.

**Pros:** True parallelism, fault isolation (crash one worker, others survive), cross-machine scaling, natural lease/heartbeat fit, industry-standard pattern.
**Cons:** Major rewrite, introduces gRPC dependency, requires process management infrastructure, significantly more complex deployment.
**Risks:** 3-6 month build-and-stabilize period, introduces networking failure modes, requires new observability tooling.

### Recommendation: **Option B (Evolutionary)**
Option C is premature — the system has 613 files total and has not yet proven the need for cross-machine scaling. Option B delivers 80% of the parallelism benefit at 20% of Option C's complexity. The existing `runtime_providers/` abstraction is already designed for this. Migration: add async layer on top of existing sync providers (adapter pattern), migrate tier-by-tier starting with C1/C2.

---

## 2. Coordination Model

**Current:** Centralized orchestration only. Workflows defined in YAML (44 files in `.agents/workflows/`), executed sequentially by the orchestrator. No choreography. No inter-agent communication. "Swarm" is a workflow name, not actual parallel execution.

### Option A — Conservative: Enhanced Centralized Orchestration
Keep centralized control. Add DAG execution within workflows, dependency graphs between steps, and parallel step groups. Use existing YAML workflow definitions.

**Pros:** Minimal change to existing workflow files, no new paradigms, predictable execution.
**Cons:** Still no true multi-agent coordination, orchestration bottleneck at scale.
**Risks:** DAG complexity grows quadratically; YAML becomes unwieldy.

### Option B — Evolutionary: Orchestrator + Worker Lanes
Introduce the concept of "lanes": an orchestrator assigns work to parallel lanes that execute concurrently. Lanes communicate via a shared event bus (file-based initially, upgradeable). Each lane has an independent agent context. Uses existing `lane_events.py` as foundation.

**Pros:** Real parallel execution, incremental upgrade path, lanes can be isolated or share state, natural fit for C4/C5 multi-agent patterns.
**Cons:** Requires new lane management infrastructure, file-based event bus has ordering/reliability limits.
**Risks:** Event ordering without a proper message broker is fragile; race conditions between lanes.

### Option C — Revolutionary: Full Actor Model (Choreography + Orchestration Hybrid)
Each agent is an actor with its own mailbox. Agents communicate via message passing. Orchestrator sets initial state and watches, but agents self-coordinate for sub-tasks. Uses a message broker (Redis/NATS) for delivery.

**Pros:** True multi-agent autonomy, natural fault tolerance, scales to many agents, supports complex coordination patterns.
**Cons:** Massive paradigm shift, requires message broker infrastructure, debugging distributed systems is hard, overkill for current workload.
**Risks:** Actor model introduces eventual consistency, message loss scenarios, debugging complexity. Team needs new skills.

### Recommendation: **Option B (Evolutionary)**
Option C requires infrastructure (message broker) and skills the project does not yet have. Option B builds on existing `lane_events.py`, introduces parallelism without the full actor model complexity. The file-based event bus is a stepping stone — when lane traffic exceeds its capacity, upgrade to Redis/NATS without changing the lane abstraction.

---

## 3. Memory System

**Current:** Fragmented. `.agents/memory/` (BM25 indexes, working memory JSONL, pattern cache) and `.agents/` (duplicate directory — critical drift from Wave 2). JSONL append-only writes with no idempotency. LightRAG integration exists but is separate. Unified fabric declared in `router.yaml` but not fully implemented.

### Option A — Conservative: Consolidate Directories, Keep Storage Model
Merge `.agents/` into `.agents/` (canonical). Add idempotency keys to all memory writes. Add a `.memory_lock` file for write serialization. Keep JSONL + BM25 + LightRAG as-is.

**Pros:** Minimal code change, fixes critical drift, adds basic safety (idempotency, lock file), zero new dependencies.
**Cons:** JSONL is not queryable, BM25 is primitive for semantic search, no TTL enforcement.
**Risks:** File-based locking doesn't work across processes; concurrent writers will still corrupt.

### Option B — Evolutionary: SQLite + BM25 Hybrid Store
Replace JSONL with SQLite for structured memory (sessions, facts, patterns). Keep BM25 as a FTS5 index on top of SQLite. Add proper TTL enforcement via SQLite triggers. Single-writer, multi-reader pattern with WAL mode. LightRAG stays as parallel semantic layer.

**Pros:** Queryable, ACID-compliant, FTS5 is mature, TTL enforcement is native, no new external dependencies, multi-reader without locks.
**Cons:** Migration from JSONL to SQLite requires data transformation, single-writer bottleneck (acceptable for current scale).
**Risks:** SQLite WAL mode under high write load can have contention; need migration script with validation.

### Option C — Revolutionary: Qdrant Vector Database for All Memory
Replace all file-based memory with Qdrant (already has API key in `.env.example`). Semantic vectors for all memory types. BM25 as fallback hybrid. LightRAG merges into the same store.

**Pros:** True semantic retrieval, scales to millions of entries, native TTL, multi-writer safe, industry-standard.
**Cons:** Requires running Qdrant instance (or managed service), all memory code rewrites, vector embedding cost, network dependency.
**Risks:** Single point of failure if self-hosted; operational complexity; embedding model drift affects retrieval quality.

### Recommendation: **Option B (Evolutionary)**
Qdrant (Option C) is the right target state but premature — the system needs memory consolidation and idempotency before investing in vector infrastructure. SQLite + BM25 gives us ACID semantics, queryability, and TTL enforcement with zero new dependencies. Migration path: JSONL → SQLite adapter → Qdrant sync layer → eventual Qdrant primary when scale demands it.

---

## 4. Tool Layer

**Current:** `tool_runner.py` — single module that executes tools via subprocess. No sandboxing, no isolation between tool executions, no resource limits, no timeout enforcement per tool.

### Option A — Conservative: Harden tool_runner.py
Add per-tool timeouts, resource limit wrappers (ulimit), structured error handling, and a tool registry with metadata (description, required permissions, expected output schema).

**Pros:** Minimal change, immediate safety improvements, no new dependencies, backward-compatible.
**Cons:** Still no isolation (crash in one tool kills the process), no sandboxing, resource limits via ulimit are coarse.
**Risks:** Tools with access to filesystem can still corrupt state; no protection against malicious or buggy tools.

### Option B — Evolutionary: Tool Sandbox with Process Isolation
Each tool runs in its own subprocess with dedicated stdin/stdout/stderr, resource limits (CPU, memory, file descriptors), and a chroot-like filesystem sandbox. Tools declare capabilities in a registry; executor enforces boundaries.

**Pros:** Crash isolation, resource protection, security boundaries, natural fit for C4/C5 audit requirements.
**Cons:** Requires building sandbox infrastructure, filesystem sandboxing on macOS differs from Linux, per-tool overhead.
**Risks:** Sandbox escape vulnerabilities; tool compatibility issues with restricted environments.

### Option C — Revolutionary: WebAssembly Tool Runtime
Compile or wrap each tool as a WASI module. Execute in WASI sandbox with fine-grained capability permissions. Zero native code execution without explicit approval.

**Pros:** Cryptographic sandbox, portable, fine-grained permissions, industry-forward approach.
**Cons:** Most tools are Python scripts — WASI support for Python is experimental. Massive compatibility gap. Premature for current stage.
**Risks:** Tool ecosystem incompatibility, performance overhead, immature WASI Python support.

### Recommendation: **Option B (Evolutionary)**
Option C is not viable for a Python-centric tool ecosystem. Option A doesn't provide isolation. Option B gives crash isolation and resource protection with subprocess-level sandboxing — the right balance for current scale. Start with high-risk tools (filesystem, network), expand to all tools progressively.

---

## 5. Routing / Model Selection

**Current:** `router.yaml` (v4.2) defines C1-C5 tiers, model aliases, fallback chains. `models.yaml` provides 40+ model aliases. `UnifiedRouter` (Python) reads these configs and routes tasks. Routing is deterministic (config-based) but LLM calls within execution introduce non-determinism.

### Option A — Conservative: Add Determinism Controls
Keep current routing. Add `seed` parameters to all LLM calls, `temperature: 0` for routing decisions, and a routing audit log that records why each decision was made. Add consistency checker (already exists: `routing_consistency_checker.py`).

**Pros:** Zero architecture change, immediate improvement in traceability, leverages existing consistency checker.
**Cons:** Doesn't address model selection optimization, no learning from outcomes, fallback chains are static.
**Risks:** Seed-based determinism doesn't guarantee reproducibility across model versions.

### Option B — Evolutionary: Outcome-Weighted Routing
Track task outcomes (success/failure, cost, latency, quality score) per model. Use historical data to adjust routing weights. Keep YAML config as baseline, add a runtime overlay that adjusts model selection based on recent performance. Add A/B testing for model selection.

**Pros:** Self-improving routing, cost optimization over time, maintains YAML as source of truth with runtime adjustments.
**Cons:** Requires outcome tracking infrastructure, statistical significance needs sufficient sample size, cold-start problem.
**Risks:** Bad data in = bad routing out; need careful statistical handling to avoid overfitting to small samples.

### Option C — Revolutionary: LLM-Based Meta-Router
Replace config-based routing with an LLM that reads the task description, classifies it, selects the model, and builds an execution plan. The LLM acts as the router. Config becomes training data.

**Pros:** Flexible, handles novel tasks, can reason about task complexity dynamically.
**Cons:** LLM routing is itself non-deterministic (ironic), adds cost to every task, slow (LLM call before every task), harder to audit.
**Risks:** Router hallucination (misclassifying tasks), circular dependency (using LLM to choose which LLM to use), unbounded latency.

### Recommendation: **Option B (Evolutionary)**
Option C introduces the very non-determinism we're trying to reduce. Option A is table stakes but not sufficient. Option B gives us self-improving routing while keeping YAML as the deterministic baseline — best of both worlds. The existing `routing_consistency_checker.py` and `routing_vector.py` provide foundation for outcome tracking.

---

## 6. Trace Pipeline

**Current:** Append-only JSONL files. Schema v2.1 exists (`trace_metrics_materializer.py`, `trace_validator.py`) but traces may contain v1 events. No validation on write, no schema enforcement, no query capability.

### Option A — Conservative: Schema Enforcement on Write
Add `trace_validator.py` checks at write time. Reject or quarantine events that don't match v2.1 schema. Add a migration script for v1 → v2.2. Keep JSONL storage.

**Pros:** Immediate data quality improvement, minimal code change, prevents further pollution.
**Cons:** JSONL still not queryable, no real-time monitoring, migration is one-time only.
**Risks:** Quarantined events may contain critical information; migration may lose data if schemas are incompatible.

### Option B — Evolutionary: SQLite Trace Store with Schema Enforcement
Store traces in SQLite with strict schema. Add indexes on task_id, tier, model, status, cost. Real-time query capability for dashboards. Automatic v1 → v2 migration on read.

**Pros:** Queryable, indexable, supports dashboard upgrades, schema enforcement via SQLite constraints, backward-compatible migration.
**Cons:** Write performance under high volume needs monitoring, migration complexity for existing traces.
**Risks:** SQLite write contention under concurrent trace writers; needs connection pooling.

### Option C — Revolutionary: OpenTelemetry + Jaeger/Prometheus
Replace JSONL with OpenTelemetry tracing. Full distributed tracing, real-time dashboards, alerting, service maps. Industry-standard observability stack.

**Pros:** Full observability, real-time monitoring, integrates with existing monitoring tools, supports SLO tracking.
**Cons:** Massive infrastructure investment (collector, backend, dashboard), steep learning curve, overkill for single-node system.
**Risks:** Operational complexity; team needs observability expertise; cost of running Jaeger/Prometheus.

### Recommendation: **Option B (Evolutionary)**
OpenTelemetry (Option C) is the right long-term target but requires infrastructure the project doesn't have. SQLite gives us queryability and schema enforcement today. Migration path: JSONL → SQLite → OpenTelemetry exporter (when multi-node scaling arrives).

---

## 7. Eval Pipeline

**Current:** Benchmark suite in `scripts/benchmarks/`, persona eval suite, `skill_accuracy_benchmark.py`, `run_regression_suite.py`, `persona_eval.py`. Results written to files with no standardized format. No automated quality gates on eval results.

### Option A — Conservative: Standardize Eval Output Format
Define a standard eval result schema (YAML/JSON). All benchmarks output to this format. Add a summary aggregator. Keep existing benchmark scripts.

**Pros:** Minimal change, enables comparison across runs, no new dependencies.
**Cons:** Still file-based, no automated gating, no trend analysis.
**Risks:** Schema drift between eval types; aggregator becomes maintenance burden.

### Option B — Evolutionary: Automated Quality Gate Pipeline
Add eval results to SQLite (shared with trace store). Define quality thresholds per tier. Automated pass/fail gates. Trend analysis across runs. Dashboard integration.

**Pros:** Automated quality enforcement, trend visibility, integrates with trace pipeline, supports data-driven decisions.
**Cons:** Requires threshold definition effort, false positives may block legitimate work, needs calibration period.
**Risks:** Overly strict gates slow development; thresholds need regular recalibration.

### Option C — Revolutionary: Continuous Evaluation Platform
Automated eval runs on every code change. Statistical analysis of results. Regression detection. Automated rollback on quality degradation. ML-based anomaly detection.

**Pros:** Zero manual intervention, catches regressions immediately, statistical rigor, self-tuning.
**Cons:** Massive build-out, ML anomaly detection requires training data, complex debugging when platform itself has issues.
**Risks:** False negatives miss real regressions; platform complexity creates its own failure modes.

### Recommendation: **Option B (Evolutionary)**
Option C requires statistical maturity the project hasn't built yet. Option A doesn't enforce quality. Option B gives automated gates and trend analysis with the SQLite infrastructure we're already building for traces. Synergy: trace store + eval store share the same database.

---

## 8. Dashboard UI

**Current:** Bash dashboard scripts generating markdown reports. No real-time UI. No web interface. Reports are static snapshots.

### Option A — Conservative: Enhanced Markdown Reports
Improve report formatting, add sections for eval trends, trace summaries, and system health. Add cron-based report generation. Keep markdown-only output.

**Pros:** Zero new infrastructure, immediate improvement in report quality, works in any terminal.
**Cons:** Still static, no interactivity, no real-time monitoring.
**Risks:** Reports grow unwieldy; no alerting capability.

### Option B — Evolutionary: SQLite-Backed Web Dashboard
Build a lightweight web dashboard (Flask/FastAPI) that reads from SQLite (traces + evals). Real-time views: task queue, model usage, cost tracking, eval trends. No write capability — read-only dashboard.

**Pros:** Real-time visibility, interactive exploration, leverages SQLite investment, single-binary deployment.
**Cons:** New web framework dependency, requires a long-running process, basic UI effort.
**Risks:** Dashboard becomes a separate service to maintain; scope creep into full management UI.

### Option C — Revolutionary: Grafana + Prometheus Full Observability Stack
Full observability dashboard with Grafana panels. Metrics from Prometheus. Alerts via webhook. Custom panels for agent OS internals.

**Pros:** Industry-standard, powerful visualization, alerting, supports SLO tracking.
**Cons:** Requires Grafana + Prometheus infrastructure, steep learning curve, significant build-out effort.
**Risks:** Over-engineering for current scale; operational burden of running observability stack.

### Recommendation: **Option B (Evolutionary)**
Grafana (Option C) requires Prometheus metrics the system doesn't emit yet. Option B builds a lightweight web dashboard on top of SQLite — same database as traces and evals. FastAPI is already in the Python ecosystem. Migration path: markdown reports → FastAPI dashboard → Grafana exporter (when Prometheus arrives).

---

## 9. Queues / Retries / Durable Execution

**Current:** None. Tasks execute synchronously. No retry logic beyond model fallback chains. No durable execution (no state persistence between steps). No task queue.

### Option A — Conservative: In-Memory Retry + Simple Queue
Add an in-memory task queue (Python `queue.Queue`). Add retry logic with exponential backoff for transient failures. Save in-flight task state to disk periodically.

**Pros:** Simple implementation, no new dependencies, covers most failure modes.
**Cons:** In-memory queue is lost on crash, no distributed capability, limited durability.
**Risks:** Crash during task execution loses all queued work; state snapshots may be inconsistent.

### Option B — Evolutionary: SQLite-Based Durable Execution
Task queue stored in SQLite. Each step writes its state to SQLite before execution. On crash, resume from last checkpoint. Retry policies configurable per tier. Idempotency keys prevent duplicate execution.

**Pros:** Crash-safe, resumable, no new external dependencies, integrates with trace/eval SQLite, natural idempotency.
**Cons:** SQLite write contention under concurrent execution, not distributed, limited throughput.
**Risks:** Corruption under concurrent writes; needs careful transaction management.

### Option C — Revolutionary: Temporal.io / Cadence for Durable Execution
Use Temporal.io for workflow orchestration. Built-in durability, retries, cron schedules, signal handling. Industry-standard for durable execution.

**Pros:** Battle-tested durable execution, handles all edge cases, scales to distributed, built-in monitoring.
**Cons:** Requires Temporal server infrastructure, significant learning curve, vendor lock-in risk, overkill for single-node.
**Risks:** Temporal server is a separate system to operate; introduces new failure modes; team needs new skills.

### Recommendation: **Option B (Evolutionary)**
Temporal (Option C) is excellent but requires infrastructure and skills the project doesn't have. Option B builds durable execution on SQLite — same database as traces, evals, and memory. The synergy is significant: one database for all persistent state. When scale demands distributed execution, migrate to Temporal with the same workflow definitions.

---

## 10. Cost Control

**Current:** `budget_policy.yaml` defines limits per profile (`zera-standard`: $0.02/run, 6000 tokens/run). No enforcement — purely declarative. No runtime cost tracking, no alerts, no quota management.

### Option A — Conservative: Policy Enforcement at Router Level
Add cost estimation before each LLM call. Compare against budget_policy.yaml limits. Reject calls that would exceed budget. Log all costs to trace store.

**Pros:** Simple enforcement, leverages existing policy file, no new infrastructure.
**Cons:** Pre-call estimates are approximate (token count unknown before call), no running total, no quota reset logic.
**Risks:** Under-estimation leads to budget overruns; over-estimation blocks legitimate calls.

### Option B — Evolutionary: Runtime Cost Tracker with Budget Enforcement
Track actual token usage and cost per call (from API responses). Maintain running totals per profile/day/week. Enforce budgets at router level. Alert when approaching limits. Dashboard integration.

**Pros:** Accurate cost tracking, real-time enforcement, configurable alert thresholds, integrates with dashboard and trace pipeline.
**Cons:** Requires cost tracking infrastructure, API response parsing for token counts, alert system needed.
**Risks:** Cost tracking bugs could either over-block or under-block; needs careful testing.

### Option C — Revolutionary: Multi-Tenant Quota System with Pre-Paid Credits
Full quota system with pre-paid credits, usage-based billing, team-level budgets, automated recharge, API-level rate limiting.

**Pros:** Production-ready cost management, supports multi-tenant scenarios, prevents runaway costs.
**Cons:** Over-engineered for single-user system, requires billing infrastructure, significant build-out.
**Risks:** Complexity of billing system creates its own failure modes; premature optimization.

### Recommendation: **Option B (Evolutionary)**
Option C is designed for a multi-tenant SaaS, not a single-user agent OS. Option B gives accurate cost tracking and enforcement with integration into the existing trace pipeline and dashboard. The existing `budget_policy.yaml` provides the policy layer; Option B adds the enforcement layer.

---

## Cross-Cutting Concerns

| Concern | Impact | Mitigation |
|---------|--------|------------|
| `.agents/` vs `.agents/` drift | Critical — affects all subsystems | Resolve before any migration; canonical is `.agents/` |
| No idempotency on writes | High — affects memory, traces, evals | Add idempotency keys as part of SQLite migration |
| File-based shared state with no locking | High — affects all subsystems | SQLite's WAL mode solves this |
| LLM non-determinism in routing | Medium — mitigated by seed control | Outcome-weighted routing (Subsystem 5) addresses this |
| Single-threaded execution | High — blocks multi-agent patterns | Async runtime (Subsystem 1) + lanes (Subsystem 2) resolve this |

---

## Summary of Recommendations

| # | Subsystem | Recommended Option | Rationale |
|---|-----------|-------------------|-----------|
| 1 | Runtime Execution | B — Async Python Runtime | Parallelism without new infrastructure |
| 2 | Coordination Model | B — Orchestrator + Worker Lanes | Real parallelism, file-based event bus as stepping stone |
| 3 | Memory System | B — SQLite + BM25 Hybrid | ACID semantics, queryability, zero new dependencies |
| 4 | Tool Layer | B — Process Isolation Sandbox | Crash isolation, resource protection |
| 5 | Routing/Model Selection | B — Outcome-Weighted Routing | Self-improving while keeping YAML baseline |
| 6 | Trace Pipeline | B — SQLite Trace Store | Queryable, schema-enforced, backward-compatible |
| 7 | Eval Pipeline | B — Automated Quality Gates | Integrates with trace SQLite |
| 8 | Dashboard UI | B — FastAPI Web Dashboard | Real-time, read-only, leverages SQLite |
| 9 | Queues/Retries/Durable | B — SQLite Durable Execution | Crash-safe, integrates with shared SQLite |
| 10 | Cost Control | B — Runtime Cost Tracker | Accurate tracking, policy enforcement |

**Pattern:** All recommendations are Option B (Evolutionary). This is deliberate — the system needs to grow into multi-agent capabilities, not be replaced. Option A doesn't address fundamental gaps. Option C introduces infrastructure and complexity the project hasn't earned. Option B builds a cohesive platform where SQLite serves as the unified persistence layer for memory, traces, evals, queues, and cost data — with async Python and worker lanes providing the execution backbone.
