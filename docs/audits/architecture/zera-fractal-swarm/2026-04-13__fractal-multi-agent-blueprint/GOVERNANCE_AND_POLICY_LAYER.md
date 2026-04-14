# Governance and Policy Layer — Fractal Multi-Agent Architecture

> **Wave:** 4 — Target Execution Blueprint
> **Date:** 2026-04-13
> **Status:** Draft
> **Scope:** Approval points, operator overrides, drift detection, CI gates, policy enforcement, safe-mode triggers

---

## 1. Approval Points in the Pipeline

Approval points are stages in the execution pipeline where execution halts and awaits operator (human) approval before proceeding.

### 1.1 Approval Point Catalog

| ID | Point | Applies To | Trigger | Default Action on Timeout |
|----|-------|-----------|---------|---------------------------|
| **AP-1** | Pre-execution gate | C5 missions | Mission classification = C5 | Deny (mission not started) |
| **AP-2** | Pre-merge gate | C4+ tasks | Task produces code changes that will be committed | Deny (commit blocked) |
| **AP-3** | Pre-deployment gate | C4+ runs producing deployable artifacts | Run state = completed, has deployable artifact | Deny (deployment blocked) |
| **AP-4** | Escalation review | C4+ escalated tasks | Task enters `escalated` state | Hold indefinitely (requires operator) |
| **AP-5** | Compensation approval | Any entity with active compensation | Compensation handler triggered | Deny (compensation not executed) |
| **AP-6** | Policy exception | Any entity | Operator requests policy override | N/A (operator-initiated) |

### 1.2 Approval Point Flow

```
Task executes
  │
  ▼
Task completes
  │
  ▼
Does task produce code changes? ──NO──▶ Proceed normally
  │
  YES
  │
  ▼
Is task tier C4 or higher? ──NO──▶ Auto-pass (C1-C3)
  │
  YES
  │
  ▼
[AP-2] Pre-merge gate
  │
  ├── Approved ──▶ Commit proceeds
  │
  ├── Denied ──▶ Task marked as failed; rollback initiated
  │
  └── Timeout (30 min) ──▶ Denied by default
```

### 1.3 Approval Point Configuration

```yaml
approval_points:
  AP-1:
    name: "pre-execution-gate"
    applies_to: "mission"
    condition: "mission.classification == 'C5'"
    timeout_seconds: 3600    # 1 hour
    default_action: "deny"
    notification_channels: ["slack", "email"]

  AP-2:
    name: "pre-merge-gate"
    applies_to: "task"
    condition: "task.tier in ['C4', 'C5'] AND task.produces_code_changes"
    timeout_seconds: 1800    # 30 min
    default_action: "deny"
    notification_channels: ["slack"]

  AP-3:
    name: "pre-deployment-gate"
    applies_to: "run"
    condition: "run.state == 'completed' AND run.has_deployable_artifact"
    timeout_seconds: 7200    # 2 hours
    default_action: "deny"
    notification_channels: ["slack", "email", "pagerduty"]

  AP-4:
    name: "escalation-review"
    applies_to: "task"
    condition: "task.state == 'escalated'"
    timeout_seconds: null    # No timeout — requires explicit operator action
    default_action: "hold"
    notification_channels: ["slack", "email", "pagerduty"]

  AP-5:
    name: "compensation-approval"
    applies_to: "entity"
    condition: "entity.has_active_compensation"
    timeout_seconds: 3600    # 1 hour
    default_action: "deny"
    notification_channels: ["slack"]
```

---

## 2. Operator Override Mechanisms

Operators can intervene in execution at any point. Overrides are logged, auditable, and reversible where possible.

### 2.1 Override Types

