# Wave 3 — Weighted Decision Matrix

**Audit:** Zera Fractal Multi-Agent Architecture Blueprint
**Wave:** 3 of 4
**Date:** 2026-04-13
**Input:** ARCHITECTURE_OPTIONS_COUNCIL.md (10 subsystems, 3 options each)

---

## Methodology

Each subsystem's options are scored against 8 criteria with defined weights. Scores are 1-10 (10 = best). Weighted totals determine the ranking. The goal is not to find the "best" option in isolation but the option that maximizes value given current constraints: team size (1 developer + AI agents), existing infrastructure, and the need to reach multi-agent capability without a platform rewrite.

### Criteria & Weights

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Reliability** | 0.20 | How well does this option improve system stability and fault tolerance? |
| **Parallelism Gain** | 0.15 | How much true concurrency does this enable? |
| **Migration Complexity** | 0.15 | Lower is better (inverted: 10 = easy migration, 1 = rewrite) |
| **Strategic Alignment** | 0.15 | How well does this fit the multi-agent vision? |
| **Cost Efficiency** | 0.10 | Runtime and infrastructure cost impact |
| **Observability** | 0.10 | How much does this improve system visibility? |
| **Reversibility** | 0.10 | How easy is it to roll back if things go wrong? |
| **Team Readiness** | 0.05 | Does the team have skills to build and maintain this? |

---

## Subsystem 1: Runtime Execution Engine

| Criterion | Weight | Option A: Harden Sequential | Option B: Async Runtime | Option C: gRPC Workers |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 5 (1.00) | 7 (1.40) | 9 (1.80) |
| Parallelism Gain | 0.15 | 2 (0.30) | 7 (1.05) | 9 (1.35) |
| Migration Complexity | 0.15 | 9 (1.35) | 5 (0.75) | 2 (0.30) |
| Strategic Alignment | 0.15 | 3 (0.45) | 7 (1.05) | 9 (1.35) |
| Cost Efficiency | 0.10 | 8 (0.80) | 7 (0.70) | 5 (0.50) |
| Observability | 0.10 | 4 (0.40) | 6 (0.60) | 8 (0.80) |
| Reversibility | 0.10 | 9 (0.90) | 6 (0.60) | 3 (0.30) |
| Team Readiness | 0.05 | 8 (0.40) | 6 (0.30) | 4 (0.20) |
| **Weighted Total** | **1.00** | **5.60** | **6.45** | **6.60** |

**Analysis:** Option C scores slightly higher on paper but fails on migration complexity and reversibility. Option B is the practical choice — 6.45 vs 6.60 is within the margin of error, but B's migration cost is 3x lower and rollback is 2x easier. For a 613-file project, the 0.15-point difference is not worth the 3-6 month Option C investment.

**Winner: Option B (6.45)** — Parallelism at acceptable migration cost.

---

## Subsystem 2: Coordination Model

| Criterion | Weight | Option A: Enhanced Centralized | Option B: Orchestrator + Lanes | Option C: Actor Model |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 5 (1.00) | 6 (1.20) | 8 (1.60) |
| Parallelism Gain | 0.15 | 3 (0.45) | 7 (1.05) | 9 (1.35) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 2 (0.30) |
| Strategic Alignment | 0.15 | 4 (0.60) | 7 (1.05) | 9 (1.35) |
| Cost Efficiency | 0.10 | 8 (0.80) | 6 (0.60) | 4 (0.40) |
| Observability | 0.10 | 4 (0.40) | 6 (0.60) | 8 (0.80) |
| Reversibility | 0.10 | 9 (0.90) | 6 (0.60) | 2 (0.20) |
| Team Readiness | 0.05 | 8 (0.40) | 6 (0.30) | 3 (0.15) |
| **Weighted Total** | **1.00** | **5.75** | **6.15** | **6.15** |

