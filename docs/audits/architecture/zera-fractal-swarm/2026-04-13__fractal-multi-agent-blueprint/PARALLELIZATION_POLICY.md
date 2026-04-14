# Parallelization Policy — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Status:** Target design (governs all parallel execution decisions)  

---

## 1. Serial vs Parallel Decision

### 1.1 Decision Matrix

| Factor | Serial (wait) | Parallel (fan-out) |
|--------|--------------|-------------------|
| **Dependency** | Child B needs Child A's output | Children are independent |
| **Resource contention** | Children write to same file | Children write to different files |
| **Complexity tier** | C1, C2 (simple tasks) | C4, C5 (complex, multi-domain) |
| **Coordination overhead** | High (frequent sync needed) | Low (independent until merge) |
| **Estimated speedup** | <2x (not worth parallelizing) | >2x (worth the overhead) |
| **Conflict risk** | High (same module/file) | Low (different modules/files) |
| **Agent availability** | Only 1 agent available | ≥2 agents available |

### 1.2 Formal Rule

```
function decide_parallelism(task) -> "serial" | "parallel":
    if task.dependencies.length == 0:
        return "serial"  # Single task, nothing to parallelize
    
    independent_children = task.dependencies.filter(d -> d.type == "parallel")
    
    if independent_children.length <= 1:
        return "serial"  # Not enough parallel work
    
    if has_shared_resources(independent_children):
        return "serial"  # Resource contention risk
    
    if estimated_speedup(independent_children) < 2.0:
        return "serial"  # Not worth the overhead
    
    if task.tier in ["C1", "C2"]:
        return "serial"  # Simple tasks don't benefit
    
    return "parallel"
```

---

## 2. Fan-Out Criteria

A task **MAY** fan-out to parallel children when **ALL** criteria are met:

| # | Criterion | Check |
|---|-----------|-------|
| 1 | ≥2 independent children | `dependencies.filter(d -> d.type == "parallel").length >= 2` |
| 2 | No shared write targets | Children write to different file paths |
| 3 | No shared memory mutations | Children don't modify same memory keys |
| 4 | Estimated speedup ≥2x | `sequential_duration / max(parallel_durations) >= 2.0` |
| 5 | Tier ≥ C3 | `task.tier in ["C3", "C4", "C5"]` |
| 6 | Agents available | `available_agents >= parallel_children.length` |

---

## 3. Fan-In Criteria

Parallel children **MUST** fan-in when **ANY** condition is met:

| # | Condition | Action |
|---|-----------|--------|
| 1 | All children completed | Merge outputs → parent continues |
| 2 | Child failed + retries exhausted | Merge with error → parent decides |
| 3 | Timeout reached | Merge completed; mark incomplete as failed |
| 4 | Stop signal received | Cancel remaining children → merge completed |
| 5 | Budget exceeded | Cancel remaining children → merge completed |

### 3.1 Merge Strategies

