# Final Architecture Recommendation — Zera Fractal Multi-Agent Blueprint

**Audit Wave:** 7 — Final Recommendation + Migration Package
**Date:** 2026-04-13
**Status:** Ready for stakeholder review

---

## Executive Summary

### What We Found

Over Waves 0–6, we audited the Zera multi-agent architecture across 6 dimensions:

| Wave | Focus | Key Finding |
|------|-------|-------------|
| 0 | Structural hygiene | `.agents/.agents` mismatch, duplicate scripts, missing paths, silent fallbacks across the codebase |
| 1 | Orchestration topology | Single-threaded orchestration — no true parallel agents. RALPH is iterative refinement, not multi-agent coordination |
| 2 | Fractal decomposition | 6-level decomposition hierarchy designed; delegation rules and parallelization policy defined |
| 3 | Subsystem evaluation | 10 subsystems evaluated against 3 options each via weighted decision matrix |
| 4 | Target blueprint | State machine (13 states), entity/event schema, governance layer specified |
| 5 | Dashboard IA | Trace visualization, kanban/timeline views, cognitive motion signals designed |
| 6 | Benchmark & eval | Benchmark suite, chaos injection, eval metrics, test matrix specified |

**Core problem:** The current architecture *labels* itself as multi-agent but operates as a single-threaded iterative loop. Task classification (C1–C5) exists but does not drive parallel swarm execution. Observability is insufficient for diagnosing failures in complex task graphs.

### What We Recommend

**A soft-migration strategy** — not a rewrite. Incrementally harden the existing system toward true fractal multi-agent execution through 6 phases:

1. **Instrumentation** — wire observability into every orchestrator path
2. **Hardening** — fix structural issues (paths, fallbacks, duplicates)
3. **Contracts** — introduce task contracts + lease management for subagent delegation
4. **Dashboard + Replay** — ship the observability dashboard + trace replay
5. **Eval Flywheel** — benchmark suite with automated quality gates
6. **Adaptive Optimization** — runtime task decomposition + dynamic swarm sizing

**Expected timeline:** 8–12 weeks for full migration, with production-ready observability by end of Phase 2 (week 4).

---

## Key Architectural Decisions

### AD-01: Fractal Decomposition Over Flat Swarm

**Decision:** Adopt the 6-level fractal decomposition hierarchy (Wave 2) rather than a flat swarm model.

**Rationale:**
- Flat swarms cannot express hierarchical delegation (a C5 task spawning C3 subtasks spawning C1 workers)
- Fractal decomposition matches the existing C1–C5 tier model — each tier maps to a decomposition level
- Enables bounded parallelism: each level has explicit concurrency limits and resource budgets
- Failure isolation is cleaner — a failure at level N does not cascade to levels above

**Rejected alternatives:**
- *Flat swarm:* Simpler but cannot express delegation hierarchies; all agents are peers
- *Hierarchical tree (rigid):* Too inflexible — cannot adapt when a subtask is simpler than its parent suggests

---

### AD-02: Contracts + Leases Before True Parallelism

**Decision:** Implement task contracts and lease management (Phase 3) before enabling parallel swarm execution.

**Rationale:**
- Parallel execution without contracts means no way to verify subagent output correctness
- Leases prevent resource exhaustion — a subagent that hangs or loops indefinitely holds a lease that expires
- Contracts provide the schema for delegation: input, expected output, timeout, retry policy
- This is the *minimum viable protocol* for safe delegation

**Rejected alternatives:**
- *Parallel-first, contracts-later:* Would produce undetectable failures in subagent output
- *Schema-only (no leases):* Would allow runaway agents to consume unbounded resources

---

### AD-03: Observability as Foundation, Not Afterthought

**Decision:** Phase 1 is entirely instrumentation — no feature work until every orchestrator path emits structured traces.

**Rationale:**
- Wave 1 revealed that we cannot currently diagnose *why* a task failed — only that it failed
- Without traces, we cannot benchmark (Phase 5), debug failures, or validate migration correctness
- Structured traces enable trace replay (Phase 4) — critical for regression testing
- Dashboard (Wave 5) depends entirely on this data

**Trace schema (minimum):**
```yaml
trace:
  task_id: uuid
  tier: C1|C2|C3|C4|C5
  state: one of 13 states
  agent_id: string
  parent_task_id: uuid?  # null for root tasks
  started_at: iso8601
  ended_at: iso8601?
  duration_ms: int
  tools_invoked: [string]
  error: string?
  retry_count: int
  lease_id: uuid?
  output_hash: sha256?
```

---

### AD-04: Soft Migration via Compat Paths

