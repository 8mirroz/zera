# Migration Plan — Zera Fractal Multi-Agent Blueprint

**Audit Wave:** 7 — Final Recommendation + Migration Package
**Date:** 2026-04-13
**Total estimated duration:** 8–12 weeks

---

## Overview

The migration proceeds in 6 sequential phases. Each phase has explicit deliverables, success criteria, and a rollback plan. Phases are sequential because later phases depend on outputs of earlier ones, but some work within a phase can be parallelized (see `IMPLEMENTATION_BACKLOG.md` for task-level parallelism).

```
Phase 1        Phase 2        Phase 3        Phase 4        Phase 5        Phase 6
Instrumen-  →  Hardening   →  Contracts   →  Dashboard   →  Eval Fly-   →  Adaptive
tation         (structural)   + Leases       + Replay       wheel          Optimize
1–2 weeks      1–2 weeks      2–3 weeks      1–2 weeks      2 weeks        2–3 weeks
```

---

## Phase 1: Instrumentation

**Duration:** 1–2 weeks
**Dependency:** None (starting point)

### Scope

Wire structured observability into every code path in the orchestrator, router, and agent execution loop. This is the foundation for all subsequent phases.

### Deliverables

| ID | Deliverable | Description |
|----|-------------|-------------|
| P1-1 | Trace emitter | Core library that emits structured trace events (start, end, error, tool call, retry) |
| P1-2 | Orchestrator instrumentation | All paths in the orchestrator emit traces via P1-1 |
| P1-3 | Router instrumentation | Task classification (C1–C5), model selection, fallback events traced |
| P1-4 | Agent execution instrumentation | Subagent spawn, completion, timeout, error traced |
| P1-5 | Trace sink | Storage backend for traces (file-based initially, upgradeable to Qdrant/SQLite) |
| P1-6 | Trace ID propagation | Correlation IDs flow through parent→child task chains |
| P1-7 | CLI trace viewer | `swarmctl trace <task_id>` to inspect a single task trace |

### Success Criteria

- [ ] 100% of orchestrator code paths emit at least one trace event
- [ ] No silent fallbacks — every fallback logs a trace with `level: warning` or higher
- [ ] Trace IDs propagate through at least 3 levels of nested tasks
- [ ] `swarmctl trace <task_id>` returns a readable trace for any completed task
- [ ] Trace storage survives process restart (persistent sink)

### Rollback Plan

If instrumentation introduces >10% latency overhead:
1. Disable trace emission via feature flag in `configs/orchestrator/router.yaml`: `observability.enabled: false`
2. Instrumentation code remains (for future re-enablement) but becomes no-op
3. Proceed to Phase 2 without traces (Phase 4 will be blocked until this is resolved)

---

## Phase 2: Hardening

**Duration:** 1–2 weeks
**Dependency:** Phase 1 complete (need traces to validate fixes)

### Scope

Resolve all structural issues identified in Wave 0. This is cleanup work that must happen before introducing new architecture.

### Deliverables

| ID | Deliverable | Description |
|----|-------------|-------------|
| P2-1 | Path canonicalization | Resolve `.agent/.agents` mismatch; single source of truth |
| P2-2 | Duplicate script removal | Audit `scripts/` directory; remove or consolidate duplicates |
| P2-3 | Missing path creation | Create all directories referenced by code but not present on disk |
| P2-4 | Silent fallback elimination | Replace all silent fallbacks with explicit error + trace |
| P2-5 | Config validation | Schema-validate all YAML configs at startup; fail fast on invalid config |
| P2-6 | Dependency audit | Audit `package.json`, `requirements.txt`, `pyproject.toml` for unused deps |
| P2-7 | Error message standardization | All error messages follow format: `[component] action failed: reason. Suggested fix: hint` |

### Success Criteria

- [ ] Zero `.agent/.agents` path references — single canonical path
- [ ] Zero duplicate scripts (verified by `swarmctl audit --duplicates`)
- [ ] Zero silent fallbacks in production code paths
- [ ] All configs validated at startup (invalid config → process exits with message)
- [ ] All error messages follow standard format

### Rollback Plan

Hardening changes are mostly additive (fixing broken things). If a fix introduces regression:
1. Revert the specific commit (each deliverable is a separate PR)
2. Re-run Phase 1 trace checks to confirm no regression
3. Fix and re-submit

---

## Phase 3: Contracts + Leases

**Duration:** 2–3 weeks
**Dependency:** Phase 2 complete (clean codebase before adding new abstractions)

### Scope

Introduce the minimum viable protocol for safe subagent delegation: task contracts and lease management. This is the most complex phase.

### Deliverables

