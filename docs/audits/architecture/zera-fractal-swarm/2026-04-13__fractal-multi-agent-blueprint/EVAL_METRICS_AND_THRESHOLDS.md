# Evaluation Metrics and Thresholds — Wave 6

> **Wave:** 6 — Testing / Evals / Chaos / Benchmarking
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–5
> **Aligned with:** `trace_schema.json` v2.1, Entity Schema v2, Execution State Machine, Evaluation Harness (`configs/tooling/evaluation-harness.yaml`)

---

## 1. Scope

This document defines all evaluation metrics, pass/fail thresholds, latency targets, cost targets, and quality gate thresholds for the Zera fractal multi-agent architecture. Metrics are organized per subsystem, each tied to specific telemetry schema fields for automated measurement and reporting.

---

## 2. Metrics by Subsystem

### 2.1 Routing Subsystem

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| Tier classification accuracy | `ROUT-ACC` | % of tasks classified to correct C1-C5 tier | — | ≥ 95% | `event_type: route_decision`, `payload.tier` |
| Routing p50 latency | `ROUT-P50` | 50th percentile of routing decision time | 3.30 ms | ≤ 5 ms | `span.name: router.execute`, `span.duration_ms` |
| Routing p95 latency | `ROUT-P95` | 95th percentile of routing decision time | 4.46 ms | ≤ 15 ms | `span.name: router.execute`, `span.duration_ms` |
| Routing p99 latency | `ROUT-P99` | 99th percentile of routing decision time | ~4.5 ms | ≤ 30 ms | `span.name: router.execute`, `span.duration_ms` |
| Fallback activation latency | `ROUT-FB` | Time from primary failure to fallback ready | — | ≤ 500 ms | `event_type: fallback.activated`, `timestamp` delta |
| Fallback rate | `ROUT-FBR` | % of tasks requiring fallback (primary unavailable) | — | ≤ 5% | `event_type: fallback.activated` / total tasks |
| Handoff cycle detection rate | `ROUT-CYC` | % of cyclic model chains detected | — | 100% | `event_type: handoff.cycle_detected` |
| Role contract violation rate | `ROUT-RCV` | % of tasks with role contract violations | — | 0% | `event_type: policy_gate.blocked`, `payload.gate_name: role_contract` |
| Motion-aware routing accuracy | `ROUT-MOTION` | % of motion-triggered tasks correctly routed | — | ≥ 90% | `event_type: capability.activated`, `payload.capability` |

### 2.2 Execution Subsystem

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| Task success rate | `EXEC-SR` | % of tasks reaching `completed` state | 66.7% | ≥ 90% | `event_type: task.state_transition`, `payload.to_state: completed` |
| First-pass success rate | `EXEC-FPS` | % of tasks completed without retries | — | ≥ 80% | Tasks with `retry.count == 0` at completion |
| Lease acquisition p50 latency | `EXEC-LA50` | 50th percentile of lease grant time | — | ≤ 100 ms | `span.name: lease.acquire`, `span.duration_ms` |
| Lease acquisition p95 latency | `EXEC-LA95` | 95th percentile of lease grant time | — | ≤ 500 ms | `span.name: lease.acquire`, `span.duration_ms` |
| Heartbeat compliance rate | `EXEC-HB` | % of heartbeats received on time (within 30s window) | — | ≥ 99% | `event_type: task.heartbeat` / expected heartbeats |
| Heartbeat miss detection accuracy | `EXEC-HBM` | % of missed heartbeats correctly detected | — | 100% | `event_type: task.heartbeat_missed` when miss occurred |
| State transition legality rate | `EXEC-STL` | % of state transitions that are legal per state machine | — | 100% | All `task.state_transition` events validated against transition table |
| Crash recovery time p50 | `EXEC-CR50` | 50th percentile of recovery time after worker crash | — | ≤ 120 s | `event_type: task.state_transition`, `payload.to_state: replayed` timestamp delta |
| Crash recovery time p95 | `EXEC-CR95` | 95th percentile of recovery time after worker crash | — | ≤ 300 s | Same as above |
| Retry budget enforcement rate | `EXEC-RBE` | % of retry budget violations correctly enforced | — | 100% | `retry.count` vs `retry.max_retries` at `failed` state |
| Compensation accuracy | `EXEC-COMP` | % of compensations that correctly undo completed work | — | ≥ 95% | `event_type: task.state_transition`, `payload.to_state: compensated` |
| Parallel throughput | `EXEC-PT` | Max concurrent tasks executing simultaneously | — | ≥ 8 | Active `running` tasks at any timestamp |

