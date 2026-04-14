# Risks and Failsafes — Zera Fractal Multi-Agent Blueprint

**Audit Wave:** 7 — Final Recommendation + Migration Package
**Date:** 2026-04-13

---

## 1. Migration Risks

### R-1: Subagent Lease Timeout Too Short

**Description:** Fixed lease timeouts may be too short for complex C4/C5 tasks, causing premature termination and retries.

**Likelihood:** Medium
**Impact:** Medium (increased latency, wasted compute)
**Detection:** Trace events show `lease_expire` followed by `retry` for same task type repeatedly
**Mitigation:**
- Dynamic lease sizing based on task tier (C1: 60s, C2: 120s, C3: 300s, C4: 600s, C5: 1200s)
- Empirical tuning from Phase 5 benchmark data
- Lease extension API for subagents that need more time (requires justification trace)

**Residual risk after mitigation:** Low

---

### R-2: Contract Schema Too Rigid

**Description:** Strict contract schemas may reject valid but unexpected output formats, blocking otherwise correct subagent work.

**Likelihood:** Medium
**Impact:** High (blocks valid work, forces retries)
**Detection:** Trace events show `contract_validation_failed` for outputs that RALPH convergence checker scores as high quality
**Mitigation:**
- Schema versioning with allow-listed extensions per skill type
- "Soft" validation mode: logs warnings but doesn't block (Phase 3 initial rollout)
- "Hard" validation mode: blocks invalid output (after schema maturity)
- Contract extension mechanism: subagents can declare additional output fields

**Residual risk after mitigation:** Low-Medium

---

### R-3: Trace Volume Overwhelms Storage

**Description:** Full tracing of all tasks (especially C1, which are numerous) may generate more trace data than the file-based sink can handle.

**Likelihood:** Low
**Impact:** Medium (trace loss, degraded observability)
**Detection:** Trace sink latency increases >10ms per emission; disk usage grows unexpectedly
**Mitigation:**
- Sampling policy: 100% for C3+, 10% for C1, 50% for C2
- File rotation: new file per day or per 100MB
- TTL-based cleanup: traces older than 30 days archived or deleted
- Upgrade path to SQLite/Qdrant when file-based sink hits limits

**Residual risk after mitigation:** Low

---

### R-4: Migration Stalls at Phase 3 (Contracts Are Complex)

**Description:** Phase 3 introduces the most complex new abstractions (contracts, leases, delegation). Underestimating complexity could stall the migration.

**Likelihood:** Medium
**Impact:** High (all subsequent phases blocked)
**Detection:** Phase 3 timeline slips by >1 week; P0 items not completing
**Mitigation:**
- Start with minimal contract schema (input, output, timeout only) — no advanced features
- Extend iteratively: add retry policy, quality thresholds in Phase 3 follow-up
- Parallelize: contract schema (P0-14) and lease manager (P0-16) are independent
- Fallback: if delegation router (P0-18) is too complex, ship contracts + leases without delegation first

**Residual risk after mitigation:** Medium (complexity is inherent, but scope can be reduced)

---

### R-5: Dashboard Shipped Without Meaningful Data

**Description:** Phase 4 dashboard could be visually impressive but lack actionable data if Phase 1 instrumentation is incomplete.

**Likelihood:** Low
**Impact:** Medium (lost credibility, wasted frontend effort)
**Detection:** Dashboard shows "no data" or stale data for >50% of views
**Mitigation:**
- Phase 1 instrumentation is a hard gate for Phase 4 — cannot start Phase 4 until Phase 1 success criteria met
- Dashboard MVP: only show views that have data (traces first, kanban second, timeline last)
- "Data readiness" check before dashboard demo to stakeholders

**Residual risk after mitigation:** Low

---

### R-6: Backward Compat Paths Create Maintenance Burden

**Description:** Maintaining both old and new routing paths doubles testing effort and creates confusion about which path is "real."

**Likelihood:** Medium
**Impact:** Low (extra work, but system remains functional)
**Detection:** PR reviews catch bugs in old path that wouldn't affect new path; test suite takes 2x longer
**Mitigation:**
- Sunset schedule: legacy path removed 2 phases after replacement ships
- Feature flag controls which path is default; old path used only for comparison testing
- Automated tests run against both paths and compare outputs
- Documentation clearly marks old path as "legacy — do not use for new work"

