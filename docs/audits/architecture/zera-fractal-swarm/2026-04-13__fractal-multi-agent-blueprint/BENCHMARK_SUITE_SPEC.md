# Benchmark Suite Specification — Wave 6

> **Wave:** 6 — Testing / Evals / Chaos / Benchmarking
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–5
> **Aligned with:** `trace_schema.json` v2.1, Entity Schema v2, Execution State Machine, Telemetry Schema v2.1

---

## 1. Scope

This document defines the complete benchmark suite for the Zera fractal multi-agent architecture. It covers six benchmark categories, test case specifications, pass/fail thresholds, baseline metrics (current state from `benchmark_latest.json` and `benchmark_routing.py`), and target metrics after migration to the fractal execution model.

All benchmarks produce output conforming to the telemetry schema v2.1: every benchmark run emits `event`, `span`, and `artifact` records with `correlation_id`, `run_id`, and entity hierarchy fields.

---

## 2. Benchmark Categories

| Category | ID | Subsystem Under Test | Key Metrics |
|----------|----|---------------------|-------------|
| **Routing** | `BENCH-ROUTING` | Task classifier, model selector, CLI router | Latency, accuracy, fallback rate |
| **Execution** | `BENCH-EXECUTION` | Lease manager, state machine, worker pool | Throughput, success rate, heartbeat compliance |
| **Memory** | `BENCH-MEMORY` | BM25 retrieval, LightRAG, unified fabric | Hit rate, retrieval latency, recall@k |
| **Observability** | `BENCH-OBSERVABILITY` | Trace collector, event emitter, span recorder | Completeness, schema conformance, parse rate |
| **Coordination** | `BENCH-COORDINATION` | Dependency resolver, parallel dispatcher, escalation handler | Deadlock rate, resolution time, escalation accuracy |
| **Cost** | `BENCH-COST` | Token accounting, model selection, budget enforcement | Cost per tier, token efficiency, budget violation rate |

---

## 3. Test Case Specifications

### 3.1 BENCH-ROUTING

| Case ID | Name | Input | Expected Output | Metric |
|---------|------|-------|-----------------|--------|
| `RT-001` | Tier classification accuracy (C1) | T×C1 task (1 file, <50 lines) | Tier=C1, path=fast, max_tools=8 | Classification accuracy |
| `RT-002` | Tier classification accuracy (C2) | T×C2 task (1-3 files, local logic) | Tier=C2, path=fast, max_tools=12 | Classification accuracy |
| `RT-003` | Tier classification accuracy (C3) | T×C3 task (3-10 files, tests required) | Tier=C3, path=quality, ralph_loop=3 | Classification accuracy |
| `RT-004` | Tier classification accuracy (C4) | T×C4 task (cross-domain, API changes) | Tier=C4, path=swarm, human_audit=true | Classification accuracy |
| `RT-005` | Tier classification accuracy (C5) | T×C5 task (security, payments) | Tier=C5, path=swarm, council_required=true | Classification accuracy |
| `RT-006` | Routing latency — p50 | 1000 requests, uniform T×C distribution | p50 ≤ target | p50 latency (ms) |
| `RT-007` | Routing latency — p95 | 1000 requests, uniform T×C distribution | p95 ≤ target | p95 latency (ms) |
| `RT-008` | Routing latency — p99 | 1000 requests, uniform T×C distribution | p99 ≤ target | p99 latency (ms) |
| `RT-009` | Fallback chain activation | Primary model unavailable | Fallback triggered within 500ms | Fallback latency |
| `RT-010` | Motion-aware routing | Task with GSAP trigger keywords | GSAP capability activated, workflow set | Routing accuracy |
| `RT-011` | Handoff safeguard — cycle detection | Crafted cyclic model chain | Cycle detected, routing aborted | Detection rate |
| `RT-012` | Role contract enforcement | Task requiring specific agent role | Role validated, conflict checked | Enforcement rate |

**Baseline (from `benchmark_routing.py` and `benchmark_latest.json`):**
- p50 routing latency: **3.30 ms** (100 iterations × 35 T×C combos)
- p95 routing latency: **4.46 ms**
- p99 routing latency: **~4.5 ms** (estimated from tail)
- Benchmark suite pass rate: **66.7%** (6/9 cases)
- Benchmark suite score: **0.667**
- Gate status: **FAIL** (score < 0.7, pass_rate < 0.8, report_confidence < 0.75)

