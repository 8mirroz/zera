# Delegation & Stop Rules — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Status:** Target design (governs all delegation decisions)  

---

## 1. Delegation Rules

### 1.1 When to Delegate (Split)

A parent entity **MUST** delegate to children when **ANY** of these conditions is true:

| Condition | Rule | Target Level |
|-----------|------|-------------|
| Task requires >3 distinct operations | Split into subtasks (1 per operation) | Task → Subtask |
| Task touches >2 code modules | Split into subtasks (1 per module) | Task → Subtask |
| Task has parallelizable dependencies | Split into parallel subtasks | Task → Subtask |
| Task duration estimate >5 minutes | Split into smaller tasks | Task → Subtask |
| Task complexity ≥ C4 | Must have subtasks for each major component | Task → Subtask |
| Program spans >1 workflow | Split into workflows (1 per workstream) | Program → Workflow |
| Mission spans >1 functional domain | Split into programs (1 per domain) | Mission → Program |

### 1.2 When NOT to Delegate (Don't Split)

A parent entity **MUST NOT** delegate when **ALL** of these conditions are true:

| Condition | Rule |
|-----------|------|
| Single operation, single module, <1 minute | Keep as atomic action |
| Child would have identical inputs/outputs to parent | No value in splitting |
| Splitting increases coordination overhead > benefit | Keep consolidated |
| Parent is already at level 5 (atomic) | Cannot split further |

### 1.3 Delegation Handoff Contract

When delegating, the parent **MUST** provide each child:

```yaml
handoff:
  from: "parent-task-id"
  to: "child-task-id"
  contract:
    objective: "<inherited or refined objective>"
    inputs: "<filtered input set for this child>"
    constraints: "<inherited constraints>"
    expected_outputs: "<expected output from this child>"
    validation: "<how child output will be validated>"
    deadline: "<optional time bound>"
    escalation_path: "<who to contact if stuck>"
```

### 1.4 Handoff Validation

| Check | Rule |
|-------|------|
| Objective inherited | Child objective must be subset of parent objective |
| Inputs available | All child inputs must exist or be produced by sibling |
| Constraints consistent | Child constraints must not contradict parent |
| Outputs contribute | Child outputs must contribute to parent acceptance criteria |
| No orphan children | Every child must have exactly 1 parent |

---

## 2. Stop Rules

### 2.1 Automatic Stop Conditions

| Condition | Trigger | Action |
|-----------|---------|--------|
| Max retries exceeded | `retries >= max_retries` | Stop task → mark `failed` → escalate |
| Budget exceeded | `cost_usd > budget_limit` | Stop task → emit `budget_exceeded` → escalate |
| Stop signal detected | `StopController.has_active_signal(scope)` | Stop task → mark `stopped` |
| Parent failed | `parent.state == "failed"` | Stop task → mark `blocked` |
| Dependency failed | Any `dependencies[].state == "failed"` | Stop task → mark `blocked` |
| Lease expired + cannot renew | `heartbeat_at + TTL < now` and renewal fails | Stop task → mark `failed` |
| Max depth reached | `level == "atomic"` | Stop decomposition → execute |
| Time budget exceeded | `started_at + duration_limit < now` | Stop task → mark `timeout` |

### 2.2 Manual Stop Conditions (Human Intervention)

| Condition | Trigger | Action |
|-----------|---------|--------|
| Schema validation fails repeatedly | >3 consecutive validation failures | Human reviews contract |
| Conflict unresolvable | Merge detects irreconcilable outputs | Human arbitrates |
| Unexpected behavior | Agent produces output not matching expected_outputs | Human reviews and decides |
| Quality gate failure | Validation fails after retries | Human decides: retry, accept, or reject |

### 2.3 Stop Cascade

When a task stops, the cascade propagates upward:

```
Atomic Action stops
  → Subtask checks: "All children complete?" → If no, Subtask stops
    → Task checks: "All children complete?" → If no, Task stops
      → Workflow checks: "All children complete?" → If no, Workflow stops
        → Program checks: "All children complete?" → If no, Program stops
          → Mission checks: "All children complete?" → If no, Mission stops
```

**Exception:** If stop reason is `child_failed` and parent has `retry_enabled`, parent may retry with different parameters before cascading.