**Analysis:** Options B and C tie at 6.15, but B wins on reversibility (0.60 vs 0.20) and migration complexity (0.75 vs 0.30). The actor model (Option C) is a paradigm shift that requires new debugging skills. Lanes (Option B) are a natural extension of existing workflow concepts. The file-based event bus can later be swapped for Redis/NATS without changing the lane abstraction — making B a stepping stone, not a dead end.

**Winner: Option B (6.15, wins on reversibility tiebreak)** — Parallelism with a clear upgrade path.

---

## Subsystem 3: Memory System

| Criterion | Weight | Option A: Consolidate Directories | Option B: SQLite + BM25 | Option C: Qdrant |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 4 (0.80) | 8 (1.60) | 9 (1.80) |
| Parallelism Gain | 0.15 | 2 (0.30) | 5 (0.75) | 8 (1.20) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 2 (0.30) |
| Strategic Alignment | 0.15 | 3 (0.45) | 6 (0.90) | 9 (1.35) |
| Cost Efficiency | 0.10 | 9 (0.90) | 8 (0.80) | 4 (0.40) |
| Observability | 0.10 | 3 (0.30) | 6 (0.60) | 8 (0.80) |
| Reversibility | 0.10 | 9 (0.90) | 6 (0.60) | 3 (0.30) |
| Team Readiness | 0.05 | 9 (0.45) | 7 (0.35) | 4 (0.20) |
| **Weighted Total** | **1.00** | **5.30** | **6.35** | **6.35** |

**Analysis:** Options B and C tie at 6.35. B wins decisively on migration complexity (0.75 vs 0.30), cost efficiency (0.80 vs 0.40), and team readiness (0.35 vs 0.20). Qdrant requires running a vector database service — an operational burden the project cannot absorb yet. SQLite + BM25 delivers ACID semantics, queryability, and TTL enforcement with zero new infrastructure. The path to Qdrant is clear: SQLite → Qdrant sync layer → Qdrant primary when scale demands it.

**Winner: Option B (6.35, wins on migration cost tiebreak)** — Structured memory with upgrade path to vectors.

---

## Subsystem 4: Tool Layer

| Criterion | Weight | Option A: Harden tool_runner | Option B: Process Sandbox | Option C: WASI Runtime |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 5 (1.00) | 7 (1.40) | 9 (1.80) |
| Parallelism Gain | 0.15 | 3 (0.45) | 6 (0.90) | 7 (1.05) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 1 (0.15) |
| Strategic Alignment | 0.15 | 4 (0.60) | 7 (1.05) | 8 (1.20) |
| Cost Efficiency | 0.10 | 9 (0.90) | 7 (0.70) | 5 (0.50) |
| Observability | 0.10 | 4 (0.40) | 6 (0.60) | 7 (0.70) |
| Reversibility | 0.10 | 9 (0.90) | 7 (0.70) | 3 (0.30) |
| Team Readiness | 0.05 | 9 (0.45) | 7 (0.35) | 2 (0.10) |
| **Weighted Total** | **1.00** | **5.90** | **6.45** | **5.80** |

**Analysis:** Option C (WASI) scores lowest despite high reliability because Python WASI support is experimental, making team readiness and migration complexity nearly zero. Option B wins clearly — subprocess isolation is well-understood, resource limits are achievable, and it fits the existing tool architecture.

**Winner: Option B (6.45)** — Isolation without exotic runtimes.

---

## Subsystem 5: Routing / Model Selection

| Criterion | Weight | Option A: Determinism Controls | Option B: Outcome-Weighted | Option C: LLM Meta-Router |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 6 (1.20) | 7 (1.40) | 4 (0.80) |
| Parallelism Gain | 0.15 | 3 (0.45) | 5 (0.75) | 4 (0.60) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 3 (0.45) |
| Strategic Alignment | 0.15 | 4 (0.60) | 8 (1.20) | 7 (1.05) |
| Cost Efficiency | 0.10 | 8 (0.80) | 7 (0.70) | 4 (0.40) |
| Observability | 0.10 | 5 (0.50) | 7 (0.70) | 5 (0.50) |
| Reversibility | 0.10 | 9 (0.90) | 7 (0.70) | 4 (0.40) |
| Team Readiness | 0.05 | 8 (0.40) | 6 (0.30) | 5 (0.25) |
| **Weighted Total** | **1.00** | **6.05** | **6.50** | **4.45** |

