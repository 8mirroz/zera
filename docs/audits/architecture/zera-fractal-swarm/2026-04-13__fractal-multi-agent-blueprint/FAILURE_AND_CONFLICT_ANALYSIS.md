# Failure & Conflict Analysis — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Scope:** Failure classes, recovery mechanisms, gaps, and conflict scenarios  

---

## 1. Failure Classes

### 1.1 Routing Failures

| Failure Class | Trigger | Current Recovery | Gap |
|---------------|---------|-----------------|-----|
| **Model unavailable** | LLM API returns error / timeout | Fallback chain in `router.yaml` (2-3 alternatives) | ❌ No automatic retry with backoff; no circuit breaker |
| **Tier misclassification** | Task incorrectly classified as C1 when it's C4 | None — runs with wrong model/workflow | ❌ No validation that output matches expected complexity |
| **Workflow not found** | `router.yaml` references non-existent workflow path | `RegistryWorkflowResolver` returns empty dict | ❌ Silent failure — workflow runs with no definition |
| **Runtime unavailable** | Selected runtime provider fails to initialize | `RuntimeRegistry` has `fallback_chain` per provider | ⚠️ Fallback exists but no health check before selection |
| **Config parse error** | YAML/JSON in configs is malformed | `ModelRouterError` raised; `parse_simple_yaml` fallback | ⚠️ Simple parser may silently produce wrong data |
| **Model alias unresolved** | `$MODEL_*` not found in `models.yaml` | Env var expansion returns literal string | ❌ LLM call fails with unresolvable model name |

### 1.2 Execution Failures

| Failure Class | Trigger | Current Recovery | Gap |
|---------------|---------|-----------------|-----|
| **Tool timeout** | Tool execution exceeds `timeout_minutes` | Tool returns error status | ❌ No automatic retry; no partial result preservation |
| **LLM response parse error** | LLM returns malformed JSON / unexpected format | Caller-level error handling (varies by caller) | ❌ No standardized parse error recovery |
| **File write failure** | Disk full / permissions error | Exception propagated to caller | ❌ No disk space check before writes |
| **Subprocess failure** | `zera chat` / `hermes chat` returns non-zero | Exit code captured; event emitted with status=error | ✅ Adequate for current needs |
| **Memory write blocked** | Memory policy blocks write | Event `memory_write_blocked` emitted | ✅ Adequate |
| **Budget exceeded** | Token cost exceeds `budget_policy.yaml` limits | Event `budget_limit_hit` emitted | ❌ No automatic stop — depends on caller to check |

### 1.3 Coordination Failures

| Failure Class | Trigger | Current Recovery | Gap |
|---------------|---------|-----------------|-----|
| **Branch collision** | Two lanes write to same branch scope | `detect_branch_lock_collisions()` returns collision list | ❌ Detection only — no prevention |
| **Approval timeout** | Approval ticket not resolved within TTL | None — ticket remains pending indefinitely | ❌ No timeout/escalation |
| **RALPH loop divergence** | Scores oscillate without convergence | Stops after `max_iterations` (from router.yaml) | ✅ Adequate |
| **Evolution loop crash** | `self_evolution_loop.py` crashes mid-cycle | PID file may remain stale; kill switch | ⚠️ Kill switch exists but requires manual intervention |
| **Background job stuck** | Job runs indefinitely | Dead letter queue mentioned in schema, not implemented | ❌ No dead letter queue |
| **Stop signal ignored** | Agent continues after `stop_controller.signal()` | Agent must check stop signals proactively | ⚠️ Relies on agent cooperation — not enforced |

### 1.4 State Corruption Failures

| Failure Class | Trigger | Current Recovery | Gap |
|---------------|---------|-----------------|-----|
| **JSON state corruption** | Crash mid-write leaves partial JSON | `_load()` catches JSON parse error → returns default | ⚠️ Data loss — corrupt state replaced with empty default |
| **Telemetry loss** | Trace file grows too large / disk full | None | ❌ No rotation, no disk space monitoring |
| **Memory index corruption** | BM25 index corrupted | Rebuild from `memory.jsonl` (possible but not automated) | ❌ No automated rebuild |
| **Evolution state corruption** | `.agents/evolution/state.json` corrupted | Evolution falls back to default state | ⚠️ Evolution context lost |

### 1.5 Observability Failures

| Failure Class | Trigger | Current Recovery | Gap |
|---------------|---------|-----------------|-----|
| **Trace file unavailable** | Path not writable | `emit_event()` creates directory, appends | ✅ Auto-creates directory |
| **Schema violation** | Event missing required fields | `trace_validator.py` flags post-hoc | ❌ No pre-write validation |
| **Trace file rotation** | File grows too large | Manual rotation | ❌ No automatic rotation |
| **Dashboard stale** | No new events for extended period | None | ❌ No staleness detection |

---

## 2. Recovery Mechanisms — Current State

| Mechanism | Implemented? | Coverage | Reliability |
|-----------|-------------|----------|-------------|
| Model fallback chain | ✅ Yes | Model selection only | ⚠️ No retry with backoff |
| Runtime fallback chain | ✅ Yes | Runtime selection only | ⚠️ Same as above |
| Kill switch | ✅ Yes | Evolution loop only | ⚠️ Manual |
| Stop controller | ✅ Yes | All agents (cooperative) | ⚠️ Not enforced |
| Approval timeout | ❌ No | N/A | ❌ No implementation |
| Circuit breaker | ❌ No | N/A | ❌ No implementation |
| Dead letter queue | ❌ No | N/A | ❌ No implementation |
| State file backup | ⚠️ Partial | Evolution snapshots | ⚠️ Only for promotion |
| Trace validation | ✅ Yes | Post-hoc | ✅ Validator exists |
| Config validation | ✅ Yes | On `swarmctl.py doctor` | ✅ Doctor checks consistency |
| Crash recovery | ❌ No | N/A | ❌ No automatic recovery |
| Lease-based claiming | ❌ No | N/A | ❌ No implementation |
| Heartbeat monitoring | ❌ No | N/A | ❌ No implementation |

