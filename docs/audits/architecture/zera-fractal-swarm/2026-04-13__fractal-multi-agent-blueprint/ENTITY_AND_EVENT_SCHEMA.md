# Entity and Event Schema — Fractal Multi-Agent Architecture

> **Wave:** 4 — Target Execution Blueprint
> **Date:** 2026-04-13
> **Status:** Draft
> **Aligned with:** `trace_schema.json` v2.1

---

## 1. Entity Hierarchy

```
Mission (level 0)
  └── Program (level 1)
        └── Wave (level 2)
              └── Workflow (level 3)
                    └── Task (level 4)
                          ├── Subtask (level 5)
                          │     └── Action (level 6)
                          │           └── ToolCall (level 7)
                          ├── Span
                          └── Event

Artifacts and Checkpoints are associated with any entity.
```

**Note:** Mission and Program are logical groupings managed by the Mission Planner. The execution engine operates at the Wave level and below.

---

## 2. Entity Schemas

### 2.1 Run

A `run` represents a single invocation of the system with a mission.

```json
{
  "type": "run",
  "$schema": "https://antigravity.local/schemas/v2/run.json",
  "run_id": "run_2026041310000001",
  "mission": {
    "description": "Implement dark mode for the settings page",
    "classification": "C3",
    "source": "cli",
    "initiator": "user",
    "context": {
      "working_directory": "/Users/user/zera",
      "branch": "feature/dark-mode",
      "base_commit": "abc123"
    }
  },
  "state": "running",
  "created_at": "2026-04-13T10:00:00Z",
  "started_at": "2026-04-13T10:00:01Z",
  "completed_at": null,
  "programs": ["prog_001"],
  "metadata": {
    "engine_version": "4.2.0",
    "platform": "darwin",
    "python_version": "3.12"
  }
}
```

### 2.2 Wave

A `wave` is a set of workflows that can execute in parallel. Waves execute sequentially within a run.

```json
{
  "type": "wave",
  "wave_id": "wave_001",
  "run_id": "run_2026041310000001",
  "state": "running",
  "workflows": ["wf_001", "wf_002", "wf_003"],
  "dependency_graph": {},
  "created_at": "2026-04-13T10:00:01Z",
  "started_at": "2026-04-13T10:00:02Z",
  "completed_at": null,
  "metadata": {
    "decomposition_algorithm": "deterministic_dag",
    "parallelism_level": 3
  }
}
```

### 2.3 Workflow

A `workflow` is a named sequence of tasks with internal dependencies.

```json
{
  "type": "workflow",
  "workflow_id": "wf_001",
  "wave_id": "wave_001",
  "run_id": "run_2026041310000001",
  "name": "implement-dark-mode",
  "state": "running",
  "tasks": ["task_001", "task_002", "task_003"],
  "dependency_graph": {
    "task_001": [],
    "task_002": ["task_001"],
    "task_003": ["task_001"]
  },
  "created_at": "2026-04-13T10:00:02Z",
  "started_at": "2026-04-13T10:00:03Z",
  "completed_at": null,
  "metadata": {
    "source": ".agents/workflows/implement-dark-mode.yaml",
    "tier": "C3"
  }
}
```

### 2.4 Task

A `task` is the primary unit of work. Tasks are leased to workers and executed.

```json
{
  "type": "task",
  "task_id": "task_001",
  "workflow_id": "wf_001",
  "wave_id": "wave_001",
  "run_id": "run_2026041310000001",
  "correlation_id": "corr_run001_wave001_wf001_task001",
  "name": "analyze-current-theming",
  "state": "running",
  "tier": "C3",
  "priority": 1,
  "definition": {
    "prompt": "Analyze the current theming system and identify all files that need modification for dark mode support.",
    "tools": ["mcp:filesystem", "mcp:context7", "shell:grep"],
    "tool_budget": 12,
    "timeout_seconds": 600,
    "expected_artifacts": ["analysis_report.md"]
  },
  "subtasks": ["subtask_001", "subtask_002"],
  "dependencies": [],
  "lease": {
    "worker_id": "worker_1",
    "issued_at": "2026-04-13T10:00:03Z",
    "expires_at": "2026-04-13T10:05:03Z",
    "heartbeats": 2
  },
  "retry": {
    "count": 0,
    "max_retries": 3,
    "last_failure_type": null,
    "last_failure_message": null
  },
  "created_at": "2026-04-13T10:00:02Z",
  "started_at": "2026-04-13T10:00:03Z",
  "completed_at": null,
  "metadata": {
    "agent_role": "analyst",
    "skill_required": "design-system-architect"
  }
}
```

