# Task Contract Schema — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Status:** Target schema (for all task levels: Mission → Atomic Action)  

---

## 1. Schema Definition (YAML)

```yaml
# Task Contract v1.0
# Applies to: Mission, Program, Workflow, Task, Subtask, Atomic Action
# All levels share this schema; only field values differ.

$schema: "https://antigravity-core/schemas/task-contract/v1"
version: "1.0"

# ── Identity ──────────────────────────────────────────────
id: "task-<uuid>"                          # Unique identifier
parent_id: "task-<uuid> | null"            # Parent entity (null for Mission)
level: "mission|program|workflow|task|subtask|atomic"
tier: "C1|C2|C3|C4|C5"                     # Complexity tier (inherited from parent)

# ── Objective ─────────────────────────────────────────────
objective: "<string>"                      # What must be achieved
acceptance_criteria:                       # How we know it's done
  - "<testable criterion 1>"
  - "<testable criterion 2>"

# ── Inputs ────────────────────────────────────────────────
inputs:
  - id: "artifact-<id>"
    type: "file|config|memory|artifact|trace"
    path: "<relative or absolute path>"
    required: true|false
    description: "<what this input provides>"

# ── Constraints ───────────────────────────────────────────
constraints:
  - type: "time|resource|scope|quality|security"
    limit: "<description or numeric>"
    enforcement: "hard|soft"               # hard = stop if violated; soft = warn

# ── Dependencies ──────────────────────────────────────────
dependencies:
  - id: "task-<uuid>"                      # Tasks that must complete first
    type: "serial|parallel"                # serial = wait; parallel = can overlap
    condition: "success|any|all"           # What state triggers this task

# ── Expected Outputs ──────────────────────────────────────
expected_outputs:
  - id: "artifact-<id>"
    type: "file|config|memory|artifact|report"
    path: "<expected output path>"
    format: "<file format or schema ref>"
    required: true|false

# ── Validation ────────────────────────────────────────────
validation:
  type: "test|schema|review|benchmark|manual"
  method: "<how to validate>"
  threshold: "<pass criteria>"
  auto_validate: true|false                # Can validation run automatically?

# ── Rollback / Compensation ──────────────────────────────
rollback:
  enabled: true|false
  strategy: "delete|restore|compensate|none"
  target: "<what to rollback>"
  preconditions: "<when rollback is safe>"

# ── Evidence ──────────────────────────────────────────────
evidence:                                  # Populated during execution
  - type: "trace|log|screenshot|test_result|review"
    path: "<path to evidence>"
    timestamp: "<ISO-8601>"
    verified: true|false

# ── Artifact References ───────────────────────────────────
artifact_refs:                             # All files/configs touched
  - path: "<path>"
    action: "create|modify|delete|read"
    checksum: "<sha256 after execution>"

# ── Runtime Metadata ─────────────────────────────────────
runtime:
  assigned_to: "<agent_id | null>"         # Who executes this
  claimed_at: "<ISO-8601 | null>"          # Lease timestamp
  heartbeat_at: "<ISO-8601 | null>"        # Last heartbeat
  started_at: "<ISO-8601 | null>"
  completed_at: "<ISO-8601 | null>"
  state: "queued|ready|running|waiting|blocked|validating|completed|failed|compensated|escalated|replayed"
  retries: 0                               # Retry count
  max_retries: 3                           # Maximum retries allowed
  cost_usd: 0.0                            # Accumulated cost
  duration_ms: 0                           # Execution duration
```

---

## 2. Schema Validation Rules

| Rule | Condition | Error |
|------|-----------|-------|
| ID format | Must match `task-<uuid>` pattern | `invalid_id_format` |
| Parent reference | If parent_id set, parent must exist | `parent_not_found` |
| Level consistency | Children level must be exactly 1 below parent | `level_mismatch` |
| Objective | Must be non-empty string, >10 chars | `empty_objective` |
| Acceptance criteria | Must have ≥1 criterion, each testable | `no_acceptance_criteria` |
| Input paths | Referenced files must exist (if required) | `missing_required_input` |
| Dependency graph | No cycles allowed | `dependency_cycle` |
| Output paths | Must be within workspace bounds | `output_path_violation` |
| Rollback strategy | Must be valid strategy name | `invalid_rollback_strategy` |
| State transitions | Must follow state machine (see Wave 4) | `invalid_state_transition` |

---

## 3. Examples

### 3.1 Mission-Level Contract