**Targets (post-migration):**
- p50 routing latency: **≤ 5 ms** (fractal adds lease lookup overhead)
- p95 routing latency: **≤ 15 ms**
- p99 routing latency: **≤ 30 ms**
- Tier classification accuracy: **≥ 95%**
- Fallback activation: **≤ 500 ms**
- Benchmark suite pass rate: **≥ 90%**

### 3.2 BENCH-EXECUTION

| Case ID | Name | Input | Expected Output | Metric |
|---------|------|-------|-----------------|--------|
| `EX-001` | Lease acquisition latency | 100 tasks, ready state | Lease granted in ≤ 100ms | p50 lease latency |
| `EX-002` | Lease expiry enforcement | Task with 60s lease, no heartbeats | Lease revoked at 90s, task failed | Expiry accuracy (±5s) |
| `EX-003` | Heartbeat protocol — normal | Worker sends heartbeat every 30s | Lease extended, no warnings | Heartbeat success rate |
| `EX-004` | Heartbeat protocol — 1 miss | Worker misses 1 heartbeat (60s overdue) | Warning logged, lease preserved | Warning accuracy |
| `EX-005` | Heartbeat protocol — 2 misses | Worker misses 2 heartbeats (90s overdue) | Lease revoked, task failed → replayed | Revocation accuracy |
| `EX-006` | State transition correctness | Execute full state machine DAG | All 22 transitions valid per guard rules | Transition accuracy |
| `EX-007` | Parallel execution throughput | 10 independent tasks, no dependencies | All 10 run concurrently, complete within budget | Concurrency rate |
| `EX-008` | Dependency-ordered execution | 5 tasks with DAG: A→[B,C]→[D,E]→F | Execution order respects dependencies | Dependency compliance |
| `EX-009` | Crash recovery — running task | Kill worker mid-task, lease valid | Task replayed on new worker within 120s | Recovery time |
| `EX-010` | Crash recovery — expired lease | Kill worker, let lease expire, restart | Task failed → replayed → ready | Recovery accuracy |
| `EX-011` | Compensation flow | Task completed, then compensation triggered | Work undone, dependents re-evaluated | Compensation accuracy |
| `EX-012` | Retry budget enforcement | Task fails 4 times (max_retries=3) | Task escalated (C4/C5) or failed (C1-C3) | Budget accuracy |

**Baseline:** No dedicated execution benchmarks exist. Current `benchmark_latest.json` covers routing and persona, not execution state machine.

**Targets (post-migration):**
- Lease acquisition p50: **≤ 100 ms**
- Lease expiry accuracy: **±5 seconds**
- Heartbeat compliance: **100%** (no false positives)
- State transition accuracy: **100%** (no illegal transitions)
- Parallel throughput: **≥ 8 concurrent tasks** (C5 allows up to 50 tools, C3 allows 20)
- Crash recovery time: **≤ 120 seconds**
- Retry budget enforcement: **100%**

### 3.3 BENCH-MEMORY

| Case ID | Name | Input | Expected Output | Metric |
|---------|------|-------|-----------------|--------|
| `MEM-001` | BM25 retrieval — exact match | Query matching known memory entry | Top-1 result is correct entry | Precision@1 |
| `MEM-002` | BM25 retrieval — semantic match | Query semantically similar to entry | Correct entry in top-3 | Recall@3 |
| `MEM-003` | BM25 retrieval latency | 1000 queries against 10K entries | p50 ≤ target | p50 retrieval latency |
| `MEM-004` | LightRAG retrieval — graph traversal | Query requiring multi-hop reasoning | Correct answer assembled from graph | Answer accuracy |
| `MEM-005` | LightRAG retrieval latency | 100 queries | p50 ≤ target | p50 retrieval latency |
| `MEM-006` | Unified fabric sync — design to BM25 | New design decision recorded | BM25 index updated within TTL | Sync latency |
| `MEM-007` | Unified fabric sync — design to LightRAG | New design decision recorded | LightRAG graph updated within TTL | Sync latency |
| `MEM-008` | Memory TTL expiry | Entry with 24h TTL, wait 25h | Entry no longer retrievable | TTL accuracy |
| `MEM-009` | Working memory capacity | Insert 60 entries (max=50) | Oldest entries evicted, 50 retained | Capacity enforcement |
| `MEM-010` | Memory retrieval confidence | Query with ambiguous match | Confidence score returned, min_confidence=0.3 enforced | Confidence accuracy |