### 2.5 Subtask

A `subtask` is an optional decomposition of a task for parallel execution.

```json
{
  "type": "subtask",
  "subtask_id": "subtask_001",
  "task_id": "task_001",
  "workflow_id": "wf_001",
  "run_id": "run_2026041310000001",
  "correlation_id": "corr_run001_wave001_wf001_task001_sub001",
  "name": "analyze-css-variables",
  "state": "completed",
  "definition": {
    "prompt": "Identify all CSS variable definitions in the design system.",
    "tools": ["mcp:filesystem", "shell:grep"],
    "tool_budget": 8,
    "timeout_seconds": 300
  },
  "actions": ["action_001", "action_002"],
  "dependencies": [],
  "retry": {
    "count": 0,
    "max_retries": 3
  },
  "created_at": "2026-04-13T10:00:03Z",
  "started_at": "2026-04-13T10:00:04Z",
  "completed_at": "2026-04-13T10:02:15Z"
}
```

### 2.6 Action

An `action` is an atomic operation within a subtask.

```json
{
  "type": "action",
  "action_id": "action_001",
  "subtask_id": "subtask_001",
  "task_id": "task_001",
  "run_id": "run_2026041310000001",
  "correlation_id": "corr_run001_wave001_wf001_task001_sub001_act001",
  "name": "search-css-files",
  "state": "completed",
  "definition": {
    "operation": "search",
    "target": "mcp:filesystem",
    "parameters": {
      "path": "repos/packages/design-system/",
      "pattern": "**/*.css"
    }
  },
  "tool_calls": ["tc_001"],
  "state": "completed",
  "created_at": "2026-04-13T10:00:04Z",
  "completed_at": "2026-04-13T10:00:05Z"
}
```

### 2.7 ToolCall

A `tool_call` is a single invocation of a tool. The most granular entity.

```json
{
  "type": "tool_call",
  "tool_call_id": "tc_001",
  "action_id": "action_001",
  "subtask_id": "subtask_001",
  "task_id": "task_001",
  "run_id": "run_2026041310000001",
  "correlation_id": "corr_run001_wave001_wf001_task001_sub001_act001_tc001",
  "tool_name": "mcp:filesystem",
  "tool_method": "read_file",
  "tool_parameters": {
    "path": "/Users/user/zera/repos/packages/design-system/tokens.css"
  },
  "state": "completed",
  "result": {
    "status": "success",
    "output_length": 4521,
    "error": null
  },
  "created_at": "2026-04-13T10:00:04Z",
  "completed_at": "2026-04-13T10:00:05Z",
  "latency_ms": 45
}
```

---

## 3. Observability Schemas

### 3.1 Span

A `span` represents a timed operation. Aligned with `trace_schema.json` v2.1.

```json
{
  "type": "span",
  "span_id": "span_001",
  "parent_span_id": null,
  "trace_id": "trace_run001",
  "correlation_id": "corr_run001_wave001_wf001_task001",
  "entity_id": "task_001",
  "entity_type": "task",
  "run_id": "run_2026041310000001",
  "name": "task.execute",
  "kind": "internal",
  "start_time": "2026-04-13T10:00:03.000Z",
  "end_time": "2026-04-13T10:02:15.000Z",
  "duration_ms": 132000,
  "status": "ok",
  "attributes": {
    "worker_id": "worker_1",
    "tier": "C3",
    "tools_used": ["mcp:filesystem", "mcp:context7"],
    "tool_call_count": 5
  },
  "events": [
    {
      "name": "task.started",
      "timestamp": "2026-04-13T10:00:03.000Z"
    },
    {
      "name": "task.completed",
      "timestamp": "2026-04-13T10:02:15.000Z"
    }
  ]
}
```

### 3.2 Event

An `event` is an immutable, timestamped record of something that happened.

```json
{
  "type": "event",
  "event_id": "evt_001",
  "event_type": "task.state_transition",
  "timestamp": "2026-04-13T10:00:03.000Z",
  "run_id": "run_2026041310000001",
  "correlation_id": "corr_run001_wave001_wf001_task001",
  "entity_id": "task_001",
  "entity_type": "task",
  "severity": "info",
  "payload": {
    "from_state": "ready",
    "to_state": "running",
    "transition": "acquire",
    "worker_id": "worker_1",
    "lease_id": "lease_001"
  },
  "source": "scheduler",
  "tags": ["state_transition", "task_lifecycle"]
}
```