---

## 3. Merge Rules

### 3.1 When to Merge

| Condition | Rule |
|-----------|------|
| All parallel children completed | Merge outputs into parent expected_outputs |
| All serial children completed | Merge sequentially (order = dependency order) |
| Partial completion + timeout | Merge completed; mark incomplete as failed |
| All children failed | Merge as "all failed" → escalate |

### 3.2 Merge Authority

| Scenario | Merge Authority | Conflict Resolution |
|----------|----------------|-------------------|
| Single owner (all children same agent) | Task owner merges | Owner decides |
| Multiple owners (parallel agents) | Task owner (highest authority) | Owner decides; conflicts escalated |
| Conflicting outputs | Task owner + review | If unresolved → Council (C5) |
| Missing output from child | Task owner decides: retry or accept partial | Owner's decision logged |

### 3.3 Merge Contract

```yaml
merge:
  parent_id: "task-<uuid>"
  children_completed: ["task-child-1", "task-child-2", ...]
  children_failed: ["task-child-3", ...]
  merge_strategy: "sequential|parallel|best_of_n|consensus"
  merged_outputs:
    - id: "artifact-merged"
      source: ["task-child-1", "task-child-2"]
      conflict_resolution: "<how conflicts were resolved>"
  merge_result: "success|partial|failure"
  merge_evidence:
    - path: "<merge log/trace>"
      timestamp: "<ISO-8601>"
```

---

## 4. Escalation Rules

### 4.1 Escalation Path

```
Atomic Action → Subtask → Task → Workflow → Program → Mission → Council (C5)
```

### 4.2 Escalation Triggers

| Trigger | Escalate To | Time Limit |
|---------|------------|------------|
| Max retries at level N | Level N+1 owner | Immediate |
| Budget exceeded | Program owner | Immediate |
| Conflict unresolvable | Task owner → Council (C5) | 5 min → 30 min |
| Schema validation fails | Parent level | Immediate |
| Stop signal (scope=global) | Mission owner | Immediate |
| Agent unresponsive (no heartbeat) | Task owner | After TTL expires |

### 4.3 Escalation Contract

```yaml
escalation:
  from: "task-<uuid>"
  to: "<escalation target>"
  reason: "<why escalating>"
  evidence:
    - "<trace/log/screenshot>"
  context:
    retries: N
    cost_usd: X
    duration_ms: Y
    attempts: ["<attempt 1 summary>", "<attempt 2 summary>", ...]
  requested_action: "retry|override|cancel|reassign|review"
  timestamp: "<ISO-8601>"
```

---

## 5. Recursion Limits

| Parameter | Limit | Rationale |
|-----------|-------|-----------|
| Max decomposition depth | 6 levels (Mission → Atomic) | Prevents infinite decomposition |
| Max retries per level | 3 (configurable per task) | Prevents retry loops |
| Max parallel children | 10 (configurable per task) | Prevents resource exhaustion |
| Max escalation hops | 6 (to Council) | Prevents escalation loops |
| Max task tree size | 1000 entities | Prevents memory exhaustion |
| Max task tree depth | 6 (same as decomposition depth) | Consistency check |

---

## 6. Decision Tree Summary

```
Task arrives
    │
    ├─ Is it atomic? ──YES──→ Execute
    │
    NO
    │
    ├─ Should it split?
    │   ├─ YES → Create children → Validate contracts → Delegate
    │   │                              │
    │   │                              ├─ All children complete? ──YES──→ Merge
    │   │                              │                                   │
    │   │                              NO                                  ├─ Merge success? ──YES──→ Complete
    │   │                              │                                   │                        NO
    │   │                              │                                   │                         │
    │   │                              │                                   NO                         Escalate
    │   │                              │                                   │
    │   │                              │                                   └─ Stop conditions met? ──YES──→ Stop cascade
    │   │                              │
    │   │                              └─ Child failed? ──YES──→ Retry (if retries < max)
    │   │                                                     │            NO
    │   │                                                     NO           │
    │   │                                                     │            Escalate
    │   │                                                     │
    │   │                        Stop conditions met? ──YES──→ Stop cascade
    │   │
    │   NO → Execute as single unit
    │
    └─ Stop conditions met? ──YES──→ Stop cascade
```