| ID | Deliverable | Description |
|----|-------------|-------------|
| P3-1 | Task contract schema | YAML-defined contracts: input schema, output schema, timeout, retry policy |
| P3-2 | Contract validator | Validates that subagent output matches the contract's output schema |
| P3-3 | Lease manager | Issues, tracks, and expires leases for subagent execution |
| P3-4 | Lease expiration handler | On lease expiry: kill subagent, emit trace, retry or escalate |
| P3-5 | Delegation router | Routes subtasks to subagents with contract + lease attached |
| P3-6 | RALPH convergence adapter | Wraps RALPH as a convergence checker: takes outputs, scores against contract |
| P3-7 | Fractal decomposition engine (MVP) | Decomposes C3+ tasks into subtasks; assigns tier to each subtask |
| P3-8 | Compat path layer | Routes tasks through old or new path based on feature flag |

### Success Criteria

- [ ] Contract schema supports at least: input (JSON Schema), output (JSON Schema), timeout (seconds), retries (int)
- [ ] Contract validator catches schema mismatches and emits structured error
- [ ] Lease manager handles 10+ concurrent leases without collision
- [ ] Lease expiration triggers within 5 seconds of expiry
- [ ] Delegation router successfully delegates a C3 task to 2 subagents
- [ ] RALPH convergence adapter scores subagent output as pass/fail
- [ ] Compat path layer routes C1/C2 through old path, C3+ through new path

### Rollback Plan

If contracts or leases introduce instability:
1. Set `contracts.enabled: false` in router config — all tasks route through compat (old) path
2. Contract and lease code remains but is bypassed
3. Phase 4 (dashboard) can proceed with old-path traces; Phase 5 blocked until contracts work

---

## Phase 4: Dashboard + Replay

**Duration:** 1–2 weeks
**Dependency:** Phase 1 (traces) + Phase 3 (contracts working in production)

### Scope

Ship the observability dashboard designed in Wave 5, plus trace replay for regression testing.

### Deliverables

| ID | Deliverable | Description |
|----|-------------|-------------|
| P4-1 | Dashboard shell | Premium UI shell with dark mode, glassmorphism (per Design DNA) |
| P4-2 | Trace visualization | Timeline view of task traces with parent→child relationships |
| P4-3 | Kanban view | Tasks organized by state (13 states from Wave 4) on kanban board |
| P4-4 | Timeline view | Gantt-style view of task execution over time |
| P4-5 | Cognitive motion signals | Visual indicators for agent activity: thinking, waiting, blocked, completing |
| P4-6 | Trace replay engine | Replay any completed task trace; compare with expected output |
| P4-7 | Regression detector | Compare two traces; flag differences in tool calls, timing, output |
| P4-8 | Real-time stream | WebSocket-based live update of task states |

### Success Criteria

- [ ] Dashboard renders within 2 seconds for 1000+ traces
- [ ] Kanban view reflects current state of all active tasks
- [ ] Trace replay produces identical output to original execution (deterministic traces)
- [ ] Regression detector flags all tool-call differences between two traces
- [ ] Cognitive motion signals update within 500ms of state change

### Rollback Plan

Dashboard is a read-only consumer of traces. If it breaks:
1. Disable dashboard server — does not affect agent execution
2. Trace replay remains available via CLI (`swarmctl replay <task_id>`)
3. Fix and redeploy; no data loss

---

## Phase 5: Eval Flywheel

**Duration:** 2 weeks
**Dependency:** Phase 3 (contracts) + Phase 4 (dashboard for visualization)

### Scope

Implement the benchmark suite from Wave 6 with automated quality gates. This creates a feedback loop that continuously measures and improves agent performance.

### Deliverables

| ID | Deliverable | Description |
|----|-------------|-------------|
| P5-1 | Benchmark task suite | 50+ representative tasks across all C1–C5 tiers |
| P5-2 | Chaos injection framework | Inject failures (timeout, OOM, network error) during benchmark runs |
| P5-3 | Eval metrics calculator | Compute: success rate, latency, tool efficiency, output quality |
| P5-4 | Quality gate runner | Run benchmarks on every orchestrator change; block merge if metrics regress |
| P5-5 | Benchmark dashboard | Visualize benchmark results over time; trend analysis |
| P5-6 | Automated report generator | Generate weekly performance report; post to team channel |

### Success Criteria

- [ ] Benchmark suite runs in <30 minutes for full suite
- [ ] Chaos injection causes <5% false-positive failures (flaky tests)
- [ ] Quality gates block merges that regress success rate by >2%
- [ ] Benchmark results are reproducible (same input → same score ±1%)
- [ ] Weekly reports auto-generate and publish

### Rollback Plan

Eval flywheel is additive. If it causes issues:
1. Disable quality gate enforcement — benchmarks still run but don't block merges
2. Chaos injection disabled by default; enable explicitly
3. Benchmark dashboard can be taken down without affecting production

---

## Phase 6: Adaptive Optimization

**Duration:** 2–3 weeks
**Dependency:** Phase 5 (eval flywheel providing baseline metrics)

### Scope

Enable runtime task decomposition and dynamic swarm sizing. This is the final phase that delivers the full fractal multi-agent vision.

### Deliverables