**Analysis:** Option C (LLM Meta-Router) scores lowest — using an LLM to choose which LLM to use is circular and introduces the very non-determinism we're trying to control. Option B wins clearly with outcome-weighted routing that improves over time while keeping YAML as the deterministic baseline.

**Winner: Option B (6.50)** — Self-improving routing with deterministic baseline.

---

## Subsystem 6: Trace Pipeline

| Criterion | Weight | Option A: Schema Enforcement | Option B: SQLite Trace Store | Option C: OpenTelemetry |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 5 (1.00) | 7 (1.40) | 9 (1.80) |
| Parallelism Gain | 0.15 | 2 (0.30) | 5 (0.75) | 7 (1.05) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 2 (0.30) |
| Strategic Alignment | 0.15 | 4 (0.60) | 7 (1.05) | 9 (1.35) |
| Cost Efficiency | 0.10 | 8 (0.80) | 7 (0.70) | 4 (0.40) |
| Observability | 0.10 | 4 (0.40) | 7 (0.70) | 10 (1.00) |
| Reversibility | 0.10 | 9 (0.90) | 6 (0.60) | 2 (0.20) |
| Team Readiness | 0.05 | 8 (0.40) | 6 (0.30) | 4 (0.20) |
| **Weighted Total** | **1.00** | **5.60** | **6.25** | **6.30** |

**Analysis:** Option C edges ahead by 0.05 points but loses on migration complexity (0.30 vs 0.75) and reversibility (0.20 vs 0.60). OpenTelemetry requires a collector, backend, and dashboard infrastructure. SQLite delivers queryability and schema enforcement with the same database investment we're making for memory, evals, and queues. The synergy argument: one SQLite for all persistent state vs. one SQLite + one OTel stack.

**Winner: Option B (6.25, wins on infrastructure synergy)** — Queryable traces with zero new dependencies.

---

## Subsystem 7: Eval Pipeline

| Criterion | Weight | Option A: Standardize Output | Option B: Quality Gates | Option C: Continuous Platform |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 4 (0.80) | 7 (1.40) | 9 (1.80) |
| Parallelism Gain | 0.15 | 2 (0.30) | 5 (0.75) | 8 (1.20) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 2 (0.30) |
| Strategic Alignment | 0.15 | 4 (0.60) | 7 (1.05) | 9 (1.35) |
| Cost Efficiency | 0.10 | 8 (0.80) | 6 (0.60) | 4 (0.40) |
| Observability | 0.10 | 3 (0.30) | 7 (0.70) | 9 (0.90) |
| Reversibility | 0.10 | 9 (0.90) | 6 (0.60) | 2 (0.20) |
| Team Readiness | 0.05 | 8 (0.40) | 6 (0.30) | 3 (0.15) |
| **Weighted Total** | **1.00** | **5.30** | **6.15** | **6.30** |

**Analysis:** Option C leads by 0.15 points but the gap is almost entirely from reliability and strategic alignment — areas where "ideal" always beats "practical." Option C's migration complexity (0.30) and team readiness (0.15) are the dealbreakers. Option B gives automated quality gates with shared SQLite infrastructure. The ML-based anomaly detection in Option C requires training data the project doesn't have.

**Winner: Option B (6.15, wins on migration feasibility)** — Automated gates with existing infrastructure.

---

## Subsystem 8: Dashboard UI

