# 09. Observability and Tracing Audit

## Maturity Verdict
- **Partially diagnosable**.
- Stronger at reliability-suite level than at agent-runtime truth level.

## What Works
- `logs/agent_traces.jsonl` is large, structured, and consistently parseable.
- Runtime selection, background jobs, approval gates, memory retrieval, persona eval, and fallback all emit some trace events.
- Reliability runner emits useful bucket-level evidence in `outputs/reliability/events.jsonl`.

## What Is Broken
1. Trace schema drift: emitted event types exceed canonical `trace_schema.json`.
2. Success-washing: `runtime_provider_selected` and `verification_result.status=ok` can coexist with no real execution/verification.
3. Trace storage split: primary logs plus nested `repos/packages/agent-os/src/logs/agent_traces.jsonl`.
4. Benchmark pipeline does not preserve clean lineage between benchmark case identity, fallback events, and final failure taxonomy.
5. Canonical schema misses live events such as `eggent_design_route_decision`, `eggent_auto_flow`, `auto_update_cycle_completed`, `runtime_recovery_attempted`, `zera_command_resolved`, and `skill_selection_metadata`.

## Missing Instrumentation
- Policy-enforced memory write decisions.
- Telemetry-schema validation failures.
- Provider readiness vs provider selection distinction.
- Benchmark case normalization diagnostics.
- Persona-mode coverage completeness.

## Production Telemetry Checklist
- Emit `selected`, `instantiated`, `started`, `verified` as distinct runtime states.
- Fail or warn when emitted events are outside canonical schema.
- Add stable `benchmark_case_id` normalization.
- Link background jobs, approval tickets, and memory writes to the same correlation lineage.

## Deepened Findings (Phase 8+)

### Schema Drift — Significant
`configs/tooling/trace_schema.json` defines the canonical schema. But the following event types are emitted and NOT in the schema:
- `eggent_design_route_decision`
- `eggent_auto_flow`
- `auto_update_cycle_completed`
- `runtime_recovery_attempted`
- `zera_command_resolved`
- `skill_selection_metadata`
- `goal_stack_updated` (221 events in traces)
- `memory_retrieval_scored` (117 events)
- `persona_eval_scored`
- `runtime_degraded_mode_entered`

The schema is not validated at emission time. Any component can emit any event type with any fields.

### Trace Storage Split
Two trace files exist:
1. `logs/agent_traces.jsonl` — primary (large, >10MB)
2. `repos/packages/agent-os/src/logs/agent_traces.jsonl` — secondary (from agent_os package tests)

The `emit_event()` function uses `AGENT_OS_TRACE_FILE` env var or defaults to `logs/agent_traces.jsonl`. There is no mechanism to ensure a single canonical trace ledger.

### Correlation IDs — Present but Underutilized
`run_id` is consistently emitted (UUID per event). However:
- Background jobs have separate `run_id` from parent task
- Memory retrieval events share `run_id` but no retrieval-to-decision linkage
- Approval tickets are emitted but not linked back to original `run_id`
- Benchmark cases have separate `case_run_id` but no normalization to canonical `case_id`

### Event Completeness — Mixed
Well-instrumented:
- Runtime provider selection (`runtime_provider_selected`)
- Zera command resolution (`zera_command_resolved`)
- Fallback events (`runtime_provider_fallback`)
- Recovery attempts (`runtime_recovery_attempted`)

Poorly instrumented:
- Pre-flight catalog update (silent fail)
- Profile context injection (no event)
- Registry workflow resolution (silent None)
- Memory write decisions (no policy events)
- Autonomy gate checks (gate doesn't exist)
- Provider health (no health check events)

### Rerun Comparability — Broken
Benchmark reruns cannot be cleanly compared because:
1. Case IDs include `::rN` suffixes, making each repeat a "new" case
2. `real-trace-*` cases are included in totals but not in expected cases
3. The analyzer counts total cases for coverage but raw IDs for expected matching
4. No baseline snapshot is preserved — only `benchmark_latest.json` exists

### Token Accounting — Present but Not Enforced
`token_usage` fields are emitted (input, output, cache_read, cache_write). But:
- No token budget enforcement exists
- No `cost_budget_usd` gate blocks execution
- Token efficiency is calculated but not used for routing decisions
- `total_cost_usd: 0.0` in all benchmark results (free models only tested)

### Diagnosability Score — 56/100
- You can trace a run from start to finish: yes
- You can tell if a run actually executed successfully: no (success-washing)
- You can identify which persona mode was active: yes (but always "plan")
- You can see memory retrieval results: yes (but no precision/recall)
- You can detect provider degradation: partially (fallback events exist)
- You can compare two runs: no (case identity normalization broken)
- You can audit persona integrity: no (no tone/sycophancy events)
- You can trace external cron impact: no (outside repo traces)

### Maturity Classification
| Dimension | Level | Notes |
|---|---|---|
| Event volume | L3 stable | 18,919+ lines, consistent structure |
| Schema compliance | L1 fragile | Schema drift, no validation |
| State distinctness | L0 chaotic | Selected/executed/verified conflated |
| Correlation | L2 workable | run_id consistent but linkage incomplete |
| Benchmark lineage | L0 chaotic | Case identity broken |
| Persona observability | L1 fragile | Only plan mode observed, no tone events |
| Memory observability | L1 fragile | Retrieval events exist, no quality metrics |
| Provider health | L0 chaotic | No health checking |