```yaml
id: "mission-build-platform"
parent_id: null
level: mission
tier: C5
objective: "Build Antigravity Core v5.0 — a fractal multi-agent autonomous development platform"
acceptance_criteria:
  - "All 10 subsystems pass integration tests"
  - "Dashboard shows real-time execution state"
  - "Trace pipeline handles 10K events/min without loss"
  - "Fractal decomposition produces valid trees for C1–C5 tasks"
inputs:
  - id: "artifact-router-yaml"
    type: config
    path: "configs/orchestrator/router.yaml"
    required: true
    description: "Current routing configuration"
constraints:
  - type: time
    limit: "4 weeks"
    enforcement: soft
  - type: resource
    limit: "Budget: $500 LLM costs"
    enforcement: hard
dependencies: []
expected_outputs:
  - id: "artifact-platform-v5"
    type: artifact
    path: "repos/"
    format: "codebase"
    required: true
validation:
  type: benchmark
  method: "Run full benchmark suite"
  threshold: "All scores ≥ 0.85"
  auto_validate: true
rollback:
  enabled: true
  strategy: restore
  target: "git revert to pre-mission snapshot"
  preconditions: "No production traffic on new code"
evidence: []
artifact_refs: []
runtime:
  assigned_to: null
  state: queued
  retries: 0
  max_retries: 1
```

### 3.2 Task-Level Contract

```yaml
id: "task-implement-leases"
parent_id: "workflow-instrumentation"
level: task
tier: C4
objective: "Implement lease + heartbeat mechanism for parallel task claiming"
acceptance_criteria:
  - "Task can be claimed with lease (TTL 5 min)"
  - "Lease extends on heartbeat"
  - "Expired lease can be claimed by another agent"
  - "Concurrent claims for same task fail (one wins)"
inputs:
  - id: "artifact-state-json"
    type: file
    path: ".agents/runtime/tasks.json"
    required: true
    description: "Task state store"
  - id: "artifact-trace-schema"
    type: config
    path: "configs/tooling/trace_schema.json"
    required: true
    description: "Trace event schema for lease events"
constraints:
  - type: scope
    limit: "Only modify .agents/runtime/ and agent_os/runtime_providers/"
    enforcement: hard
  - type: quality
    limit: "Must pass all existing tests"
    enforcement: hard
dependencies:
  - id: "task-add-trace-fields"
    type: serial
    condition: success
expected_outputs:
  - id: "artifact-lease-module"
    type: file
    path: "repos/packages/agent-os/src/agent_os/swarm/lease.py"
    format: "python"
    required: true
  - id: "artifact-lease-tests"
    type: file
    path: "repos/packages/agent-os/tests/test_lease.py"
    format: "python"
    required: true
validation:
  type: test
  method: "pytest repos/packages/agent-os/tests/test_lease.py"
  threshold: "All tests pass"
  auto_validate: true
rollback:
  enabled: true
  strategy: delete
  target: "Remove lease.py and test_lease.py"
  preconditions: "No other task depends on lease module"
evidence: []
artifact_refs: []
runtime:
  assigned_to: "agent-engineer-01"
  claimed_at: "2026-04-13T10:00:00Z"
  heartbeat_at: "2026-04-13T10:04:30Z"
  state: running
  retries: 0
  max_retries: 3
  cost_usd: 0.05
  duration_ms: 270000
```

### 3.3 Atomic Action Contract

```yaml
id: "action-read-router-yaml"
parent_id: "subtask-parse-routing-config"
level: atomic
tier: C1
objective: "Read configs/orchestrator/router.yaml and return parsed content"
acceptance_criteria:
  - "File exists and is readable"
  - "Content parses as valid YAML"
  - "Parsed dict contains 'routing' key"
inputs:
  - id: "artifact-router-yaml"
    type: file
    path: "configs/orchestrator/router.yaml"
    required: true
    description: "Router configuration"
constraints:
  - type: time
    limit: "1 second"
    enforcement: soft
dependencies: []
expected_outputs:
  - id: "artifact-parsed-router"
    type: memory
    path: null
    format: "python dict"
    required: true
validation:
  type: schema
  method: "Validate parsed dict against router schema"
  threshold: "No validation errors"
  auto_validate: true
rollback:
  enabled: false
  strategy: none
  target: null
  preconditions: null
evidence: []
artifact_refs:
  - path: "configs/orchestrator/router.yaml"
    action: read
    checksum: null
runtime:
  assigned_to: null
  state: queued
  retries: 0
  max_retries: 1
  cost_usd: 0.0
  duration_ms: 0
```

---

## 4. Contract Lifecycle

```
Created → Validated → Queued → Ready → Claimed (lease) → Running
    ↓         ↓          ↓        ↓         ↓               ↓
  Invalid  Validation  Blocked  Waiting  Heartbeat     Completed/Failed
  (reject)  (reject)    ↑        ↑        ↓               ↓
                     Retry     Timeout  Expired       Validating
                                                       ↓
                                                 Completed/Failed
                                                      (final)
```