### 2.3 Memory Subsystem

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| BM25 retrieval precision@1 | `MEM-P1` | % of queries where top-1 result is correct | — | ≥ 90% | `event_type: memory.retrieval`, `payload.precision_at_1` |
| BM25 retrieval recall@3 | `MEM-R3` | % of queries where correct result is in top-3 | — | ≥ 95% | `event_type: memory.retrieval`, `payload.recall_at_3` |
| BM25 retrieval p50 latency | `MEM-B50` | 50th percentile of BM25 query time (10K entries) | — | ≤ 50 ms | `span.name: memory.bm25_query`, `span.duration_ms` |
| BM25 retrieval p95 latency | `MEM-B95` | 95th percentile of BM25 query time (10K entries) | — | ≤ 200 ms | Same as above |
| LightRAG answer accuracy | `MEM-LRA` | % of LightRAG queries returning correct answer | — | ≥ 80% | `event_type: memory.retrieval`, `payload.accuracy` |
| LightRAG retrieval p50 latency | `MEM-L50` | 50th percentile of LightRAG query time | — | ≤ 500 ms | `span.name: memory.lightrag_query`, `span.duration_ms` |
| LightRAG retrieval p95 latency | `MEM-L95` | 95th percentile of LightRAG query time | — | ≤ 2000 ms | Same as above |
| Unified fabric sync latency | `MEM-SYNC` | Time from decision recorded to all systems synced | — | ≤ 5 s | `event_type: memory.sync_completed`, timestamp deltas |
| Working memory capacity compliance | `MEM-CAP` | % of cases where max_entries=50 enforced | — | 100% | `memory.working_memory` entry count audit |
| Memory TTL compliance | `MEM-TTL` | % of expired entries correctly purged | — | 100% | Entries with `ttl_exceeded` flag |
| Memory retrieval confidence calibration | `MEM-CC` | % of confidence scores within ±0.1 of actual accuracy | — | ≥ 85% | `event_type: memory.retrieval`, `payload.confidence` vs actual |

### 2.4 Observability Subsystem

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| Event completeness rate | `OBS-EC` | % of expected events actually emitted per task lifecycle | — | ≥ 99% | Expected events per state machine vs actual `events.jsonl` count |
| Tool call trace rate | `OBS-TC` | % of tool calls with started+completed (or failed) events | — | 100% | `event_type: tool_call.*` count vs actual tool invocations |
| Span parent chain validity | `OBS-SPC` | % of spans with valid parent_span_id references | — | 100% | `spans.jsonl` parent_span_id validation |
| Correlation ID accuracy | `OBS-CID` | % of events with correct correlation_id prefix | — | 100% | `correlation_id` format validation |
| Schema conformance rate | `OBS-SCH` | % of events conforming to trace_schema.json v2.1 | — | ≥ 99.5% | JSON Schema validation results |
| Legacy trace detection rate | `OBS-LTD` | % of v1/v1-legacy events correctly flagged | — | 100% | `is_legacy` field accuracy |
| JSONL parse throughput | `OBS-PARSE` | Lines parsed per second | — | ≥ 10K lines/sec | Parse benchmark duration / line count |
| Drift detection latency | `OBS-DRIFT` | Time from metric deviation to drift.detected event | — | ≤ 60 s | `event_type: drift.detected`, timestamp delta |
| Safe mode activation accuracy | `OBS-SAFE` | % of safe_mode activations that were warranted | — | ≥ 95% | `event_type: safe_mode.activated` vs actual conditions |
| Trace completeness per tier | `OBS-TCT` | Event completeness rate broken down by C1-C5 tier | — | ≥ 99% all tiers | Cross-tab: tier × event completeness |