| Override | Effect | Reversible | Scope |
|----------|--------|------------|-------|
| `approve` | Passes an approval point | No (decision is recorded) | Single entity |
| `deny` | Fails an approval point | No | Single entity |
| `force_state` | Sets entity to a specific state | Yes (revert to previous state) | Single entity |
| `retry` | Forces a retry regardless of budget | Yes (can cancel retry) | Single entity |
| `skip` | Skips an entity (marks as completed with no output) | Yes | Single entity |
| `pause` | Pauses all execution for a run/wave | Yes | Run or wave |
| `resume` | Resumes paused execution | N/A | Run or wave |
| `cancel` | Cancels a run (all entities transition to failed) | No | Run |
| `inject_artifact` | Adds an artifact to the store (bypasses normal production) | Yes | Run |
| `policy_override` | Temporarily disables a policy rule | Yes (re-enable) | Run or global |

### 2.2 Override Command Interface

```bash
# Approve a pre-merge gate
swarmctl.py gate approve AP-2 --task task_001 --reason "Reviewed, looks good"

# Force a task to completed (bypass validation)
swarmctl.py override force-state --task task_001 --state completed --reason "Validation environment down"

# Retry a task beyond its budget
swarmctl.py override retry --task task_001 --force --reason "Transient failure, infrastructure fixed"

# Pause a run
swarmctl.py override pause --run run_2026041310000001 --reason "Investigating cascade failure"

# Resume a paused run
swarmctl.py override resume --run run_2026041310000001

# Cancel a run entirely
swarmctl.py override cancel --run run_2026041310000001 --reason "Mission no longer relevant"

# Inject an artifact
swarmctl.py override inject-artifact --run run_2026041310000001 --task task_001 --file /path/to/file.txt

# Temporary policy override
swarmctl.py override policy --disable tool_budget_enforcement --run run_2026041310000001 --duration 30m
```

### 2.3 Override Audit Log

All overrides are recorded in an append-only audit log:

```json
{
  "override_id": "ovr_001",
  "type": "force_state",
  "operator": "user@example.com",
  "target_entity": "task_001",
  "target_entity_type": "task",
  "previous_state": "running",
  "new_state": "completed",
  "reason": "Validation environment down",
  "timestamp": "2026-04-13T10:30:00Z",
  "reversible": true,
  "reverted": false
}
```

### 2.4 Override Safety Guards

| Guard | Description |
|-------|-------------|
| **Reason required** | Every override must include a human-readable reason |
| **Operator identity** | Operator identity is recorded (authenticated via CLI auth) |
| **Confirmation for destructive actions** | `cancel` and `force_state` to terminal states require explicit `--yes` flag |
| **Rate limiting** | Maximum 10 overrides per run per 5-minute window |
| **Audit trail** | All overrides are in append-only audit log; never deleted |
| **Reversibility indicator** | Each override is marked as reversible or not |

---

## 3. Drift Detection Strategy

Drift detection compares actual execution metrics against expected baselines and flags deviations.

### 3.1 Drift Metrics

| Metric | Baseline Source | Alert Threshold | Action |
|--------|----------------|-----------------|--------|
| **Task latency p50** | Historical p50 for same workflow | > 2x baseline | Log warning |
| **Task latency p99** | Historical p99 for same workflow | > 3x baseline | Log warning; notify operator |
| **Task failure rate** | Historical failure rate for same tier | > 2x baseline | Log warning |
| **Queue depth** | Expected queue depth for current wave | > 3x expected | Log warning |
| **Worker utilization** | Expected utilization (target: 70-85%) | < 30% or > 95% | Log warning |
| **Tool call error rate** | Historical error rate per tool | > 5x baseline | Log warning; notify operator |
| **Heartbeat miss rate** | Expected: < 1% | > 5% | Log warning; potential worker issue |
| **Lease expiry rate** | Expected: < 2% | > 10% | Log warning; potential worker overload |

### 3.2 Drift Detection Algorithm