| Strategy | When Used | Description |
|----------|-----------|-------------|
| **Sequential merge** | Serial dependencies | Merge in dependency order (A then B then C) |
| **Parallel merge** | Independent children | Merge all at once (order doesn't matter) |
| **Best-of-N** | Competing approaches | Pick best output by scoring |
| **Consensus** | Verification tasks | Require agreement from ≥N children |
| **Quorum** | Voting tasks | Require ≥N/K children to agree |

---

## 4. Parallel Safety Requirements

### 4.1 Lease-Based Task Claiming

| Requirement | Detail |
|-------------|--------|
| **Claim** | Agent acquires lease before starting task |
| **Lease TTL** | 5 minutes (configurable per task) |
| **Renew** | Agent sends heartbeat to extend lease |
| **Expiry** | If heartbeat not received within TTL, lease expires |
| **Reclaim** | Expired lease can be claimed by another agent |
| **Conflict** | If two agents claim same task simultaneously, one wins (atomic compare-and-swap) |

**Lease schema:**
```yaml
lease:
  task_id: "task-<uuid>"
  agent_id: "agent-<id>"
  claimed_at: "<ISO-8601>"
  expires_at: "<ISO-8601>"  # claimed_at + TTL
  heartbeat_at: "<ISO-8601>"
  state: "active|expired|released"
```

### 4.2 Heartbeat Requirements

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Heartbeat interval | Every 60 seconds | Detect hung agents within 2×TTL |
| Heartbeat TTL | 5 minutes | Balance between false positives and stale lease detection |
| Heartbeat payload | `{task_id, agent_id, progress, state}` | Minimal, sufficient for monitoring |
| Missed heartbeat action | Mark lease as expired | Allow other agents to claim |

### 4.3 Idempotency Requirements

| Operation | Idempotency Key | Behavior |
|-----------|----------------|----------|
| `emit_event` | `run_id + event_type + hash(payload)` | Skip if already emitted |
| Task claim | `task_id` | Only first claim succeeds |
| Approval create | `action_type + run_id` | Return existing ticket if duplicate |
| Memory write | `key + version` | Only write if version matches |
| File write | `path + checksum` | Skip if file already matches |

### 4.4 Write Isolation

| Rule | Description |
|------|-------------|
| **Authority boundary** | Each task owns exclusive write access to its output artifacts |
| **No cross-task writes** | Task A must NOT write to Task B's output path |
| **Shared resources** | If multiple tasks need same resource, use merge authority (not direct writes) |
| **Append-only** | Shared append targets (traces, memory) are safe for concurrent access |

---

## 5. Parallel Execution Model

### 5.1 Agent-to-Task Assignment

```
┌─────────────────────────────────────────────────┐
│              Task Queue (claimed)                 │
│  [T1:claimed:A] [T2:claimed:B] [T3:free]        │
└─────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌────────┐    ┌────────┐    ┌────────┐
    │Agent A │    │Agent B │    │(free)  │
    │Running │    │Running │    │Waiting │
    │  T1    │    │  T2    │    │        │
    └────────┘    └────────┘    └────────┘
         │              │
         ▼              ▼
    ┌─────────────────────────┐
    │   Merge Point (fan-in)   │
    │   Collect T1+T2 outputs  │
    │   Apply merge strategy   │
    └─────────────────────────┘
```

### 5.2 Parallel Execution States

```
queued → ready → claimed (lease) → running → [completed|failed|timeout]
                                                  │
                                                  ▼
                                          merge point (fan-in)
                                                  │
                                                  ▼
                                          [merged|merge_failed]
```

---

## 6. Current vs Target Parallelization

| Aspect | Current State | Target State |
|--------|--------------|--------------|
| Execution model | Single-threaded sequential | Multi-agent parallel with leases |
| Task claiming | No claiming (implicit ownership) | Lease-based explicit claiming |
| Heartbeat | No heartbeat monitoring | 60s heartbeat, 5min TTL |
| Idempotency | No idempotency keys | Idempotency on all write ops |
| Write isolation | Shared file writes (no isolation) | Authority-bound writes |
| Merge strategy | Implicit (last output wins) | Explicit merge with conflict resolution |
| Fan-out criteria | None (no parallelism) | Formal criteria (see §2) |
| Fan-in criteria | None (sequential only) | Formal criteria (see §3) |
| Coordination overhead | N/A (no parallelism) | Bounded by max parallel children (10) |

---

## 7. Resource Budgets for Parallel Execution

| Resource | Limit | Enforcement |
|----------|-------|-------------|
| Max parallel children per task | 10 | Decomposition validation |
| Max concurrent agents | 5 | Agent pool limit |
| Max parallel cost per task | $10 | Budget gate |
| Max parallel duration | 30 min | Timeout kill |
| Max total parallel cost (mission) | $500 | Mission budget gate |

---

## 8. Failure Modes in Parallel Execution

| Failure Mode | Detection | Recovery |
|-------------|-----------|----------|
| Agent crashes mid-task | Heartbeat timeout | Reassign task to new agent |
| Agent produces wrong output | Validation failure | Retry with different agent |
| Two agents claim same task | Lease conflict (CAS fails) | Loser retries on different task |
| Merge conflict (incompatible outputs) | Merge validation failure | Escalate to merge authority |
| Resource exhaustion (disk/memory) | Pre-execution check | Queue task until resources free |
| Budget exceeded mid-execution | Cost monitoring | Cancel lowest-priority tasks |