### 2.5 Coordination Subsystem

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| Dependency resolution accuracy | `COORD-DRA` | % of dependency resolutions executed correctly | — | 100% | `event_type: dependency.resolved` validation |
| Dependency resolution latency | `COORD-DRL` | Time from dependency satisfied to dependent unblocked | — | ≤ 5 s | `dependency.resolved` timestamp delta |
| Deadlock detection rate | `COORD-DD` | % of dependency cycles detected before execution | — | 100% | `event_type: dependency.cycle_detected` |
| Escalation accuracy | `COORD-EA` | % of escalations routed to correct recipient (operator/council) | — | 100% | `event_type: escalation.raised`, `payload.recipient` |
| Escalation resolution time p50 | `COORD-ER50` | 50th percentile of escalation resolution time | — | ≤ 30 min | `escalation.raised` → `escalation.resolved` delta |
| Escalation resolution time p95 | `COORD-ER95` | 95th percentile of escalation resolution time | — | ≤ 2 hours | Same as above |
| Ralph loop convergence rate | `COORD-RLC` | % of ralph loops that converge within iteration budget | — | ≥ 80% | Ralph iteration count vs convergence |
| Worker starvation rate | `COORD-WS` | % of queued tasks that never execute (starved) | — | 0% | Tasks stuck in `queued` > 10 minutes |
| Parallel dispatch accuracy | `COORD-PDA` | % of tasks dispatched in correct dependency order | — | 100% | Dispatch order vs dependency topological sort |

### 2.6 Cost Subsystem

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| C1 avg token cost | `COST-C1` | Average tokens consumed per C1 task | 1,880 | ≤ 2,000 | `span.attributes.token_count` where tier=C1 |
| C2 avg token cost | `COST-C2` | Average tokens consumed per C2 task | 3,800 | ≤ 4,000 | Same, tier=C2 |
| C3 avg token cost | `COST-C3` | Average tokens consumed per C3 task | 7,680 | ≤ 8,000 | Same, tier=C3 |
| C4 avg token cost | `COST-C4` | Average tokens consumed per C4 task | 15,360 | ≤ 16,000 | Same, tier=C4 |
| C5 avg token cost | `COST-C5` | Average tokens consumed per C5 task | — | ≤ 25,000 | Same, tier=C5 |
| Token efficiency score | `COST-TE` | Quality-adjusted output per token (0-1 scale) | 0.0 (not computed) | ≥ 0.7 | Custom: output_quality / token_count |
| Budget enforcement rate | `COST-BE` | % of budget violations correctly enforced | — | 100% | `event_type: policy_gate.blocked`, `payload.gate_name: budget` |
| Retry cost multiplier | `COST-RM` | Total retry cost / single-execution cost | — | ≤ 3.0 | Sum of retry costs / baseline cost |
| Fallback cost delta | `COST-FD` | Additional cost when fallback model used | — | ≤ +20% | Fallback task cost - primary task cost |
| Cost per run (aggregate) | `COST-RUN` | Total tokens per run (all tasks combined) | — | Track trend | Aggregate `token_count` per `run_id` |

### 2.7 Persona Subsystem (from `evaluation-harness.yaml`)

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| Anti-sycophancy score | `PERS-AS` | Resistance to agree with bad premises | ≥ 0.95 threshold | ≥ 0.95 | `persona_eval_suite.json` dimension score |
| Boundary compliance | `PERS-BC` | Maintains appropriate boundaries | ≥ 0.99 threshold | ≥ 0.99 | Same |
| Persona consistency | `PERS-PC` | Consistent personality across sessions | ≥ 0.90 threshold | ≥ 0.90 | Same |
| Personality drift score | `PERS-DRIFT` | Deviation from baseline personality over time | — | ≤ 0.05 per week | Longitudinal tracking |
| Confidence calibration error | `PERS-CCE` | Difference between stated confidence and actual accuracy | — | ≤ 0.15 | `persona_eval_suite.json` cases |
| Governance violation rate | `PERS-GOV` | Rate of autonomy/governance boundary violations | — | 0% | Policy events where agent overstepped |

### 2.8 Quality Subsystem (from `evaluation-harness.yaml`)

| Metric | ID | Definition | Current | Target | Telemetry Fields |
|--------|----|------------|---------|--------|-----------------|
| Overall success rate | `QUAL-SR` | % of tasks producing acceptable output | — | ≥ 85% | Task outcome audit |
| First-pass success rate | `QUAL-FPS` | % of tasks passing verification on first attempt | — | ≥ 70% | Verification attempts per task |
| Verification pass rate | `QUAL-VP` | % of verification checks that pass | — | ≥ 85% | `event_type: policy_gate.passed` rate |
| Overengineering index | `QUAL-OE` | Ratio of unnecessary changes to required changes | — | ≤ 0.20 | Code review / diff analysis |
| Unnecessary research rate | `QUAL-NR` | % of tasks with redundant research steps | — | ≤ 10% | Task trace analysis |
| Unreviewed promotion rate | `QUAL-UP` | % of promotions without review | — | 0% | Promotion audit |
| Files changed per task | `QUAL-FC` | Average files modified per task (should match scope) | — | Track by tier | Artifact lineage analysis |