```python
def detect_drift(metric_name: str, current_value: float, baseline: Baseline) -> DriftAlert | None:
    """Detect drift for a given metric."""
    threshold = baseline.alert_threshold
    deviation_pct = (current_value - baseline.value) / baseline.value * 100

    if current_value > threshold:
        severity = _classify_severity(deviation_pct, baseline)
        return DriftAlert(
            metric=metric_name,
            expected=baseline.value,
            actual=current_value,
            deviation_pct=deviation_pct,
            severity=severity,
            timestamp=now_utc(),
        )
    return None

def _classify_severity(deviation_pct: float, baseline: Baseline) -> str:
    if deviation_pct > 500:
        return "critical"
    elif deviation_pct > 200:
        return "high"
    elif deviation_pct > 100:
        return "medium"
    else:
        return "low"
```

### 3.3 Drift Response Policy

| Severity | Response |
|----------|----------|
| `low` | Log only; no action |
| `medium` | Log; include in next periodic report |
| `high` | Log; notify operator via Slack; include in periodic report |
| `critical` | Log; notify operator via Slack + PagerDuty; evaluate for safe-mode activation |

### 3.4 Baseline Management

Baselines are computed from historical execution data and updated periodically:

```yaml
baseline_config:
  update_interval: "daily"           # Recompute baselines daily
  lookback_window: "7d"              # Use last 7 days of data
  minimum_samples: 10                # Need at least 10 executions
  outlier_removal: true              # Remove top/bottom 5% before computing
  percentiles: [50, 90, 99]          # Track p50, p90, p99
```

---

## 4. CI Gates — Pre-Promotion Requirements

Before any entity (task output, workflow result, run output) is promoted to the next stage, the following gates must pass.

### 4.1 Gate Catalog by Tier

| Gate | C1 | C2 | C3 | C4 | C5 | Description |
|------|:--:|:--:|:--:|:--:|:--:|-------------|
| **G-1: Lint** | ✓ | ✓ | ✓ | ✓ | ✓ | Code passes all lint checks |
| **G-2: Format** | ✓ | ✓ | ✓ | ✓ | ✓ | Code passes format checks |
| **G-3: Type Check** | — | ✓ | ✓ | ✓ | ✓ | No type errors (Pyright/MyPy) |
| **G-4: Unit Tests** | — | ✓ | ✓ | ✓ | ✓ | All unit tests pass |
| **G-5: Integration Tests** | — | — | ✓ | ✓ | ✓ | Integration tests pass |
| **G-6: Security Scan** | — | — | — | ✓ | ✓ | No known vulnerabilities |
| **G-7: Artifact Verification** | — | — | ✓ | ✓ | ✓ | All expected artifacts exist and are non-empty |
| **G-8: Retrospective** | — | — | ✓ | ✓ | ✓ | Retrospective written |
| **G-9: Code Review** | — | — | ✓ | ✓ | ✓ | Code review evidence collected |
| **G-10: Human Audit** | — | — | — | ✓ | ✓ | Human audit completed |
| **G-11: ADR Update** | — | — | — | — | ✓ | ADR updated |
| **G-12: Council Review** | — | — | — | — | ✓ | Council review passed |

### 4.2 Gate Evaluation Flow

```
Task completes
  │
  ▼
Produce artifacts
  │
  ▼
Evaluate gates applicable to this tier
  │
  ├── G-1: Run linter ──▶ Pass/Fail
  ├── G-2: Run formatter ──▶ Pass/Fail
  ├── G-3: Run type checker ──▶ Pass/Fail
  ├── G-4: Run unit tests ──▶ Pass/Fail
  ├── ...
  │
  ▼
All gates pass? ──NO──▶ Task state = failed; reason = gate_failure
  │
  YES
  │
  ▼
Task state = completed
  │
  ▼
Approval point check (if applicable)
```

### 4.3 Gate Configuration

