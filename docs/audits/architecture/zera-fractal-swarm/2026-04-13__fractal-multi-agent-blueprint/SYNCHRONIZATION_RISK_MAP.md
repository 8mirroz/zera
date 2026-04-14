# Synchronization Risk Map — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Scope:** Shared-state paths, concurrency risks, missing safety mechanisms  

---

## 1. Shared-State Paths

### 1.1 File-Based Shared State

| Path | Type | Writers | Readers | Concurrency Risk |
|------|------|---------|---------|-----------------|
| `logs/agent_traces.jsonl` | Append-only | `emit_event()` (all components) | Validator, dashboard, auditor | ⚠️ Concurrent appends may interleave lines (no file lock) |
| `.agents/memory/memory.jsonl` | Append-only | All agents | Retriever, indexer | ⚠️ Same as above |
| `.agents/runtime/approvals.json` | Read-write | ApprovalEngine | Auditor, agent | 🔴 Read-modify-write without lock |
| `.agents/runtime/background-jobs.json` | Read-modify-write | BackgroundJobRegistry, Scheduler | Monitor | 🔴 Read-modify-write without lock |
| `.agent/evolution/state.json` | Read-modify-write | zera-evolutionctl, self_evolution_loop | All evolution tools | 🔴 Read-modify-write without lock |
| `.agent/evolution/promotion_state.json` | Read-modify-write | zera-evolutionctl (promote) | Promotion auditor | 🔴 Read-modify-write without lock |
| `.agent/evolution/evolutionctl-state.json` | Read-modify-write | zera-evolutionctl | Status queries | 🔴 Read-modify-write without lock |
| `.agents/memory/goal-stack.json` | Read-modify-write | Goal manager | Agent runtime | 🔴 Read-modify-write without lock |
| `.agents/memory/skill_index.json` | Read-modify-write | `publish-skills` | Skill router | 🟡 Low contention (infrequent writes) |
| `.agents/memory/router_embeddings.json` | Read-modify-write | Embedding generator | Router | 🟡 Low contention |

### 1.2 Environment Variable Shared State

| Variable | Purpose | Readers | Risk |
|----------|---------|---------|------|
| `AGENT_OS_TRACE_FILE` | Override trace file path | `emit_event()` | 🟢 Read-only |
| `ZERA_REPO_ROOT` / `AGENT_OS_REPO_ROOT` | Override repo root | All scripts | 🟢 Read-only |
| `OPENROUTER_API_KEY` | LLM API key | Model providers | 🟢 Read-only |
| `GEMINI_API_KEY` | Gemini API key | Model providers | 🟢 Read-only |

---

## 2. Concurrency Risks

### 2.1 🔴 High Risk: No File Locking on State Files

**Affected files:** All `.json` state files in `.agents/runtime/`, `.agent/evolution/`

**Pattern:**
```python
def _save(self, payload):
    data = self._load()       # READ
    data.update(payload)      # MODIFY
    self.storage_path.write_text(...)  # WRITE
```

**Risk:** If two processes call `_save()` simultaneously, one write will be lost (last-writer-wins).

**Missing:**
- File-level locks (fcntl/flock)
- Atomic writes (write to temp + rename)
- Optimistic concurrency control (version numbers)
- Lease-based exclusive access

### 2.2 🔴 High Risk: Concurrent Trace Appends

**Affected:** `logs/agent_traces.jsonl`, `.agent/evolution/telemetry.jsonl`, `.agents/memory/memory.jsonl`

**Pattern:**
```python
with path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(row) + "\n")
```

**Risk:** On some filesystems, concurrent append operations can interleave partial writes, producing invalid JSONL lines.

**Missing:**
- Write-ahead logging
- Line-level locking
- Write batching

### 2.3 🟡 Medium Risk: Branch Lock Detection Without Enforcement

**Affected:** `agent_os/swarm/branch_lock.py`

**Current:** `detect_branch_lock_collisions()` identifies overlapping scopes but does NOT:
- Write lock files
- Block concurrent access
- Acquire/release locks
- Implement timeout/heartbeat

**Risk:** The collision detection is a **pure function** — it returns a list of collisions but does not prevent them.