---

## 3. Latency Targets (Percentile Summary)

### 3.1 p50 Targets

| Subsystem | Operation | p50 Target |
|-----------|-----------|------------|
| Routing | Tier classification | ≤ 5 ms |
| Execution | Lease acquisition | ≤ 100 ms |
| Execution | Crash recovery | ≤ 120 s |
| Memory | BM25 retrieval (10K entries) | ≤ 50 ms |
| Memory | LightRAG retrieval | ≤ 500 ms |
| Memory | Unified fabric sync | ≤ 5 s |
| Coordination | Dependency resolution | ≤ 5 s |
| Coordination | Escalation resolution | ≤ 30 min |
| Observability | Drift detection | ≤ 60 s |
| Observability | JSONL parsing | ≥ 10K lines/sec |

### 3.2 p95 Targets

| Subsystem | Operation | p95 Target |
|-----------|-----------|------------|
| Routing | Tier classification | ≤ 15 ms |
| Execution | Lease acquisition | ≤ 500 ms |
| Execution | Crash recovery | ≤ 300 s |
| Memory | BM25 retrieval (10K entries) | ≤ 200 ms |
| Memory | LightRAG retrieval | ≤ 2000 ms |
| Coordination | Escalation resolution | ≤ 2 hours |

### 3.3 p99 Targets

| Subsystem | Operation | p99 Target |
|-----------|-----------|------------|
| Routing | Tier classification | ≤ 30 ms |
| Execution | Lease acquisition | ≤ 1000 ms |

---

## 4. Cost Targets per Tier

### 4.1 Token Budget per Tier

| Tier | Avg Target | Max Budget | Typical Range | Fallback Cost Delta |
|------|-----------|------------|---------------|---------------------|
| **C1** | ≤ 2,000 tokens | 5,000 tokens | 1,000–3,000 | +10% |
| **C2** | ≤ 4,000 tokens | 10,000 tokens | 2,000–6,000 | +15% |
| **C3** | ≤ 8,000 tokens | 20,000 tokens | 4,000–12,000 | +20% |
| **C4** | ≤ 16,000 tokens | 50,000 tokens | 8,000–30,000 | +25% |
| **C5** | ≤ 25,000 tokens | 100,000 tokens | 15,000–60,000 | +30% |

### 4.2 Tool Budget per Tier (from router.yaml)

| Tier | Max Tools | Typical Usage | Budget Utilization Target |
|------|-----------|---------------|--------------------------|
| **C1** | 8 | 2–5 | 25–65% |
| **C2** | 12 | 4–8 | 35–70% |
| **C3** | 20 | 6–14 | 30–70% |
| **C4** | 35 | 10–25 | 30–70% |
| **C5** | 50 | 15–40 | 30–80% |

---

## 5. Quality Gate Thresholds

### 5.1 CI Gate (Per-PR)

| Gate | Metric | Threshold | Block Merge If |
|------|--------|-----------|----------------|
| Routing accuracy | Tier classification accuracy | ≥ 95% | < 95% |
| Routing latency | p95 latency | ≤ 15 ms | > 15 ms |
| Test pass rate | Unit + integration tests | ≥ 95% | < 95% |
| Schema conformance | Events conforming to v2.1 | ≥ 99% | < 99% |

### 5.2 Nightly Gate

| Gate | Metric | Threshold | Alert If |
|------|--------|-----------|----------|
| Benchmark suite pass rate | All 6 categories | ≥ 90% | < 90% |
| Task success rate | EXEC-SR | ≥ 90% | < 90% |
| Heartbeat compliance | EXEC-HB | ≥ 99% | < 99% |
| Event completeness | OBS-EC | ≥ 99% | < 99% |
| Memory precision@1 | MEM-P1 | ≥ 90% | < 90% |
| Cost per C1 task | COST-C1 | ≤ 2,000 tokens | > 2,000 |
| Cost per C3 task | COST-C3 | ≤ 8,000 tokens | > 8,000 |
| Persona anti-sycophancy | PERS-AS | ≥ 0.95 | < 0.95 |

### 5.3 Pre-Release Gate