```yaml
gates:
  G-1:
    name: "lint"
    command: "ruff check repos/"
    timeout_seconds: 60
    applies_to_tiers: ["C1", "C2", "C3", "C4", "C5"]

  G-2:
    name: "format"
    command: "ruff format --check repos/"
    timeout_seconds: 60
    applies_to_tiers: ["C1", "C2", "C3", "C4", "C5"]

  G-3:
    name: "type-check"
    command: "pyright repos/"
    timeout_seconds: 120
    applies_to_tiers: ["C2", "C3", "C4", "C5"]

  G-4:
    name: "unit-tests"
    command: "pytest repos/ -m unit"
    timeout_seconds: 300
    applies_to_tiers: ["C2", "C3", "C4", "C5"]

  G-5:
    name: "integration-tests"
    command: "pytest repos/ -m integration"
    timeout_seconds: 600
    applies_to_tiers: ["C3", "C4", "C5"]

  G-6:
    name: "security-scan"
    command: "bandit -r repos/ -ll"
    timeout_seconds: 120
    applies_to_tiers: ["C4", "C5"]

  G-7:
    name: "artifact-verification"
    command: "internal:check_artifacts"
    timeout_seconds: 30
    applies_to_tiers: ["C3", "C4", "C5"]

  G-8:
    name: "retrospective"
    command: "internal:check_retrospective"
    timeout_seconds: 30
    applies_to_tiers: ["C3", "C4", "C5"]

  G-9:
    name: "code-review"
    command: "internal:check_code_review"
    timeout_seconds: 30
    applies_to_tiers: ["C3", "C4", "C5"]

  G-10:
    name: "human-audit"
    command: "approval_gate:AP-10"
    timeout_seconds: null
    applies_to_tiers: ["C4", "C5"]

  G-11:
    name: "adr-update"
    command: "internal:check_adr"
    timeout_seconds: 30
    applies_to_tiers: ["C5"]

  G-12:
    name: "council-review"
    command: "approval_gate:AP-12"
    timeout_seconds: null
    applies_to_tiers: ["C5"]
```

---

## 5. Policy Enforcement Points

Policy enforcement points (PEPs) are locations in the execution pipeline where policy rules are evaluated and enforced.

### 5.1 PEP Catalog

| PEP | Location | Policy Evaluated | Enforcement Action |
|-----|----------|-----------------|-------------------|
| **PEP-1: Tool Budget** | Before each tool call | `tool_call_count < task.tool_budget` | Block tool call; fail task |
| **PEP-2: Timeout** | During task execution | `elapsed_time < task.timeout_seconds` | Kill task; fail |
| **PEP-3: File System Boundary** | Before file operations | `path within task.allowed_paths` | Block operation; fail task |
| **PEP-4: Tool Allowlist** | Before each tool call | `tool_name in task.definition.tools` | Block tool call; fail task |
| **PEP-5: Tier Budget** | At task dispatch | `resources <= tier_max_resources` | Deny dispatch; escalate |
| **PEP-6: Write Authority** | Before each state write | `writer in entity.allowed_writers` | Block write; log violation |
| **PEP-7: Rate Limit** | At task dispatch | `dispatch_rate < max_dispatch_rate` | Queue task; wait |
| **PEP-8: Concurrent Task** | At task dispatch | `active_tasks < max_concurrent_tasks` | Queue task; wait |
| **PEP-9: Dependency Integrity** | At dependency resolution | `all dependencies in terminal state` | Block resolution |
| **PEP-10: Artifact Size** | At artifact creation | `artifact_size < max_artifact_size` | Reject artifact; warn |

### 5.2 Policy Evaluation Order

```
Task dispatch:
  PEP-5 (Tier Budget)
  PEP-8 (Concurrent Tasks)
  PEP-7 (Rate Limit)
  PEP-9 (Dependency Integrity)
    │
    ▼
Task execution:
  PEP-2 (Timeout) — continuous check
    │
    ▼
Tool call:
  PEP-4 (Tool Allowlist)
  PEP-1 (Tool Budget)
  PEP-3 (File System Boundary)
    │
    ▼
State write:
  PEP-6 (Write Authority)
    │
    ▼
Artifact creation:
  PEP-10 (Artifact Size)
```

### 5.3 Policy Configuration