**Decision:** Maintain backward compatibility throughout migration. New systems run alongside old; routing gradually shifts.

**Rationale:**
- A rewrite would require halting all agent operations for weeks — unacceptable for a production platform
- Compat paths allow incremental rollout: C1/C2 tasks migrate first (lowest risk), C4/C5 last
- If a phase fails, rollback is simply reverting routing config — no data loss
- Each phase has an explicit feature flag in `configs/orchestrator/router.yaml`

**Rejected alternatives:**
- *Big-bang rewrite:* Months of downtime, no rollback path, high risk of regression
- *Parallel systems with no migration:* Leaves legacy forever; doubles maintenance burden

---

### AD-05: RALPH Repurposed, Not Replaced

**Decision:** RALPH (currently iterative refinement) becomes the *convergence checker* within the fractal hierarchy, not the primary orchestrator.

**Rationale:**
- RALPH's iterative loop is valuable for validating subagent output quality
- It should run *after* subagent execution to verify contracts are met
- The primary orchestrator becomes the fractal delegation engine
- RALPH as convergence checker: takes subagent outputs → scores against contract → passes/fails/retries

**New role:**
```
Fractal Orchestrator
  ├── Decompose task → subtasks
  ├── Lease subagents → execute in parallel
  ├── Collect outputs
  └── RALPH convergence checker → verify → pass | retry | escalate
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Subagent lease timeout too short for complex tasks | Medium | Medium | Dynamic lease sizing based on task tier; empirical tuning from Phase 5 benchmarks |
| Contract schema too rigid, blocking valid outputs | Medium | High | Schema versioning + allow-listed extensions per skill type |
| Trace volume overwhelms storage | Low | Medium | Sampling policy for C1 tasks; full traces for C3+; TTL-based cleanup |
| Migration stalls at Phase 3 (contracts are complex) | Medium | High | Start with minimal contract schema (input/output/timeout only); extend iteratively |
| Dashboard shipped without meaningful data | Low | Medium | Phase 1 instrumentation gates Phase 4 dashboard work |
| Backward compat paths create maintenance burden | Medium | Low | Sunset schedule: legacy paths removed 2 phases after replacement ships |

**Overall risk level:** Medium. All identified risks have concrete mitigations. No showstoppers.

---

## Expected Outcomes

### After Phase 2 (Week 4) — "Observable System"
- All orchestrator paths emit structured traces
- Structural issues (Wave 0) resolved
- System health visible via CLI (`swarmctl doctor` enhanced)
- No silent fallbacks; all errors logged with context

### After Phase 4 (Week 7) — "Visible System"
- Dashboard shipped with trace visualization, kanban view, timeline
- Trace replay works for any completed task
- Regression detection automated via trace comparison
- Team can *see* what agents are doing in real time

### After Phase 6 (Week 12) — "Adaptive System"
- True fractal multi-agent execution with parallel swarms
- Runtime task decomposition based on complexity analysis
- Dynamic swarm sizing (concurrency adapts to resource availability)
- Eval flywheel continuously benchmarks and tunes agent performance
- Expected throughput increase: **3–5x** for C3+ tasks
- Expected failure detection rate: **>95%** (currently ~40%)

---

## Decision Record

| Decision | Status | Owner | Target Phase |
|----------|--------|-------|--------------|
| AD-01: Fractal decomposition | Accepted | Architecture | Phase 3 |
| AD-02: Contracts + leases first | Accepted | Architecture | Phase 3 |
| AD-03: Instrumentation first | Accepted | Infrastructure | Phase 1 |
| AD-04: Soft migration | Accepted | Architecture | All phases |
| AD-05: RALPH repurposed | Accepted | Architecture | Phase 3 |
| Dashboard IA (Wave 5) | Accepted | Frontend | Phase 4 |
| Benchmark suite (Wave 6) | Accepted | QA | Phase 5 |

---

## Next Steps

1. **Stakeholder review** of this document (this wave)
2. **Phase 1 kickoff** — instrumentation scope finalization
3. **Create tracking issue** in project management system with all backlog items (see `IMPLEMENTATION_BACKLOG.md`)
4. **Weekly migration standup** — 15 min, Monday, track phase progress
5. **Phase gate reviews** — at end of each phase, verify success criteria before proceeding

**Supporting documents in this package:**
- `MIGRATION_PLAN.md` — Detailed phase plans with dependencies
- `IMPLEMENTATION_BACKLOG.md` — Prioritized backlog with acceptance criteria
- `QUICK_WINS.md` — Sub-1-day improvements to start immediately
- `RISKS_AND_FAILSAFES.md` — Risk register with rollback strategies