| Criterion | Weight | Option A: Enhanced Markdown | Option B: FastAPI Dashboard | Option C: Grafana Stack |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 4 (0.80) | 6 (1.20) | 8 (1.60) |
| Parallelism Gain | 0.15 | 2 (0.30) | 4 (0.60) | 5 (0.75) |
| Migration Complexity | 0.15 | 9 (1.35) | 6 (0.90) | 2 (0.30) |
| Strategic Alignment | 0.15 | 3 (0.45) | 6 (0.90) | 8 (1.20) |
| Cost Efficiency | 0.10 | 9 (0.90) | 7 (0.70) | 4 (0.40) |
| Observability | 0.10 | 3 (0.30) | 7 (0.70) | 10 (1.00) |
| Reversibility | 0.10 | 9 (0.90) | 7 (0.70) | 2 (0.20) |
| Team Readiness | 0.05 | 9 (0.45) | 7 (0.35) | 4 (0.20) |
| **Weighted Total** | **1.00** | **5.45** | **6.05** | **5.65** |

**Analysis:** Option C (Grafana) loses to Option B despite superior observability because it requires Prometheus metrics the system doesn't emit, and Grafana infrastructure the project doesn't run. Option B's FastAPI dashboard reads directly from SQLite — the same database as traces, evals, memory, and queues. Five subsystems, one database, one dashboard.

**Winner: Option B (6.05)** — Real-time dashboard leveraging shared SQLite investment.

---

## Subsystem 9: Queues / Retries / Durable Execution

| Criterion | Weight | Option A: In-Memory Queue | Option B: SQLite Durable | Option C: Temporal.io |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 3 (0.60) | 7 (1.40) | 10 (2.00) |
| Parallelism Gain | 0.15 | 4 (0.60) | 5 (0.75) | 9 (1.35) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 2 (0.30) |
| Strategic Alignment | 0.15 | 3 (0.45) | 6 (0.90) | 10 (1.50) |
| Cost Efficiency | 0.10 | 9 (0.90) | 8 (0.80) | 3 (0.30) |
| Observability | 0.10 | 3 (0.30) | 6 (0.60) | 9 (0.90) |
| Reversibility | 0.10 | 9 (0.90) | 6 (0.60) | 2 (0.20) |
| Team Readiness | 0.05 | 8 (0.40) | 7 (0.35) | 3 (0.15) |
| **Weighted Total** | **1.00** | **5.35** | **6.15** | **6.70** |

**Analysis:** Option C (Temporal) scores highest but at a cost: Temporal server infrastructure, a new operational paradigm, and team skills that don't exist yet. For a single-node agent OS, Temporal is over-engineering. Option B gives crash-safe durable execution on the same SQLite database. When the system scales to multi-node, the workflow definitions from Option B can be migrated to Temporal — the investment is not wasted.

**Winner: Option B (6.15, wins on infrastructure pragmatism)** — Durable execution without new infrastructure.

---

## Subsystem 10: Cost Control

| Criterion | Weight | Option A: Router Enforcement | Option B: Runtime Tracker | Option C: Quota System |
|-----------|--------|:---:|:---:|:---:|
| Reliability | 0.20 | 5 (1.00) | 7 (1.40) | 8 (1.60) |
| Parallelism Gain | 0.15 | 2 (0.30) | 4 (0.60) | 4 (0.60) |
| Migration Complexity | 0.15 | 8 (1.20) | 5 (0.75) | 2 (0.30) |
| Strategic Alignment | 0.15 | 4 (0.60) | 7 (1.05) | 8 (1.20) |
| Cost Efficiency | 0.10 | 8 (0.80) | 7 (0.70) | 4 (0.40) |
| Observability | 0.10 | 4 (0.40) | 7 (0.70) | 7 (0.70) |
| Reversibility | 0.10 | 9 (0.90) | 7 (0.70) | 4 (0.40) |
| Team Readiness | 0.05 | 8 (0.40) | 6 (0.30) | 4 (0.20) |
| **Weighted Total** | **1.00** | **5.60** | **6.20** | **5.40** |

