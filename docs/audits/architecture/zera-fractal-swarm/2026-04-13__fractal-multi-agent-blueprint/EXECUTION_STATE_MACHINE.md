# Execution State Machine — Fractal Multi-Agent Architecture

> **Wave:** 4 — Target Execution Blueprint
> **Date:** 2026-04-13
> **Status:** Draft
> **Scope:** All execution-level entities (task, subtask, action, workflow, wave, run)

---

## 1. State Taxonomy

### 1.1 State Categories

States are grouped into 4 categories based on their semantics:

| Category | States | Semantics |
|----------|--------|-----------|
| **Pre-execution** | `queued`, `ready` | Entity exists but has not started execution |
| **In-execution** | `running`, `waiting`, `blocked` | Entity is actively executing or paused |
| **Post-execution** | `validating`, `completed`, `failed`, `compensated`, `escalated` | Entity has finished execution |
| **Recovery** | `replayed` | Entity is being re-executed after a failure or audit |

### 1.2 Complete State Set

```
queued ──▶ ready ──▶ running ──▶ validating ──▶ completed
               │         │                          ▲
               │         ├─▶ waiting ──▶ running ───┘
               │         │
               │         ├─▶ blocked ──▶ ready ──▶ ...
               │         │
               │         ├─▶ failed ──▶ replayed ──▶ ready ──▶ ...
               │         │                │
               │         │                ├─▶ completed (recovered)
               │         │                │
               │         │                └─▶ escalated
               │         │
               │         └─▶ escalated
               │
               └──▶ failed (immediate failure without execution)

completed ──▶ compensated (undo completed work)
```

---

## 2. State Diagram — Full Transition Map

### 2.1 Graph Notation

```
[state] --(transition_name; guard)--> [next_state]
```

### 2.2 Complete Transition Table

#### 2.2.1 Pre-execution Transitions

| # | From | To | Transition | Guard (Conditions) | Effect |
|---|------|----|------------|-------------------|--------|
| 1 | `queued` | `ready` | `enqueue` | All parent entities exist; entity is created with valid definition | Entity added to priority queue |
| 2 | `ready` | `running` | `acquire` | Lease granted; worker available; dependency resolver confirms all predecessors completed | Lease issued; worker assigned; span(open) emitted |
| 3 | `ready` | `failed` | `abort_pre_execution` | Entity definition invalid; required tools unavailable; policy gate denies | Failure event emitted; error reason recorded |

#### 2.2.2 In-execution Transitions

| # | From | To | Transition | Guard (Conditions) | Effect |
|---|------|----|------------|-------------------|--------|
| 4 | `running` | `validating` | `submit_for_validation` | Worker reports task complete; output artifacts written | Validation workflow triggered |
| 5 | `running` | `waiting` | `await_input` | Task declares input dependency not yet satisfied; explicit wait declared by task | Wait timer started; heartbeat pauses |
| 6 | `running` | `blocked` | `block` | External dependency unavailable (e.g., MCP server down, resource exhausted); not a task input dependency | Block reason recorded; lease extended or revoked |
| 7 | `running` | `failed` | `fail` | Error threshold exceeded; tool budget exhausted; timeout; worker crash; policy violation | Failure event emitted; retry budget checked; artifacts captured (if any) |
| 8 | `running` | `escalated` | `escalate` | Failure is non-recoverable; requires human intervention; C4/C5 task with audit failure | Escalation event; operator notified; execution paused |

#### 2.2.3 Recovery Transitions (from `waiting`)

| # | From | To | Transition | Guard (Conditions) | Effect |
|---|------|----|------------|-------------------|--------|
| 9 | `waiting` | `running` | `resume` | Awaited input becomes available; input dependency satisfied | Span(resume) emitted; worker re-engaged |
| 10 | `waiting` | `failed` | `wait_timeout` | Wait duration exceeds configured timeout | Failure event emitted; retry budget checked |

#### 2.2.4 Recovery Transitions (from `blocked`)

| # | From | To | Transition | Guard (Conditions) | Effect |
|---|------|----|------------|-------------------|--------|
| 11 | `blocked` | `ready` | `unblock` | External dependency restored; operator manually unblocks | Entity re-queued; priority preserved |
| 12 | `blocked` | `failed` | `block_timeout` | Block duration exceeds configured timeout | Failure event emitted; retry budget checked |

#### 2.2.5 Post-execution Transitions

| # | From | To | Transition | Guard (Conditions) | Effect |
|---|------|----|------------|-------------------|--------|
| 13 | `validating` | `completed` | `validate_pass` | All validation checks pass; output artifacts verified; checksum matches | Completed timestamp recorded; dependency resolver notified |
| 14 | `validating` | `failed` | `validate_fail` | Validation check fails; output artifact corrupted; checksum mismatch | Failure event emitted; retry budget checked |
| 15 | `failed` | `replayed` | `retry` | Retry budget not exhausted; retry policy permits retry for this failure type | Retry counter incremented; entity re-queued with backoff |
| 16 | `failed` | `escalated` | `escalate_on_retry_exhausted` | Retry budget exhausted; all retries failed | Escalation event; operator notified |
| 17 | `failed` | `compensated` | `compensate` | Compensation handler exists; compensation is required (e.g., rollback database migration) | Compensation action executed; compensation result recorded |
| 18 | `replayed` | `ready` | `replay_complete` | Replay execution scheduled; entity re-queued | Priority may be adjusted; replay counter incremented |
| 19 | `replayed` | `completed` | `replay_succeeded` | Replayed execution completes successfully (shortcut from `replayed` after validation) | Completed timestamp recorded |
| 20 | `completed` | `compensated` | `compensate_completed` | Operator requests rollback; or automatic compensation triggered by downstream failure | Compensation action executed |