**Residual risk after mitigation:** Low

---

### R-7: RALPH Repurposing Breaks Existing Workflows

**Description:** Changing RALPH from orchestrator to convergence checker may break workflows that depend on its current behavior.

**Likelihood:** Medium
**Impact:** Medium (regression in task quality for workflows using RALPH)
**Detection:** Benchmark scores drop for tasks that previously used RALPH as orchestrator
**Mitigation:**
- RALPH's iterative loop preserved as convergence checker — only the calling convention changes
- A/B test: run RALPH in both roles (orchestrator vs. checker) on same tasks; compare results
- If convergence checker scores lower, adjust scoring threshold or add pre-processing
- Rollback: RALPH can continue as orchestrator until convergence checker matches quality

**Residual risk after mitigation:** Low-Medium

---

### R-8: Dynamic Decomposition Produces Invalid Subtasks

**Description:** Phase 6's runtime decomposition (AD-05) may produce subtasks that cannot be executed (missing context, invalid contracts).

**Likelihood:** Medium
**Impact:** High (task failures, cascading retries)
**Detection:** Benchmark tasks fail at decomposition step; traces show `decomposition_error`
**Mitigation:**
- Decomposition validated by contract checker before subagent dispatch
- Shadow mode: decompose but don't dispatch; validate subtasks against ground truth
- Fallback: if dynamic decomposition fails, fall back to static rules (Phase 3)
- Human-in-the-loop review for first 100 dynamic decompositions

**Residual risk after mitigation:** Medium (novel system, will need tuning)

---

## 2. Failsafes

### F-1: Trace-Based Failure Detection

**Mechanism:** Every orchestrator path emits traces. A monitoring script checks for anomalies every 5 minutes.

**Detects:**
- Silent failures (no trace emitted when one expected)
- Stuck tasks (trace shows same state for >expected duration)
- High error rate (>10% of tasks in last hour ended in error)
- Lease exhaustion (>5 lease expiries in last 10 minutes)

**Response:**
- Alert to team channel
- Auto-generate incident report with affected task IDs
- If error rate >25%: auto-disable new features (revert to compat path)

---

### F-2: Contract Validation Guardrail