### 2.4 🟡 Medium Risk: Non-Idempotent Steps

**Affected:** Several operations are not idempotent:

| Operation | Why Non-Idempotent | Impact |
|-----------|-------------------|--------|
| `emit_event()` | Appends new line each call | Duplicate events on retry |
| `ApprovalEngine.signal()` | Creates new UUID each call | Duplicate tickets on retry |
| `StopController.signal()` | Creates new UUID each call | Duplicate stop signals on retry |
| `BackgroundJobRegistry.register()` | Appends to list | Duplicate registrations on retry |
| Evolution `promote-enable` | Creates promotion state | Partial promotion on failure |

**Missing:**
- Idempotency keys
- Deduplication logic
- "Already done" checks

### 2.5 🟡 Medium Risk: No Heartbeat Mechanism

**Affected:** All long-running operations

| Operation | Duration | Heartbeat? | Timeout? |
|-----------|----------|------------|----------|
| Self-evolution loop | Hours | ❌ No | ❌ No |
| RALPH loop | Minutes | ❌ No | ❌ No |
| Background jobs | Variable | ❌ No | ⚠️ Configured but not enforced |
| LLM calls | Seconds | ❌ No | ⚠️ Provider-level only |

**Risk:** If a long-running operation hangs, there is no way to detect it (no liveness probe, no timeout kill).

### 2.6 🟢 Low Risk: Read-Only Config Access

**Affected:** All YAML config files

**Pattern:** Config files are loaded once and cached (e.g., `RegistryWorkflowResolver._router_cache`).

**Risk:** Minimal — reads are safe. Stale cache is the only risk (config changes not reflected until cache invalidation).

---

## 3. Missing Safety Mechanisms

| Mechanism | Needed Where | Current State | Priority |
|-----------|-------------|---------------|----------|
| File locks (flock) | `.agents/runtime/*.json`, `.agent/evolution/*.json` | ❌ Not implemented | P0 |
| Atomic writes (temp + rename) | All state files | ❌ Not implemented | P0 |
| Idempotency keys | emit_event, approval, stop signals | ❌ Not implemented | P1 |
| Lease + heartbeat | Long-running tasks, background jobs | ❌ Not implemented | P1 |
| Optimistic concurrency (version) | State files with read-modify-write | ❌ Not implemented | P1 |
| Trace line integrity check | JSONL files | ⚠️ trace_validator.py (post-hoc) | P2 |
| Deadlock detection | Future parallel agents | ❌ Not applicable yet | N/A |

---

## 4. Current Concurrency Model Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| Single-threaded safety | ✅ Good | Most operations are single-threaded, reducing risk |
| Append-only safety | ⚠️ Partial | JSONL appends are mostly safe but not guaranteed |
| Read-modify-write safety | ❌ Poor | No locking on state files |
| Retry safety | ❌ Poor | Non-idempotent operations cause duplicates |
| Timeout safety | ❌ Poor | No liveness monitoring |
| Crash recovery | ⚠️ Partial | State files may be corrupted on crash (no atomic writes) |

---

## 5. Risk Heatmap

```
                    Frequency
              Low        Medium      High
         ┌──────────┬──────────┬──────────┐
    High │  MEDIUM  │  HIGH    │ CRITICAL │
         │          │          │          │
 Impact  ├──────────┼──────────┼──────────┤
 Medium  │  LOW     │  MEDIUM  │  HIGH    │
         │          │          │          │
         ├──────────┼──────────┼──────────┤
    Low  │  INFO    │  LOW     │  MEDIUM  │
         │          │          │          │
         └──────────┴──────────┴──────────┘
```

| Risk | Impact | Frequency | Zone |
|------|--------|-----------|------|
| State file corruption (no atomic writes) | High | Medium | **HIGH** |
| Lost writes (no file locking) | High | Medium | **HIGH** |
| Duplicate events (no idempotency) | Medium | High | **HIGH** |
| Hung processes (no heartbeat) | Medium | Low | **MEDIUM** |
| Stale config cache | Low | Medium | **LOW** |
| Trace interleaving | Medium | Low | **MEDIUM** |