| ID | Deliverable | Description |
|----|-------------|-------------|
| P6-1 | Runtime complexity analyzer | Analyzes incoming task; estimates complexity score |
| P6-2 | Dynamic decomposition engine | Decomposes tasks at runtime based on complexity (not pre-configured rules) |
| P6-3 | Dynamic swarm sizer | Adjusts concurrency based on available resources and task priority |
| P6-4 | Resource budget manager | Allocates CPU/memory/token budgets per subagent based on tier |
| P6-5 | Adaptive retry policy | Retry count adapts based on historical success rate for similar tasks |
| P6-6 | Performance tuner | Uses benchmark data (Phase 5) to optimize model selection per task type |
| P6-7 | Compat path sunset | Remove old routing path; all tasks use fractal orchestration |

### Success Criteria

- [ ] Runtime analyzer correctly classifies task complexity for 90%+ of benchmark tasks
- [ ] Dynamic decomposition produces valid subtasks (validated by contract checker)
- [ ] Swarm sizer respects resource limits (no OOM, no token exhaustion)
- [ ] Adaptive retry reduces total retries by 20% vs. fixed retry policy
- [ ] Model selection optimization improves success rate by 10% vs. baseline
- [ ] Compat path fully removed; zero references to old routing

### Rollback Plan

This is the highest-risk phase. If adaptive optimization causes instability:
1. Set `adaptive.enabled: false` — falls back to static decomposition rules (Phase 3)
2. All fractal orchestration continues; only the *dynamic* aspect is disabled
3. Tuning continues in shadow mode (analyzes but doesn't act) until stable

---

## Dependencies Between Phases

```
Phase 1 (Instrumentation)
    │
    ├───► Phase 2 (Hardening) ── requires traces to validate fixes
    │         │
    │         └───► Phase 3 (Contracts + Leases) ── requires clean codebase
    │                   │
    │                   ├───► Phase 4 (Dashboard + Replay) ── requires traces + contracts
    │                   │
    │                   └───► Phase 5 (Eval Flywheel) ── requires contracts for scoring
    │                             │
    │                             └───► Phase 6 (Adaptive Optimization) ── requires baseline metrics
```

**Parallel opportunities within phases:**
- Phase 1: P1-1 (trace emitter) must come first; P1-2 through P1-4 can proceed in parallel once P1-1 is ready
- Phase 2: All deliverables independent; can be parallelized across agents
- Phase 3: P3-1 and P3-3 (contract schema + lease manager) can proceed in parallel; P3-5 depends on both
- Phase 4: P4-1 (shell) first; P4-2 through P4-5 can proceed in parallel
- Phase 5: P5-1 and P5-2 independent; P5-3 depends on P5-1; P5-4 depends on P5-3
- Phase 6: Sequential — each deliverable depends on the previous

---

## Backward Compatibility Strategy

### Feature Flags

All new systems are controlled by feature flags in `configs/orchestrator/router.yaml`:

```yaml
migration:
  # Phase 1: Observability
  observability:
    enabled: true          # Enable after Phase 1
    sampling_rate: 1.0     # 100% sampling; reduce for C1 in production

  # Phase 3: Contracts + Leases
  contracts:
    enabled: false         # Enable after Phase 3
    tier_threshold: C3     # Only apply to C3+ initially

  leases:
    enabled: false         # Enable after Phase 3
    default_timeout: 300   # 5 minutes
    expiry_action: retry   # retry | escalate | fail

  # Phase 6: Adaptive
  adaptive:
    enabled: false         # Enable after Phase 6
    decomposition: dynamic # static | dynamic
    swarm_sizing: dynamic  # fixed | dynamic
```

### Compat Path Layer

Phase 3 introduces a compat path layer that routes tasks through old or new execution paths:

```
Incoming Task
    │
    ▼
┌─────────────────────┐
│  Feature Flag Check  │  contracts.enabled?
└─────────────────────┘
    │              │
    ▼              ▼
  YES →          NO →
  New Path       Old Path
  (fractal)      (existing)
    │              │
    ▼              ▼
  Output ───► Normalize ───► Return
```

The normalize step ensures output format is identical regardless of path, so downstream consumers are unaffected.

### Sunset Schedule

| Legacy Component | Sunset After | Removal Phase |
|------------------|--------------|---------------|
| Old routing path | Phase 4 ships | Phase 6 |
| RALPH as orchestrator | Phase 3 ships | Phase 3 (repurposed, not removed) |
| Silent fallback patterns | Phase 2 ships | Phase 2 |
| `.agents` path references | Phase 2 ships | Phase 2 |
| Duplicate scripts | Phase 2 ships | Phase 2 |

---

## Phase Gate Checklist

Before proceeding from one phase to the next, verify:

- [ ] All deliverables for current phase complete
- [ ] All success criteria met (document evidence)
- [ ] No regressions in existing functionality (run `make test-all`)
- [ ] Trace data confirms correct behavior (Phase 1+)
- [ ] Quality gates pass (Phase 5+)
- [ ] Stakeholder sign-off received
- [ ] Rollback plan documented and tested
- [ ] Next phase scope confirmed (no scope creep)

**If any criterion fails:** Do not proceed. Fix the failure, re-verify, then proceed.