#### 2.2.6 Escalation Resolution

| # | From | To | Transition | Guard (Conditions) | Effect |
|---|------|----|------------|-------------------|--------|
| 21 | `escalated` | `ready` | `resolve_escalation` | Operator reviews and approves retry; or operator modifies task and re-submits | Operator decision recorded; entity re-queued |
| 22 | `escalated` | `failed` | `abandon_escalation` | Operator decides to abandon; or entity is no longer relevant | Final failure recorded; mission status updated |

---

## 3. Terminal States

A terminal state is one from which no further state transitions are possible for the entity itself.

| Terminal State | Meaning | Propagation |
|----------------|---------|-------------|
| `completed` | Entity executed successfully. All validations passed. Artifacts stored. | Dependency resolver marks successors as potentially `ready` |
| `failed` | Entity execution failed and no further retries are permitted (budget exhausted or non-recoverable error). | Parent entity may transition to `failed` or `compensated` |
| `compensated` | Entity was completed but its work has been undone via compensation. | Parent entity notified; may trigger re-planning |
| `escalated` | Entity requires human intervention and has not yet been resolved. | Execution of dependent entities paused; operator alerted |

### 3.1 Terminal State Semantics

```
completed:   Success. Output is valid. Dependents may proceed.
failed:      Irrecoverable failure. Output is invalid. Dependents are blocked.
compensated: Output was valid but has been invalidated by compensation. Dependents must re-evaluate.
escalated:   State is unknown or unsafe. Dependents are frozen pending operator action.
```

---

## 4. Retry and Recovery Model

### 4.1 Retry Budget

Each entity has a **retry budget** defined by:

```yaml
retry_budget:
  max_retries: 3                    # Maximum retry attempts
  max_replay_retries: 1             # Additional retries for replayed executions
  backoff:
    type: exponential               # exponential, linear, constant
    base_seconds: 5                 # Initial delay
    multiplier: 2                   # Backoff multiplier
    max_seconds: 300                # Cap at 5 minutes
    jitter: true                    # Add random jitter (±20%)
  retryable_failures:               # Failure types eligible for retry
    - tool_timeout
    - mcp_server_unavailable
    - worker_crash
    - transient_validation_failure
  non_retryable_failures:           # Failure types that never retry
    - policy_violation
    - invalid_entity_definition
    - tool_not_found
    - budget_exceeded
    - operator_abort
```

### 4.2 Retry Decision Flow

```
Task fails
  │
  ▼
Is failure type in retryable_failures?
  │
  ├── NO ──▶ Transition to failed (terminal)
  │
  └── YES
       │
       ▼
Has retry_count < max_retries?
  │
  ├── NO ──▶ Transition to escalated (if C4/C5) or failed (if C1-C3)
  │
  └── YES
       │
       ▼
Calculate backoff delay
       │
       ▼
Transition to replayed
       │
       ▼
Replay complete: transition to ready
       │
       ▼
Acquire lease and re-execute
```

### 4.3 Recovery Paths Summary

| Failure Scenario | Recovery Path |
|-----------------|---------------|
| Transient tool failure | `running → failed → replayed → ready → running` |
| Missing input dependency | `running → waiting → running` (when input arrives) |
| External service down | `running → blocked → ready → running` (when service restored) |
| Validation failure (retryable) | `validating → failed → replayed → ready → running` |
| Worker crash | `running → failed → replayed → ready → running` (new worker) |
| Non-recoverable error | `running → failed` (terminal) or `running → escalated` (C4/C5) |
| Operator rollback | `completed → compensated` |
| Escalation resolved | `escalated → ready → running` (re-execute) or `escalated → failed` (abandon) |

---

## 5. State Persistence Model

### 5.1 Storage Layout

```
.agents/store/
├── runs/
│   └── {run_id}/
│       ├── state.json              # Run-level state
│       ├── waves/
│       │   └── {wave_id}/
│       │       ├── state.json      # Wave-level state
│       │       ├── workflows/
│       │       │   └── {wf_id}/
│       │       │       ├── state.json            # Workflow state
│       │       │       ├── tasks/
│       │       │       │   └── {task_id}/
│       │       │       │       ├── state.json    # Task state (single source of truth)
│       │       │       │       ├── events.jsonl  # Append-only event log
│       │       │       │       ├── spans.jsonl   # Append-only span log
│       │       │       │       ├── artifacts/    # Output files
│       │       │       │       └── checkpoints/  # Checkpoint files
│       │       │       └── ...
│       │       └── ...
│       └── ...
└── ...
```