---

## 3. Conflict Scenarios

### 3.1 Routing Conflict: Multiple Routers Disagree

**Scenario:** `UnifiedRouter` selects model A based on tier, but `PersonaModeRouter` overrides to model B based on mode.

**Current behavior:** `PersonaModeRouter` is consulted within `ZeraCommandOS`, so the mode binding takes precedence. No conflict — it's a designed override.

**Risk:** If the mode-bound model is unavailable, the fallback chain from the original tier is lost.

### 3.2 State Conflict: Dual Evolution State

**Scenario:** `.agents/evolution/state.json` and `.agents/evolution/state.json` diverge.

**Current behavior:** `zera-evolutionctl.py` reads/writes `.agents/evolution/` only. Any tool reading `.agents/evolution/` sees stale data.

**Risk:** Decision based on stale state → incorrect promotion/rollback.

### 3.3 Trace Conflict: Concurrent Appends

**Scenario:** Two processes append to `logs/agent_traces.jsonl` simultaneously.

**Current behavior:** Both appends succeed (file append is atomic for small writes on most filesystems), but lines may interleave if writes are large.

**Risk:** Invalid JSONL lines → `trace_validator.py` flags them as invalid.

### 3.4 Memory Conflict: Concurrent Writes

**Scenario:** Two agents write to `.agents/memory/memory.jsonl` simultaneously.

**Current behavior:** Same as trace file — appends are mostly safe but not guaranteed.

**Risk:** Memory corruption → retrieval returns incorrect results.

### 3.5 Approval Conflict: Duplicate Tickets

**Scenario:** `ApprovalEngine._save()` called twice for the same action (retry).

**Current behavior:** Two separate tickets created with different UUIDs.

**Risk:** Confusion — operator may approve one ticket thinking it's the only one.

---

## 4. Failure Recovery Gaps — Priority Matrix

| Gap | Impact | Effort | Priority |
|-----|--------|--------|----------|
| File locking on state files | 🔴 High (data loss) | Medium | P0 |
| Atomic writes (temp + rename) | 🔴 High (corruption) | Low | P0 |
| Idempotency for emit/approval/stop | 🟡 Medium (duplicates) | Low | P1 |
| Circuit breaker for LLM calls | 🟡 Medium (cascading failures) | Medium | P1 |
| Heartbeat + timeout for long operations | 🟡 Medium (hung processes) | Medium | P1 |
| Lease-based task claiming | 🔴 High (for future parallel agents) | High | P1 |
| Dead letter queue for background jobs | 🟡 Medium (lost jobs) | Medium | P2 |
| Trace file rotation | 🟢 Low (operational hygiene) | Low | P2 |
| Automated memory index rebuild | 🟢 Low (can rebuild manually) | Medium | P2 |
| Pre-write schema validation | 🟡 Medium (invalid traces) | Low | P1 |
| Approval timeout + escalation | 🟡 Medium (stuck approvals) | Medium | P1 |

---

## 5. Orchestration vs Choreography — Distinction

| Aspect | Current System | True Multi-Agent Would Need |
|--------|---------------|---------------------------|
| **Decision model** | Centralized orchestration (single router) | Decentralized choreography (agents coordinate) |
| **Failure isolation** | Process-level (crash kills everything) | Agent-level (one agent fails, others continue) |
| **State ownership** | Shared files (no boundaries) | Per-agent state with explicit handoff |
| **Retry model** | Manual or caller-specific | Automatic with backoff, per-agent |
| **Conflict resolution** | Last-writer-wins | Explicit merge/consensus |
| **Observability** | Centralized trace file | Distributed tracing with correlation IDs |

---

## 6. Deterministic vs Non-Deterministic Branching

| Component | Branching Type | Determinism | Notes |
|-----------|---------------|-------------|-------|
| `UnifiedRouter` | Deterministic (config lookup) | ✅ Fully deterministic | Same input → same output |
| `RegistryWorkflowResolver` | Deterministic (config lookup) | ✅ Fully deterministic | Same input → same output |
| `ZeraCommandOS.resolve()` | Deterministic (keyword matching) | ✅ Fully deterministic | Same input → same output |
| `PersonaModeRouter` | Deterministic (config lookup) | ✅ Fully deterministic | Same input → same output |
| `RALPH loop` | Non-deterministic (LLM output varies) | ❌ LLM introduces randomness | Same input → different outputs per iteration |
| `self_evolution_loop` | Non-deterministic (LLM scoring) | ❌ LLM introduces randomness | Same input → different evolution paths |
| `RuntimeRegistry` | Deterministic (config lookup) | ✅ Fully deterministic | Same input → same output |
| `ApprovalEngine` | Deterministic (ticket creation) | ✅ Fully deterministic | Same input → same ticket |

**Summary:** The orchestration layer is **fully deterministic** — same config input always produces the same routing decision. Non-determinism is introduced only when LLM calls are made (execution phase, RALPH, evolution).