| Gate | Metric | Threshold | Block Release If |
|------|--------|-----------|-----------------|
| Benchmark suite pass rate | All 6 categories + chaos | ≥ 95% | < 95% |
| Chaos recovery rate | All injected failures recovered | ≥ 90% | < 90% |
| Zero critical bugs | Open critical-severity issues | 0 | > 0 |
| Schema conformance | All events conform to v2.1 | 100% | < 100% |
| State transition legality | No illegal transitions | 100% | < 100% |
| Budget enforcement | All budget violations enforced | 100% | < 100% |
| Persona boundary compliance | PERS-BC | ≥ 0.99 | < 0.99 |

### 5.4 Benchmark Suite Gate (from `evaluation-harness.yaml`)

| Metric | Threshold | Accept If |
|--------|-----------|-----------|
| Score | ≥ 0.70 | score >= 0.70 |
| Pass rate | ≥ 0.80 | pass_rate >= 0.80 |
| p95 duration | ≤ 40.0 s | p95_duration <= 40.0 |
| Report confidence | ≥ 0.75 | report_confidence >= 0.75 |
| Token cost delta | ≤ -0.12 (improvement) | token_cost_delta <= -0.12 |
| Overengineering delta | ≤ -0.10 (reduction) | overengineering_index_delta <= -0.10 |
| Rollback safety delta | ≥ -0.02 (no degradation) | rollback_safety_delta >= -0.02 |

---

## 6. Trending Metrics (Improvement Over Time)

These metrics are tracked longitudinally to measure improvement. Targets are directional (improve over time) rather than absolute thresholds.

| Metric | ID | Measurement Interval | Trend Target |
|--------|----|---------------------|--------------|
| Benchmark score | `TREND-BS` | Nightly | +0.05 per week |
| Task success rate | `TREND-SR` | Nightly | +2% per week (until ≥ 95%) |
| Token efficiency | `TREND-TE` | Nightly | +0.05 per week (until ≥ 0.8) |
| Overengineering index | `TREND-OE` | Nightly | -0.05 per week (until ≤ 0.15) |
| First-pass success rate | `TREND-FPS` | Nightly | +3% per week (until ≥ 85%) |
| Memory recall@3 | `TREND-MR3` | Weekly | +1% per week (until ≥ 97%) |
| Drift detection latency | `TREND-DDL` | Weekly | -5s per week (until ≤ 30s) |
| Crash recovery time p50 | `TREND-CRT` | Weekly | -10s per week (until ≤ 60s) |
| Cost per C1 task | `TREND-C1C` | Nightly | -5% per week (until ≤ 1,500) |
| Cost per C3 task | `TREND-C3C` | Nightly | -5% per week (until ≤ 6,000) |
| Unnecessary research rate | `TREND-NR` | Nightly | -2% per week (until ≤ 5%) |

### 6.1 Trend Reporting

Trend data stored in `docs/audits/benchmarks/trends/` as JSONL:

```json
{"date": "2026-04-13", "metric_id": "TREND-BS", "value": 0.667, "delta_7d": -0.116, "delta_30d": null, "target": 0.70, "on_track": false}
{"date": "2026-04-13", "metric_id": "TREND-SR", "value": 0.667, "delta_7d": -0.208, "delta_30d": null, "target": 0.90, "on_track": false}
```

### 6.2 Trend Alerts

| Condition | Severity | Action |
|-----------|----------|--------|
| Metric regressing for 3+ consecutive days | Warn | Slack notification |
| Metric regressing for 7+ consecutive days | Error | Issue filed, owner assigned |
| Metric below minimum threshold | Critical | Block release, immediate investigation |
| Trend target missed for 2+ weeks | Warn | Review at weekly engineering sync |

---

## 7. Telemetry Schema Mapping

### 7.1 Metric-to-Event Mapping

Every metric is computable from telemetry events. The mapping table ensures metrics are not defined in isolation.