### 3.3 Event Type Catalog

| Event Type | Payload Fields | Source | Severity |
|------------|---------------|--------|----------|
| `task.state_transition` | `from_state`, `to_state`, `transition` | Scheduler | `info` |
| `task.lease_granted` | `worker_id`, `lease_id`, `expires_at` | Lease Manager | `info` |
| `task.lease_expired` | `worker_id`, `lease_id`, `reason` | Lease Manager | `warn` |
| `task.heartbeat` | `worker_id`, `lease_id` | Worker | `debug` |
| `task.heartbeat_missed` | `worker_id`, `miss_count` | Lease Manager | `warn` |
| `tool_call.started` | `tool_name`, `tool_method`, `parameters_hash` | Worker | `debug` |
| `tool_call.completed` | `tool_name`, `status`, `latency_ms`, `output_length` | Worker | `info` |
| `tool_call.failed` | `tool_name`, `error_type`, `error_message` | Worker | `error` |
| `artifact.created` | `artifact_id`, `entity_id`, `artifact_type`, `size_bytes` | Worker | `info` |
| `checkpoint.created` | `checkpoint_id`, `entity_id`, `checkpoint_type` | Worker | `info` |
| `dependency.resolved` | `task_id`, `dependency_id`, `resolution_time` | Dependency Resolver | `info` |
| `retry.initiated` | `entity_id`, `retry_count`, `backoff_seconds` | Retry Handler | `warn` |
| `escalation.raised` | `entity_id`, `reason`, `tier` | Scheduler | `error` |
| `escalation.resolved` | `entity_id`, `resolution`, `operator_id` | Policy Engine | `info` |
| `safe_mode.activated` | `reason`, `affected_count` | Policy Engine | `critical` |
| `safe_mode.deactivated` | `reason` | Policy Engine | `info` |
| `policy_gate.blocked` | `entity_id`, `gate_name`, `reason` | Policy Engine | `warn` |
| `policy_gate.passed` | `entity_id`, `gate_name` | Policy Engine | `info` |
| `drift.detected` | `metric`, `expected`, `actual`, `deviation_pct` | Drift Detector | `warn` |
| `worker.registered` | `worker_id`, `capabilities` | Worker Pool | `info` |
| `worker.deregistered` | `worker_id`, `reason` | Worker Pool | `warn` |

---

## 4. Artifact Schema

An `artifact` is a file or data object produced by an entity.

```json
{
  "type": "artifact",
  "artifact_id": "art_001",
  "entity_id": "task_001",
  "entity_type": "task",
  "run_id": "run_2026041310000001",
  "correlation_id": "corr_run001_wave001_wf001_task001",
  "name": "analysis_report.md",
  "artifact_type": "file",
  "mime_type": "text/markdown",
  "size_bytes": 4521,
  "path": ".agents/store/runs/run_001/waves/wave_001/workflows/wf_001/tasks/task_001/artifacts/analysis_report.md",
  "checksum_sha256": "a1b2c3d4e5f6...",
  "lineage": {
    "produced_by": "task_001",
    "workflow_id": "wf_001",
    "wave_id": "wave_001",
    "run_id": "run_2026041310000001",
    "tool_calls": ["tc_001", "tc_002", "tc_003"]
  },
  "created_at": "2026-04-13T10:02:15Z",
  "metadata": {
    "description": "Analysis of current theming system",
    "tags": ["analysis", "theming"]
  }
}
```

---

## 5. Checkpoint Schema

A `checkpoint` captures the execution state at a point in time for recovery.

```json
{
  "type": "checkpoint",
  "checkpoint_id": "ckpt_001",
  "entity_id": "task_001",
  "entity_type": "task",
  "run_id": "run_2026041310000001",
  "checkpoint_type": "state_snapshot",
  "state": {
    "task_state": "running",
    "subtasks_completed": ["subtask_001"],
    "subtasks_remaining": ["subtask_002"],
    "artifacts_produced": ["art_001"],
    "tool_calls_made": ["tc_001", "tc_002"]
  },
  "created_at": "2026-04-13T10:01:00Z",
  "path": ".agents/store/runs/run_001/waves/wave_001/workflows/wf_001/tasks/task_001/checkpoints/ckpt_001.json",
  "metadata": {
    "trigger": "periodic",
    "interval_seconds": 60
  }
}
```