**Mechanism:** Contract validator runs in "audit mode" (logs warnings but doesn't block) for the first 2 weeks after Phase 3 launch.

**Detects:**
- Schema mismatches that indicate contract bugs (not subagent bugs)
- Patterns of false positives (valid outputs rejected by schema)
- Missing contract fields that subagents consistently provide

**Response:**
- If >20% of outputs fail validation: pause hard validation, audit schemas
- If specific field always missing: add to schema as optional
- If specific pattern always rejected: adjust schema or fix subagent

---

### F-3: Lease Timeout Circuit Breaker

**Mechanism:** If lease expiries exceed threshold, circuit breaker pauses new lease issuance for 5 minutes.

**Detects:**
- Systemic issue causing all subagents to timeout (not individual slow tasks)
- Resource exhaustion (not enough CPU/memory for concurrent subagents)
- Deadlock in subagent execution

**Response:**
- Pause new lease issuance for 5 minutes
- Drain existing leases (let them complete or expire)
- Emit alert with: active lease count, expiry rate, resource usage
- After 5 minutes: resume with reduced concurrency (50% of previous)

---

### F-4: Feature Flag Emergency Kill Switch

**Mechanism:** All new features controlled by feature flags. Single config change disables all new systems.

**Detects:** N/A (manual activation)

**Response:**
```yaml
# configs/orchestrator/router.yaml
migration:
  emergency_disable: true  # Set to true to disable all new features
```

When set:
- All tasks route through old (compat) path
- New features run in shadow mode (observe but don't act)
- Alert emitted with timestamp and who triggered the kill switch
- No data loss — traces and leases from before disable remain accessible

---

### F-5: Benchmark Regression Gate

**Mechanism:** Quality gate runner (Phase 5) blocks merges that regress benchmark metrics beyond threshold.

**Detects:**
- Success rate regression >2%
- p99 latency increase >10%
- Tool efficiency decrease >5%
- Output quality score decrease >3%

**Response:**
- PR blocked from merge
- Regression report generated with: which tasks regressed, how much, likely cause
- Author must: fix regression OR document acceptable reason + get team approval to override

---

## 3. Rollback Strategies Per Phase

### Phase 1 Rollback (Instrumentation)

**Trigger:** Trace emission introduces >10% latency overhead.

**Procedure:**
1. Set `observability.enabled: false` in router config
2. Deploy — instrumentation code becomes no-op
3. Profile trace emission to find overhead source
4. Fix (likely: batch emissions, async writes, reduce payload)
5. Re-enable and verify overhead <5%

**Data loss:** None. Traces already written remain in sink files.

**Recovery time:** <30 minutes (config change + deploy)

---

### Phase 2 Rollback (Hardening)

**Trigger:** A hardening fix introduces regression in existing functionality.

**Procedure:**
1. Each hardening deliverable is a separate PR — revert the specific PR
2. Run Phase 1 trace checks to confirm no regression
3. Fix the issue and re-submit as new PR

**Data loss:** None. Hardening is additive fixes, not destructive.

**Recovery time:** <1 hour (revert + re-deploy)

---

### Phase 3 Rollback (Contracts + Leases)

**Trigger:** Contracts or leases cause task failures or excessive retries.

**Procedure:**
1. Set `contracts.enabled: false` and `leases.enabled: false` in router config
2. All tasks route through compat (old) path
3. Contract and lease code remains but is bypassed
4. Investigate failures via traces (Phase 1 instrumentation still active)
5. Fix contracts/leases; re-enable when benchmark tasks pass

**Data loss:** None. In-flight leases are drained (allowed to complete or expire).

**Recovery time:** <30 minutes (config change + deploy)

---

### Phase 4 Rollback (Dashboard + Replay)

**Trigger:** Dashboard causes performance issues or displays incorrect data.

**Procedure:**
1. Disable dashboard server — does not affect agent execution
2. Trace replay remains available via CLI (`swarmctl replay <task_id>`)
3. Fix dashboard issues; redeploy

**Data loss:** None. Dashboard is read-only consumer of traces.

**Recovery time:** <15 minutes (stop dashboard server)

---

### Phase 5 Rollback (Eval Flywheel)

**Trigger:** Quality gates block valid merges due to flaky benchmarks.

**Procedure:**
1. Set `quality_gate.enforce: false` — benchmarks still run but don't block merges
2. Chaos injection disabled by default
3. Investigate flaky tests; fix or exclude from gate
4. Re-enable enforcement when false-positive rate <5%

**Data loss:** None. Benchmark results remain available for analysis.

**Recovery time:** <15 minutes (config change)

---

### Phase 6 Rollback (Adaptive Optimization)

**Trigger:** Dynamic decomposition or swarm sizing causes instability.

**Procedure:**
1. Set `adaptive.enabled: false` — falls back to static decomposition rules (Phase 3)
2. All fractal orchestration continues; only the dynamic aspect is disabled
3. Adaptive tuning continues in shadow mode (analyzes but doesn't act)
4. Investigate instability via traces and benchmark data
5. Re-enable when shadow mode matches or exceeds static performance

**Data loss:** None. Shadow mode preserves all analysis data.

**Recovery time:** <30 minutes (config change + deploy)

---

## 4. Emergency Procedures

### EP-1: Complete System Rollback

**When:** Multiple phases failing simultaneously; system unstable.

**Procedure:**
1. Set `migration.emergency_disable: true` in router config
2. All tasks route through old (pre-migration) path
3. Stop all new feature servers (dashboard, eval, adaptive)
4. Verify system stability (all tasks completing via old path)
5. Incident post-mortem: what failed, why, how to prevent
6. Plan recovery: fix issues, re-enable phases one at a time

**Recovery time:** <1 hour

---

### EP-2: Trace Sink Full

**When:** Trace storage at capacity; new traces cannot be written.

**Procedure:**
1. Enable trace sampling: `observability.sampling_rate: 0.1` (10%)
2. Rotate trace files: `mv traces/ traces-old/ && mkdir traces/`
3. Archive old traces: `tar -czf traces-$(date).tar.gz traces-old/`
4. Remove archived traces after 30 days (per TTL policy)
5. If recurring: upgrade to SQLite or Qdrant backend

**Recovery time:** <15 minutes

---

### EP-3: Subagent Runaway (Resource Exhaustion)

**When:** Subagents consuming unbounded CPU/memory/tokens.

**Procedure:**
1. Activate lease timeout circuit breaker (F-3) — auto-pauses new leases
2. Kill all active subagent processes: `swarmctl kill-all-agents`
3. Reduce max concurrency: `leases.max_concurrent: 2` (from default 10)
4. Investigate via traces: which tasks caused runaway, what tools consumed resources
5. Resume with reduced concurrency; monitor for 30 minutes
6. Gradually increase concurrency if stable

**Recovery time:** <30 minutes

---

### EP-4: Config Corruption

**When:** Router config or other critical configs become invalid/corrupted.

**Procedure:**
1. System exits at startup with validation error (P0-12)
2. Restore last known-good config from git: `git checkout HEAD~1 -- configs/orchestrator/router.yaml`
3. Restart system
4. Investigate what corrupted the config (manual edit? automated script?)
5. Add config backup: copy config to `.backup/` before any automated change

**Recovery time:** <10 minutes

---

## 5. Known Unknowns

### KU-1: True Parallel Agent Performance

**What we don't know:** How well the current model providers (OpenRouter, Direct API, Ollama, MLX) handle true parallel requests. The current system is single-threaded, so we have no data on parallel performance.

**How we'll learn:** Phase 5 benchmarks include parallel task execution. We'll measure: throughput, error rate, latency variance under parallel load.

**Risk if wrong:** Parallel execution may be slower than expected due to rate limits or resource contention. Mitigation: dynamic swarm sizing (P1-17) adapts to actual capacity.

---

### KU-2: Contract Schema Adequacy

**What we don't know:** Whether our initial contract schema (input, output, timeout, retry) covers all subagent delegation needs.

**How we'll learn:** Phase 3 rollout with audit mode (F-2) will reveal gaps: fields subagents need but schema doesn't allow, quality criteria that can't be expressed.

**Risk if wrong:** Schema evolution required mid-migration. Mitigation: schema versioning and extension mechanism.

---

### KU-3: RALPH as Convergence Checker Quality

**What we don't know:** Whether RALPH's iterative scoring works as well when applied to subagent outputs vs. its current iterative refinement role.

**How we'll learn:** A/B testing during Phase 3: RALPH scores subagent outputs vs. human evaluation of same outputs.

**Risk if wrong:** May need a different scoring mechanism. Mitigation: pluggable convergence checker interface — swap RALPH for alternative if needed.

---

### KU-4: Dashboard Scalability

**What we don't know:** Whether the file-based trace sink can support real-time dashboard updates at production scale (1000+ tasks/day).

**How we'll learn:** Phase 4 load testing: simulate 1000+ traces, measure dashboard render time and WebSocket latency.

**Risk if wrong:** May need to upgrade to SQLite/Qdrant earlier than planned. Mitigation: dashboard architecture is sink-agnostic; backend swap doesn't affect frontend.

---

### KU-5: Dynamic Decomposition Accuracy

**What we don't know:** Whether runtime complexity analysis (P1-15) can accurately predict how a task should be decomposed without human-curated rules.

**How we'll learn:** Shadow mode in Phase 6: decompose but don't dispatch; compare against ground truth decomposition from benchmark tasks.

**Risk if wrong:** Dynamic decomposition may produce suboptimal subtasks. Mitigation: fallback to static rules; dynamic only enabled when accuracy >90%.

---

## Risk Register Summary

| ID | Risk | Likelihood | Impact | Residual | Owner |
|----|------|-----------|--------|----------|-------|
| R-1 | Lease timeout too short | Medium | Medium | Low | Infrastructure |
| R-2 | Contract schema too rigid | Medium | High | Low-Medium | Architecture |
| R-3 | Trace volume overwhelms | Low | Medium | Low | Infrastructure |
| R-4 | Phase 3 stalls | Medium | High | Medium | Architecture |
| R-5 | Dashboard without data | Low | Medium | Low | Frontend |
| R-6 | Compat path burden | Medium | Low | Low | Architecture |
| R-7 | RALPH repurposing breaks workflows | Medium | Medium | Low-Medium | Architecture |
| R-8 | Invalid subtasks from decomposition | Medium | High | Medium | Architecture |

**Overall risk posture:** Medium. All risks have concrete mitigations. No showstoppers identified. Highest-risk items (R-4, R-8) are manageable through scope reduction and shadow mode validation.