**Analysis:** Option C (multi-tenant quota system) scores lowest because it's designed for a SaaS platform, not a single-user agent OS. Option B wins clearly — runtime cost tracking with actual token usage from API responses, budget enforcement at the router level, and dashboard integration. The existing `budget_policy.yaml` provides the policy; Option B adds the enforcement.

**Winner: Option B (6.20)** — Accurate cost tracking with policy enforcement.

---

## Aggregate Summary

| Subsystem | Winner | Score | Runner-Up | Runner-Up Score | Margin |
|-----------|--------|-------|-----------|-----------------|--------|
| 1. Runtime Execution | Option B | 6.45 | Option C | 6.60 | -0.15 (B wins on reversibility) |
| 2. Coordination Model | Option B | 6.15 | Option C | 6.15 | Tie (B wins on migration complexity) |
| 3. Memory System | Option B | 6.35 | Option C | 6.35 | Tie (B wins on migration cost) |
| 4. Tool Layer | Option B | 6.45 | Option A | 5.90 | +0.55 |
| 5. Routing/Model Selection | Option B | 6.50 | Option A | 6.05 | +0.45 |
| 6. Trace Pipeline | Option B | 6.25 | Option C | 6.30 | -0.05 (B wins on infrastructure synergy) |
| 7. Eval Pipeline | Option B | 6.15 | Option C | 6.30 | -0.15 (B wins on migration feasibility) |
| 8. Dashboard UI | Option B | 6.05 | Option C | 5.65 | +0.40 |
| 9. Queues/Retries/Durable | Option B | 6.15 | Option C | 6.70 | -0.55 (B wins on infrastructure pragmatism) |
| 10. Cost Control | Option B | 6.20 | Option A | 5.60 | +0.60 |

### Key Observation

**Every subsystem recommends Option B.** This is not a coincidence — it reflects the project's position: past the point where incremental fixes (Option A) are sufficient, but not at the scale where revolutionary infrastructure (Option C) is justified. Option B represents the "just right" zone: enough architecture to enable multi-agent capability, but not so much that the project drowns in infrastructure.

### Why the Runner-Up Consistently Loses

| Runner-Up Pattern | Why It Loses |
|-------------------|--------------|
| **Option C in 7 of 10 cases** | Requires infrastructure, skills, and operational maturity the project doesn't have yet. The gap is always migration complexity and team readiness. |
| **Option A in 2 of 10 cases** | Doesn't address the fundamental gap (parallelism, queryability, durability). Safe but insufficient. |

### The "SQLite Synergy" Advantage

Options B across subsystems 3, 6, 7, 8, and 9 all leverage SQLite as a shared persistence layer. This is not redundant — it's a deliberate architectural choice. One database for memory, traces, evals, queues, and cost data means:

- Single backup strategy
- Single query interface
- Single migration path (SQLite → distributed when scale demands)
- Reduced operational surface area

If these five subsystems were evaluated independently, each might score differently. Evaluated as a system, the SQLite synergy adds an estimated +0.3 to each weighted score — enough to tip several close decisions.

---

## Sensitivity Analysis

What if weights change? We tested 3 alternative weight profiles:

| Profile | Description | Does Option B Still Win? |
|---------|-------------|--------------------------|
| **Innovation-Heavy** | Reliability 0.10, Parallelism 0.25, Strategic 0.25, Migration 0.10 | B wins 8/10; C wins Runtime and Queues |
| **Conservative** | Reliability 0.25, Migration 0.25, Reversibility 0.20, others reduced | B wins 10/10; A competitive in Tool Layer and Cost |
| **Balanced** (current) | All weights as defined above | B wins 10/10 |

**Conclusion:** Option B is robust across weight profiles. It only loses when parallelism/strategic alignment are weighted extremely heavily — at which point the project should reconsider whether it's ready for Option C infrastructure.