**Baseline:** No dedicated memory benchmarks. `benchmark_latest.json` includes `bench-memory-retrieval` case with pass status=ok, duration=3.834s.

**Targets (post-migration):**
- BM25 precision@1: **≥ 90%**
- BM25 recall@3: **≥ 95%**
- BM25 retrieval p50: **≤ 50 ms** (10K entries)
- LightRAG answer accuracy: **≥ 80%**
- Unified fabric sync latency: **≤ 5 seconds**
- TTL accuracy: **100%**
- Working memory capacity enforcement: **100%**

### 3.4 BENCH-OBSERVABILITY

| Case ID | Name | Input | Expected Output | Metric |
|---------|------|-------|-----------------|--------|
| `OBS-001` | Trace completeness — task lifecycle | Execute single task from queued→completed | All state transition events emitted | Event completeness rate |
| `OBS-002` | Trace completeness — tool calls | Task makes 5 tool calls | 5× tool_call.started + 5× tool_call.completed emitted | Tool call trace rate |
| `OBS-003` | Span-parent chain integrity | Execute task with 3 subtasks | All spans have valid parent_span_id or null (root) | Parent chain validity |
| `OBS-004` | Correlation ID propagation | Execute full hierarchy (run→wave→workflow→task→subtask→action→tool_call) | All events have correct correlation_id prefix | Correlation accuracy |
| `OBS-005` | Schema conformance — v2.1 events | 1000 emitted events | 100% validate against trace_schema.json v2.1 | Schema conformance rate |
| `OBS-006` | Legacy trace detection | Mixed v1/v2 trace file | All legacy events flagged with is_legacy | Detection rate |
| `OBS-007` | JSONL parse rate | 100K-line events.jsonl | Parse completes within budget | Parse throughput (lines/sec) |
| `OBS-008` | Event ordering | Concurrent events from multiple workers | Events timestamped and ordered correctly | Ordering accuracy |
| `OBS-009` | Drift detection | Metric deviates >10% from baseline | drift.detected event emitted within 60s | Detection latency |
| `OBS-010` | Safe mode activation | Policy violation cascade | safe_mode.activated event emitted | Activation accuracy |

**Baseline:** `benchmark_latest.json` shows trace coverage as part of suite diagnostics. Current `test_trace_schema_mirror.py`, `test_trace_validator.py`, `test_observability_trace_v2.py` exist but no dedicated benchmarks. p95 trace parse duration in existing suite: **4.46 ms**.

**Targets (post-migration):**
- Event completeness rate: **≥ 99%** (all 40+ event types covered)
- Tool call trace rate: **100%**
- Parent chain validity: **100%**
- Correlation accuracy: **100%**
- Schema conformance: **≥ 99.5%**
- Legacy detection: **100%**
- JSONL parse rate: **≥ 10K lines/sec** (per TRACE_VISUALIZATION_SPEC.md §6.4)
- Drift detection latency: **≤ 60 seconds**

### 3.5 BENCH-COORDINATION

| Case ID | Name | Input | Expected Output | Metric |
|---------|------|-------|-----------------|--------|
| `COORD-001` | Dependency resolution — simple | Task B depends on Task A | B waits for A, proceeds after A completes | Resolution accuracy |
| `COORD-002` | Dependency resolution — diamond | A→[B,C]→D | D waits for both B and C | Resolution accuracy |
| `COORD-003` | Dependency resolution — cycle detection | Crafted cyclic dependency graph | Cycle detected, error emitted, no deadlock | Detection rate |
| `COORD-004` | Parallel dispatch — no deps | 10 independent tasks | All dispatched simultaneously | Dispatch latency |
| `COORD-005` | Parallel dispatch — with deps | 10 tasks, 3-level DAG | Tasks dispatched as dependencies resolve | Staged dispatch accuracy |
| `COORD-006` | Escalation routing — C4 | C4 task fails, non-recoverable | Escalated state, operator notified | Escalation accuracy |
| `COORD-007` | Escalation routing — C5 | C5 task fails, requires council | Escalated state, council notified | Escalation accuracy |
| `COORD-008` | Escalation resolution | Escalated task, operator approves | Task transitions to ready, re-executes | Resolution accuracy |
| `COORD-009` | Escalation abandonment | Escalated task, operator abandons | Task transitions to failed, terminal | Abandonment accuracy |
| `COORD-010` | Ralph loop convergence | C3 task, score=0.7, threshold=0.85 | Loop runs up to 3 iterations, converges or escalates | Convergence rate |