### 5.2 State File Format

Each `state.json` file contains the current state of the entity:

```json
{
  "id": "task_abc123",
  "entity_type": "task",
  "state": "running",
  "state_history": [
    {"state": "queued", "timestamp": "2026-04-13T10:00:00Z", "transition": "enqueue"},
    {"state": "ready", "timestamp": "2026-04-13T10:00:01Z", "transition": "enqueue"},
    {"state": "running", "timestamp": "2026-04-13T10:00:02Z", "transition": "acquire"}
  ],
  "lease": {
    "worker_id": "worker_1",
    "issued_at": "2026-04-13T10:00:02Z",
    "expires_at": "2026-04-13T10:05:02Z",
    "heartbeats": [
      {"timestamp": "2026-04-13T10:02:00Z"},
      {"timestamp": "2026-04-13T10:04:00Z"}
    ]
  },
  "retry": {
    "count": 0,
    "max_retries": 3,
    "last_failure": null
  },
  "dependencies": ["task_xyz789"],
  "created_at": "2026-04-13T10:00:00Z",
  "updated_at": "2026-04-13T10:00:02Z"
}
```

### 5.3 Write Semantics

| Property | Rule |
|----------|------|
| **Append-only** | Events and spans are append-only JSONL files. Never modified after write. |
| **Atomic state** | `state.json` is written atomically (write to `.tmp`, then rename). |
| **No in-place edits** | Historical state entries in `state_history` are never modified. |
| **Idempotent writes** | Writing the same event twice (same `event_id`) is a no-op. |
| **Lease atomicity** | Lease acquisition uses file-based locking (`fcntl.flock`) in single-process mode. |

### 5.4 Crash Recovery

On process restart, the system rebuilds in-memory state from the on-disk state:

```
1. Scan .agents/store/ for all state.json files
2. Rebuild entity tree from state files
3. For each entity with state == "running":
   a. Check if lease is still valid (not expired)
   b. If lease valid: re-assign to worker, request heartbeat
   c. If lease expired: transition to failed → replayed → ready (re-dispatch)
4. For each entity with state == "waiting" or "blocked":
   a. Re-evaluate conditions
   b. If condition resolved: transition to ready
   c. If condition still holds: preserve state
5. Drain priority queue and resume dispatch
```

### 5.5 State Transition Invariants

| Invariant | Enforcement |
|-----------|-------------|
| **No backward transitions** | State transitions only move forward in the DAG. Exception: `replayed` → `ready` (explicit recovery). |
| **No skip transitions** | Each transition must pass through its guard. No direct `queued` → `completed`. |
| **Terminal states are terminal** | Once in a terminal state, no further transitions except operator-initiated compensation or escalation resolution. |
| **Lease-state consistency** | An entity in `running` MUST have a valid lease. An entity with an expired lease MUST NOT remain in `running`. |
| **Dependency-ordering** | An entity cannot transition to `running` until all dependencies are in `completed`. |

---

## 6. Heartbeat Protocol

### 6.1 Heartbeat Schedule

```
Worker claims lease
  │
  ▼
Heartbeat interval: 30 seconds (configurable per tier)
  │
  ▼
┌─────────────────────────────────────────────┐
│ Every 30s: Worker sends heartbeat           │
│   │                                          │
│   ├── Success: Lease extended by 60s        │
│   │                                          │
│   └── Missed:                                │
│       │                                      │
│       ├── 1 miss (60s overdue): Warning     │
│       │                                      │
│       ├── 2 misses (90s overdue): Revoke    │
│       │     lease, transition to failed      │
│       │                                      │
│       └── Worker crash detected:             │
│             Immediate lease revocation       │
└─────────────────────────────────────────────┘
```

### 6.2 Heartbeat Failure Handling

| Miss Count | Time Since Last Heartbeat | Action |
|------------|--------------------------|--------|
| 0 | ≤ 30s | Normal operation |
| 1 | 30-60s | Warning logged; worker monitored |
| 2 | 60-90s | Lease revoked; task failed; replay queued |
| 3+ | > 90s | Task escalated (if C4/C5) or abandoned (if C1-C3) |

---

## 7. State Machine per Entity Type

Not all entity types support all states. The following table shows which states are valid for each entity type:

| State | run | wave | workflow | task | subtask | action | tool_call |
|-------|:---:|:----:|:--------:|:----:|:-------:|:------:|:---------:|
| `queued` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ready` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `running` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `waiting` | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ |
| `blocked` | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ | ✗ |
| `validating` | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ |
| `completed` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `failed` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `compensated` | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| `escalated` | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ |
| `replayed` | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ |

**Notes:**
- `run` and `wave` do not support `waiting`/`blocked` — they are aggregation entities.
- `tool_call` does not support `waiting`/`blocked`/`validating`/`replayed` — it is an atomic invocation.
- `action` does not support `validating` — validation is at the task level.
- `compensated` is only meaningful for entities with side effects (run, wave, task).