---

## 6. Correlation ID Scheme

### 6.1 Format

```
corr_{run_id}_{wave_id}_{workflow_id}_{task_id}_{subtask_id}_{action_id}_{toolcall_id}
```

### 6.2 Examples

| Entity | Correlation ID |
|--------|---------------|
| Run | `corr_run001` |
| Wave | `corr_run001_wave001` |
| Workflow | `corr_run001_wave001_wf001` |
| Task | `corr_run001_wave001_wf001_task001` |
| Subtask | `corr_run001_wave001_wf001_task001_sub001` |
| Action | `corr_run001_wave001_wf001_task001_sub001_act001` |
| ToolCall | `corr_run001_wave001_wf001_task001_sub001_act001_tc001` |

### 6.3 Usage Rules

1. Every event and span MUST include a `correlation_id`.
2. The `correlation_id` enables tracing from any entity up to the root run.
3. Correlation IDs are deterministic: given the entity IDs, the correlation ID is computable.
4. When querying for all events related to a task, filter by `correlation_id` prefix matching the task's correlation ID.

---

## 7. Lineage Tracking

### 7.1 Lineage Graph

```
Artifact
  └── produced_by: task_id
        └── belongs_to: workflow_id
              └── belongs_to: wave_id
                    └── belongs_to: run_id
                          └── initiated_by: mission

Artifact lineage includes:
  - tool_calls: [tc_001, tc_002, ...]   # Tool calls that contributed
  - subtasks: [subtask_001, ...]          # Subtasks that produced intermediate results
  - parent_artifacts: [art_002, ...]      # Artifacts this artifact depends on (if any)
```

### 7.2 Lineage Query Examples

**Query: All artifacts produced by a workflow**
```
SELECT artifact_id FROM artifacts
WHERE lineage.workflow_id = 'wf_001'
```

**Query: Root cause of a failed artifact**
```
SELECT * FROM tool_calls
WHERE tool_call_id IN (
  SELECT tool_call_id FROM artifact_lineage
  WHERE artifact_id = 'art_001'
)
AND result.status = 'error'
```

**Query: All downstream artifacts affected by a failed task**
```
SELECT artifact_id FROM artifacts
WHERE lineage.task_id = 'task_001'
OR lineage.workflow_id IN (
  SELECT workflow_id FROM workflows
  WHERE tasks @> 'task_001'
)
```

### 7.3 Lineage in Artifact Metadata

Every artifact's `lineage` field MUST contain:

```json
{
  "lineage": {
    "produced_by": "<entity_id>",
    "workflow_id": "<workflow_id>",
    "wave_id": "<wave_id>",
    "run_id": "<run_id>",
    "tool_calls": ["<tool_call_id>", ...],
    "parent_artifacts": ["<artifact_id>", ...]
  }
}
```

---

## 8. Alignment with trace_schema.json v2.1

### 8.1 Mapping Table

| v2.1 Field | v2 Entity Schema Field | Notes |
|------------|----------------------|-------|
| `trace_id` | `span.trace_id` | Direct mapping |
| `span_id` | `span.span_id` | Direct mapping |
| `parent_span_id` | `span.parent_span_id` | Direct mapping |
| `operation_name` | `span.name` | Renamed for consistency |
| `start_time` | `span.start_time` | Direct mapping |
| `end_time` | `span.end_time` | Direct mapping |
| `status` | `span.status` | Direct mapping (`ok`, `error`, `unknown`) |
| `attributes` | `span.attributes` | Direct mapping |
| `events[].name` | `event.event_type` | Event type becomes the event name |
| `events[].timestamp` | `event.timestamp` | Direct mapping |
| `resource.service.name` | `span.attributes.worker_id` | Worker identity as service |

### 8.2 v2.1 Compatibility Layer

The trace collector emits v2.1-compatible spans alongside native v2 spans:

```json
{
  "v2.1_compatible_span": {
    "trace_id": "trace_run001",
    "span_id": "span_001",
    "parent_span_id": null,
    "operation_name": "task.execute",
    "start_time": "2026-04-13T10:00:03.000Z",
    "end_time": "2026-04-13T10:02:15.000Z",
    "status": "ok",
    "attributes": {
      "entity_type": "task",
      "entity_id": "task_001",
      "run_id": "run_2026041310000001",
      "worker_id": "worker_1"
    },
    "events": [
      {
        "name": "task.state_transition",
        "timestamp": "2026-04-13T10:00:03.000Z",
        "attributes": {
          "from_state": "ready",
          "to_state": "running"
        }
      }
    ]
  }
}
```