```yaml
policies:
  PEP-1:
    name: "tool-budget"
    max_tool_calls_per_task: 50      # Hard limit
    max_tool_calls_per_subtask: 20   # Hard limit
    action_on_violation: "fail_task"

  PEP-2:
    name: "timeout"
    default_timeout_seconds: 600     # 10 minutes
    max_timeout_seconds: 3600        # 1 hour (override allowed per task)
    action_on_violation: "kill_and_fail"

  PEP-3:
    name: "filesystem-boundary"
    allowed_roots:
      - "/Users/user/zera/repos/"
      - "/Users/user/zera/sandbox/"
      - "/Users/user/zera/.agents/store/"
    action_on_violation: "fail_task"

  PEP-4:
    name: "tool-allowlist"
    # Defined per task in task.definition.tools
    action_on_violation: "fail_task"

  PEP-5:
    name: "tier-budget"
    tier_limits:
      C1: { max_agents: 1, max_tools: 8, max_duration_seconds: 300 }
      C2: { max_agents: 1, max_tools: 12, max_duration_seconds: 600 }
      C3: { max_agents: 2, max_tools: 20, max_duration_seconds: 1800 }
      C4: { max_agents: 3, max_tools: 35, max_duration_seconds: 3600 }
      C5: { max_agents: 3, max_tools: 50, max_duration_seconds: 7200 }
    action_on_violation: "escalate"

  PEP-6:
    name: "write-authority"
    # Defined in EXECUTION_STATE_MACHINE.md §4.2
    action_on_violation: "block_and_log"

  PEP-7:
    name: "rate-limit"
    max_dispatch_per_second: 10
    action_on_violation: "queue_and_wait"

  PEP-8:
    name: "concurrent-tasks"
    max_concurrent_tasks: 10
    action_on_violation: "queue_and_wait"

  PEP-9:
    name: "dependency-integrity"
    # All dependencies must be in terminal state
    action_on_violation: "block_resolution"

  PEP-10:
    name: "artifact-size"
    max_artifact_size_bytes: 104857600  # 100 MB
    action_on_violation: "reject_and_warn"
```

---

## 6. Emergency Safe-Mode Triggers

Safe-mode is a fallback execution state that prioritizes correctness over parallelism. When activated, the system falls back to sequential execution with enhanced validation.

### 6.1 Safe-Mode Trigger Conditions

| Trigger ID | Condition | Severity | Automatic |
|------------|-----------|----------|-----------|
| **SM-1** | Cascade failure: > 50% of active tasks fail within 5 minutes | Critical | Yes |
| **SM-2** | Resource exhaustion: disk, memory, or CPU at > 95% | Critical | Yes |
| **SM-3** | Worker pool collapse: all workers unresponsive | Critical | Yes |
| **SM-4** | Data corruption detected: state file checksum mismatch | Critical | Yes |
| **SM-5** | Drift critical: latency p99 > 10x baseline for 3 consecutive checks | High | Yes |
| **SM-6** | Policy violation cascade: > 3 PEP violations within 10 minutes | High | Yes |
| **SM-7** | Operator command | Any | No |

### 6.2 Safe-Mode Behavior

When safe-mode is activated:

```
1. STOP: Halt all task dispatch immediately
2. DRAIN: Allow currently running tasks to complete or timeout (do not kill)
3. FREEZE: Do not dispatch any new tasks
4. ASSESS: Run system health check
   ├── Check worker pool health
   ├── Check file system integrity
   ├── Check state file consistency
   └── Check resource utilization
5. DECIDE: Operator evaluates assessment
   ├── If fixable: Apply fix, deactivate safe-mode, resume parallel
   ├── If not fixable: Switch to sequential fallback mode
   └── If catastrophic: Cancel run entirely
```

### 6.3 Sequential Fallback Mode

If safe-mode assessment determines that parallel execution is not recoverable:

```
Sequential Fallback Mode:
  - One task at a time (no parallelism)
  - Enhanced validation after each task
  - All tasks treated as C4 (require validation)
  - Heartbeat interval reduced to 15s
  - Retry budget halved
  - All tool calls logged at debug level
  - Operator notified of mode switch
```

### 6.4 Safe-Mode Deactivation

Safe-mode can only be deactivated by:

1. **Automatic deactivation:** Assessment passes, no critical issues found, resource utilization normal. System waits 60 seconds before resuming parallel execution.

2. **Operator deactivation:** Operator explicitly commands deactivation after manual investigation.

3. **Fallback activation:** System transitions to sequential fallback mode (safe-mode is not "deactivated" — it is "downgraded").

### 6.5 Safe-Mode Notification

When safe-mode is activated:

```json
{
  "event_type": "safe_mode.activated",
  "timestamp": "2026-04-13T10:30:00Z",
  "trigger": "SM-1",
  "reason": "Cascade failure: 12 of 20 active tasks failed within 5 minutes",
  "affected_runs": ["run_2026041310000001"],
  "affected_tasks": ["task_001", "task_002", "task_005", "task_007", "task_008", "task_009", "task_010", "task_011", "task_012", "task_013", "task_014", "task_015"],
  "action": "dispatch_halted; awaiting_assessment",
  "notification_sent": {
    "slack": true,
    "email": true,
    "pagerduty": true
  }
}
```

---

## 7. Policy Registry

All policies are defined in a central registry and loaded at system startup. Policies can be hot-reloaded (with operator approval).

```yaml
# configs/orchestrator/policy_registry.yaml
policy_registry:
  version: "4.2.0"
  last_updated: "2026-04-13T00:00:00Z"
  hot_reload: false  # Set to true to allow runtime policy changes

  approval_points:
    # See §1 above

  overrides:
    # See §2 above

  drift_detection:
    # See §3 above

  ci_gates:
    # See §4 above

  enforcement_points:
    # See §5 above

  safe_mode:
    # See §6 above
```

---

## 8. Governance Audit Trail

All governance actions are recorded in an append-only audit log:

```
.agents/store/
├── audit/
│   ├── approvals.jsonl          # Approval point decisions
│   ├── overrides.jsonl          # Operator overrides
│   ├── drift_alerts.jsonl       # Drift detection alerts
│   ├── gate_results.jsonl       # CI gate results
│   ├── policy_violations.jsonl  # PEP violations
│   └── safe_mode_events.jsonl   # Safe-mode activations/deactivations
```

Each entry follows this format:

```json
{
  "audit_id": "audit_001",
  "audit_type": "approval_decision",
  "timestamp": "2026-04-13T10:30:00Z",
  "actor": "policy_engine",
  "target_entity": "task_001",
  "target_entity_type": "task",
  "run_id": "run_2026041310000001",
  "action": "deny",
  "reason": "Pre-merge gate AP-2: code review not completed",
  "details": {
    "gate_id": "AP-2",
    "timeout_seconds": 1800,
    "default_action": "deny"
  }
}
```

---

## 9. Summary — Governance at a Glance

| Concern | Mechanism | Enforcement |
|---------|-----------|-------------|
| **When can execution proceed?** | Approval points (AP-1 through AP-6) | Policy engine halts dispatch until approved |
| **Can a human intervene?** | Operator overrides (10 types) | CLI interface with audit log |
| **How do we detect anomalies?** | Drift detection (8 metrics, 4 severity levels) | Automatic alerting; safe-mode trigger at critical |
| **What must pass before promotion?** | CI gates (G-1 through G-12, tier-dependent) | Gate evaluation before state transition to `completed` |
| **How are rules enforced at runtime?** | Policy enforcement points (PEP-1 through PEP-10) | Evaluated at dispatch, execution, tool call, state write, artifact creation |
| **What happens in a crisis?** | Safe-mode triggers (SM-1 through SM-7) | Automatic dispatch halt; assessment; sequential fallback |