**Baseline:** `benchmark_latest.json` includes `bench-stop-signal` (ok, 3.871s), `bench-approval-gate` (ok, 3.257s), `bench-zera-recovery` (error, 3.86s). No dedicated coordination benchmarks.

**Targets (post-migration):**
- Dependency resolution accuracy: **100%**
- Cycle detection rate: **100%**
- Parallel dispatch latency: **≤ 200 ms** (10 tasks)
- Escalation accuracy: **100%**
- Ralph loop convergence rate: **≥ 80%** (within iteration budget)

### 3.6 BENCH-COST

| Case ID | Name | Input | Expected Output | Metric |
|---------|------|-------|-----------------|--------|
| `COST-001` | Token accounting — C1 | C1 task execution | Token count recorded, within budget | Accounting accuracy |
| `COST-002` | Token accounting — C5 | C5 task execution | Token count recorded, within budget | Accounting accuracy |
| `COST-003` | Budget enforcement — exceeded | Task exceeds token budget | Task terminated, budget_exceeded event | Enforcement rate |
| `COST-004` | Model cost tracking | 100 tasks across 5 model tiers | Per-tier cost aggregated accurately | Cost accuracy |
| `COST-005` | Cost per tier — C1 | 100 C1 tasks | Average cost ≤ target | Avg cost per task |
| `COST-006` | Cost per tier — C3 | 100 C3 tasks | Average cost ≤ target | Avg cost per task |
| `COST-007` | Cost per tier — C5 | 100 C5 tasks | Average cost ≤ target | Avg cost per task |
| `COST-008` | Token efficiency | Compare output quality vs tokens used | Efficiency score calculated | Efficiency score |
| `COST-009` | Fallback cost impact | Primary model fails, fallback used | Cost delta recorded | Fallback cost delta |
| `COST-010` | Retry cost overhead | Task retries 3 times | Total retry cost recorded | Retry cost multiplier |

**Baseline (from `benchmark_latest.json` per-case token data):**
- C1 task: **1,880 tokens** (1,440 in + 440 out)
- C2 task: **3,800 tokens** (2,700 in + 1,100 out)
- C3 task: **7,680 tokens** (5,040 in + 2,640 out)
- C4 task: **15,360 tokens** (10,080 in + 5,280 out)
- Token efficiency: **0.0** (not computed)

**Targets (post-migration):**
- C1 avg cost: **≤ 2,000 tokens**
- C2 avg cost: **≤ 4,000 tokens**
- C3 avg cost: **≤ 8,000 tokens**
- C4 avg cost: **≤ 16,000 tokens**
- C5 avg cost: **≤ 25,000 tokens**
- Token efficiency: **≥ 0.7** (quality-adjusted)
- Budget enforcement: **100%**
- Retry cost overhead: **≤ 3× single-execution cost**

---

## 4. Benchmark Execution Protocol

### 4.1 Execution Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Online** | Run against live system | Pre-merge validation, nightly |
| **Replay** | Run against recorded traces | Regression testing, historical comparison |
| **Shadow** | Run challenger alongside baseline | Model/policy comparison |

### 4.2 Execution Steps

```
1. Initialize benchmark harness
   ├── Load test cases from suite definition
   ├── Connect to telemetry collector (v2.1 schema)
   └── Reset metrics store

2. For each benchmark category:
   ├── Execute test cases (sequential within category)
   ├── Record span for each case (start/end/duration/status)
   ├── Emit events for each assertion
   └── Collect artifacts (logs, traces, outputs)

3. Aggregate results
   ├── Calculate percentiles (p50, p95, p99)
   ├── Compare against thresholds
   ├── Generate pass/fail report
   └── Compute trend deltas (vs previous run)

4. Publish artifacts
   ├── Write results to docs/audits/benchmarks/
   ├── Update benchmark_latest.json
   ├── Emit benchmark_complete event
   └── Trigger CI gate (pass/fail)
```

### 4.3 Telemetry Schema Alignment

Every benchmark execution produces telemetry conforming to the v2.1 schema:

| Telemetry Field | Benchmark Mapping |
|-----------------|-------------------|
| `run_id` | `bench_{YYYYMMDDHHMMSS}{seq}` |
| `correlation_id` | `corr_{run_id}_{category}_{case_id}` |
| `event_type` | `benchmark.case_started`, `benchmark.case_completed`, `benchmark.case_failed`, `benchmark.suite_completed` |
| `entity_type` | `benchmark_case`, `benchmark_suite` |
| `span.name` | `{category}.execute` (e.g., `routing.execute`, `execution.execute`) |
| `span.attributes` | `{tier, model, tools_used, attempt_count, token_count}` |
| `artifact` | Benchmark results JSON, trace captures, performance profiles |

See `trace_schema.json` v2.1 for full field definitions. Event types `benchmark.*` are registered in the event type catalog (Entity Schema §3.3).

### 4.4 Execution Schedule

| Frequency | Scope | Trigger |
|-----------|-------|---------|
| **Per-PR** | BENCH-ROUTING (RT-001 through RT-012) | PR created or updated |
| **Nightly** | All 6 categories, full suite | Cron 02:00 UTC |
| **Pre-release** | All categories + chaos injection (see FAILURE_INJECTION_PLAN.md) | Release candidate created |
| **On-demand** | Any category | `make benchmark CATEGORY=execution` |

---

## 5. Benchmark Infrastructure

### 5.1 Existing Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Routing benchmark script | `repos/packages/agent-os/benchmark_routing.py` | Active, covers RT-001 to RT-008 |
| Benchmark results (latest) | `docs/ki/benchmark_latest.json` | Active, score=0.667 |
| Benchmark anomalies | `docs/ki/benchmark_anomalies.json` | Active |
| Benchmark report | `docs/ki/benchmark_latest.md` | Active |
| Runtime benchmark matrix | `configs/tooling/runtime_benchmark_matrix.json` | Active |
| Evaluation harness config | `configs/tooling/evaluation-harness.yaml` | Active, 11 metrics |
| Persona eval suite | `configs/tooling/persona_eval_suite.json` | Active, 4 cases |
| Test suite | `repos/packages/agent-os/tests/` | 101 test files |

### 5.2 New Artifacts Required

| Artifact | Path | Priority |
|----------|------|----------|
| Execution benchmark script | `repos/packages/agent-os/benchmark_execution.py` | P0 |
| Memory benchmark script | `repos/packages/agent-os/benchmark_memory.py` | P0 |
| Observability benchmark script | `repos/packages/agent-os/benchmark_observability.py` | P0 |
| Coordination benchmark script | `repos/packages/agent-os/benchmark_coordination.py` | P0 |
| Cost benchmark script | `repos/packages/agent-os/benchmark_cost.py` | P0 |
| Chaos injection scripts | `scripts/chaos/` | P1 |
| Benchmark suite orchestrator | `repos/packages/agent-os/scripts/benchmark_runner.py` | P0 |

### 5.3 Benchmark Runner CLI

```bash
# Run full suite
python3 repos/packages/agent-os/scripts/benchmark_runner.py --all

# Run specific category
python3 repos/packages/agent-os/scripts/benchmark_runner.py --category routing

# Run specific cases
python3 repos/packages/agent-os/scripts/benchmark_runner.py --cases RT-001,RT-006,RT-007

# Compare against baseline
python3 repos/packages/agent-os/scripts/benchmark_runner.py --all --baseline docs/ki/benchmark_latest.json

# Output to specific file
python3 repos/packages/agent-os/scripts/benchmark_runner.py --all --output docs/audits/benchmarks/2026-04-13_full_suite.json
```

---

## 6. Summary Table

| Category | Cases | Baseline Pass Rate | Target Pass Rate | Priority |
|----------|-------|--------------------|------------------|----------|
| BENCH-ROUTING | 12 | 66.7% (suite-wide) | ≥ 90% | P0 |
| BENCH-EXECUTION | 12 | N/A (no baseline) | ≥ 95% | P0 |
| BENCH-MEMORY | 10 | Partial (1 case) | ≥ 90% | P0 |
| BENCH-OBSERVABILITY | 10 | Partial (trace tests) | ≥ 99% | P0 |
| BENCH-COORDINATION | 10 | Partial (2 cases) | ≥ 95% | P0 |
| BENCH-COST | 10 | Token data exists | ≥ 95% | P1 |
| **Total** | **64** | **66.7%** | **≥ 92%** | — |