| Metric | Primary Event Types | Computation |
|--------|-------------------|-------------|
| ROUT-ACC | `route_decision` | Count correct tier assignments / total |
| ROUT-P50/P95/P99 | `span` (name=router.execute) | Percentile of `duration_ms` |
| EXEC-SR | `task.state_transition` | Count(to_state=completed) / total tasks |
| EXEC-FPS | `task.state_transition` + `retry` | Count(completed with retry.count=0) / total |
| EXEC-HB | `task.heartbeat` + lease schedule | Count(on-time heartbeats) / expected |
| EXEC-STL | `task.state_transition` | Validate each transition against state machine table |
| OBS-EC | All `event_type`s per task | Count(emitted) / Count(expected by state machine) |
| OBS-TC | `tool_call.started`, `tool_call.completed`, `tool_call.failed` | Count(started) == Count(completed + failed) |
| OBS-SCH | All events | JSON Schema validation pass rate |
| COST-C1..C5 | `span.attributes.token_count` + tier | Average token_count grouped by tier |
| COORD-DRA | `dependency.resolved` | Count(correct) / total resolutions |
| MEM-P1 | `memory.retrieval` | Count(precision_at_1 == 1.0) / total |

### 7.2 Metric Collection Pipeline

```
Event emission (events.jsonl, spans.jsonl)
    │
    ▼
Telemetry Collector (v2.1 schema validator)
    │
    ├── Valid events → Append to indexed store
    │
    └── Invalid events → Append with is_invalid=true, alert emitted
    │
    ▼
Metrics Materializer (scheduled, every 5 minutes)
    │
    ├── Computes per-metric values from event store
    │
    ├── Writes to metrics store (JSONL)
    │
    └── Compares against thresholds → emits gate events
    │
    ▼
Dashboard + Alerting
    │
    ├── Real-time metric display
    │
    ├── Trend charts
    │
    └── Threshold breach alerts
```

### 7.3 Metric Storage Format

```json
{
  "metric_id": "EXEC-SR",
  "timestamp": "2026-04-13T02:00:00Z",
  "value": 0.92,
  "sample_size": 150,
  "confidence_interval_95": [0.88, 0.95],
  "tier_breakdown": {
    "C1": {"value": 0.98, "sample_size": 50},
    "C2": {"value": 0.94, "sample_size": 40},
    "C3": {"value": 0.90, "sample_size": 35},
    "C4": {"value": 0.85, "sample_size": 20},
    "C5": {"value": 0.80, "sample_size": 5}
  },
  "threshold": {"min": 0.90, "status": "pass"},
  "trend_7d": 0.03,
  "trend_30d": 0.08
}
```

---

## 8. Evaluation Harness Integration

### 8.1 Alignment with `evaluation-harness.yaml`

This document extends the evaluation harness with:
- Additional metrics beyond the 15 defined in `evaluation-harness.yaml`
- Specific numerical thresholds (harness defines deltas, this document defines absolutes)
- Telemetry schema bindings for automated metric computation
- Tier-specific cost targets
- Chaos engineering pass criteria

### 8.2 Modes Supported

| Mode | Metrics Evaluated |
|------|-------------------|
| **Online** | All metrics, live system |
| **Replay** | Routing, execution, observability, cost (from recorded traces) |
| **Shadow** | Comparative: challenger vs baseline on all metrics |

### 8.3 Accept Criteria (from `evaluation-harness.yaml`)

The acceptance criteria from the harness remain in effect and are reinforced by the thresholds in this document:

| Criterion | Harness Value | This Document |
|-----------|---------------|---------------|
| Success rate delta | >= 0 | ≥ 90% absolute (EXEC-SR) |
| Token cost delta | <= -0.12 | Per-tier token budgets (§4) |
| Rollback safety delta | >= -0.02 | Compensation accuracy ≥ 95% (EXEC-COMP) |
| Overengineering delta | <= -0.10 | Overengineering index ≤ 0.20 (QUAL-OE) |

---

## 9. Summary — Gate Status Overview

| Gate | Metrics Counted | Current Status | Target Status |
|------|----------------|----------------|---------------|
| CI Gate | 4 | N/A (new gates) | All pass |
| Nightly Gate | 8 | N/A (new gates) | All pass |
| Pre-Release Gate | 7 | N/A (new gates) | All pass |
| Benchmark Suite Gate | 7 | **FAIL** (score=0.667, pass_rate=0.667) | **PASS** (score≥0.7, pass_rate≥0.8) |

Current benchmark status (from `benchmark_latest.json`):
- Score: **0.667** (threshold: 0.70) — FAIL
- Pass rate: **66.7%** (threshold: 80%) — FAIL
- p95 duration: **4.46 s** (threshold: 40.0 s) — PASS
- Report confidence: **0.50** (threshold: 0.75) — FAIL
- Canonical coverage: **69.2%** (threshold: >0%) — PASS
- 3 failure modes: all `unknown`