### 8.3 Event JSONL Format

Events in `events.jsonl` follow this format (one JSON object per line):

```
{"event_id":"evt_001","event_type":"task.state_transition","timestamp":"2026-04-13T10:00:03.000Z","entity_id":"task_001","entity_type":"task","run_id":"run_2026041310000001","correlation_id":"corr_run001_wave001_wf001_task001","severity":"info","payload":{"from_state":"ready","to_state":"running","transition":"acquire","worker_id":"worker_1"},"source":"scheduler","tags":["state_transition","task_lifecycle"]}
{"event_id":"evt_002","event_type":"tool_call.started","timestamp":"2026-04-13T10:00:04.000Z","entity_id":"tc_001","entity_type":"tool_call","run_id":"run_2026041310000001","correlation_id":"corr_run001_wave001_wf001_task001_sub001_act001_tc001","severity":"debug","payload":{"tool_name":"mcp:filesystem","tool_method":"read_file"},"source":"worker_1","tags":["tool_call"]}
```

---

## 9. ID Generation

### 9.1 ID Formats

| Entity Type | Format | Example |
|-------------|--------|---------|
| `run_id` | `run_{YYYYMMDDHHMMSS}{4-digit-seq}` | `run_2026041310000001` |
| `wave_id` | `wave_{3-digit-seq}` | `wave_001` |
| `workflow_id` | `wf_{3-digit-seq}` | `wf_001` |
| `task_id` | `task_{3-digit-seq}` | `task_001` |
| `subtask_id` | `subtask_{3-digit-seq}` | `subtask_001` |
| `action_id` | `action_{3-digit-seq}` | `action_001` |
| `tool_call_id` | `tc_{3-digit-seq}` | `tc_001` |
| `span_id` | `span_{3-digit-seq}` | `span_001` |
| `event_id` | `evt_{3-digit-seq}` | `evt_001` |
| `artifact_id` | `art_{3-digit-seq}` | `art_001` |
| `checkpoint_id` | `ckpt_{3-digit-seq}` | `ckpt_001` |
| `lease_id` | `lease_{3-digit-seq}` | `lease_001` |
| `correlation_id` | `corr_{entity_hierarchy}` | `corr_run001_wave001_wf001_task001` |

### 9.2 Generation Rules

- IDs are generated by the entity's parent (workflow creates tasks, task creates subtasks, etc.).
- IDs are scoped to the run: sequence numbers reset per run.
- IDs are monotonically increasing within a run.

---

## 10. Schema Validation

### 10.1 Validation Points

| Point | What is Validated |
|-------|-------------------|
| Entity creation | All required fields present; field types correct |
| State transition | Transition is valid for current state; guard conditions met |
| Event emission | Event type is in catalog; payload has required fields |
| Artifact storage | Checksum matches content; path is within entity directory |
| Correlation ID | Matches entity hierarchy; prefix chain is valid |

### 10.2 Validation Implementation

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import jsonschema

ENTITY_SCHEMAS = {
    "run": "schemas/v2/run.json",
    "wave": "schemas/v2/wave.json",
    "workflow": "schemas/v2/workflow.json",
    "task": "schemas/v2/task.json",
    "subtask": "schemas/v2/subtask.json",
    "action": "schemas/v2/action.json",
    "tool_call": "schemas/v2/tool_call.json",
    "span": "schemas/v2/span.json",
    "event": "schemas/v2/event.json",
    "artifact": "schemas/v2/artifact.json",
    "checkpoint": "schemas/v2/checkpoint.json",
}

def validate_entity(entity: dict) -> list[str]:
    """Validate entity against its JSON schema. Returns list of errors."""
    schema_path = ENTITY_SCHEMAS[entity["type"]]
    with open(schema_path) as f:
        schema = json.load(f)
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(entity))
    return [f"{e.json_path}: {e.message}" for e in errors]

def validate_transition(from_state: str, to_state: str, transition: str) -> bool:
    """Validate that a state transition is legal."""
    return (from_state, to_state, transition) in VALID_TRANSITIONS
```
