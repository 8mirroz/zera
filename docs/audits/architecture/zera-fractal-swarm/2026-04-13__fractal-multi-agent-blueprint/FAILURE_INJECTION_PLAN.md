# Failure Injection Plan — Wave 6

> **Wave:** 6 — Testing / Evals / Chaos / Benchmarking
> **Date:** 2026-04-13
> **Status:** Draft
> **Predecessors:** Waves 0–5
> **Aligned with:** Execution State Machine, Entity Schema v2, Trace Schema v2.1, Retry & Recovery Model

---

## 1. Scope

This document defines the chaos engineering plan for the Zera fractal multi-agent architecture. It specifies what failures to inject, how to inject them, expected recovery behavior, pass criteria, and injection schedules. The goal is to validate that the system's fault tolerance mechanisms (retry budgets, lease management, crash recovery, escalation paths) function correctly under real failure conditions.

---

## 2. Failure Taxonomy

### 2.1 Failure Categories

| Category | ID | Failure Type | Severity | Frequency |
|----------|----|-------------|----------|-----------|
| **Infrastructure** | `INFRA-001` | Network partition (MCP server unreachable) | High | Weekly |
| **Infrastructure** | `INFRA-002` | LLM API timeout | High | Weekly |
| **Infrastructure** | `INFRA-003` | Disk full (artifact store) | Critical | Monthly |
| **Infrastructure** | `INFRA-004` | Process crash (worker) | Critical | Weekly |
| **Infrastructure** | `INFRA-005` | DNS resolution failure | Medium | Monthly |
| **State** | `STATE-001` | Lease expiry without notification | High | Weekly |
| **State** | `STATE-002` | State file corruption | Critical | Monthly |
| **State** | `STATE-003` | Stale state (crash before write) | High | Bi-weekly |
| **Protocol** | `PROTO-001` | Heartbeat timeout | High | Weekly |
| **Protocol** | `PROTO-002` | Duplicate event emission | Medium | Bi-weekly |
| **Protocol** | `PROTO-003` | Out-of-order events | Medium | Bi-weekly |
| **Policy** | `POLICY-001` | Policy engine unavailable | Critical | Monthly |
| **Policy** | `POLICY-002` | Budget exceeded mid-execution | High | Bi-weekly |
| **Coordination** | `COORD-001` | Dependency deadlock (injected) | Critical | Monthly |
| **Coordination** | `COORD-002` | Worker pool exhaustion | High | Monthly |

---

## 3. Injection Specifications

### 3.1 INFRA-001: Network Partition (MCP Server Unreachable)

**What:** Simulate MCP server (filesystem, context7) becoming unreachable during task execution.

**How:**
```python
# Chaos script: inject_mcp_unreachable.py
# Location: scripts/chaos/inject_mcp_unreachable.py

import socket
from unittest.mock import patch

def inject(target_mcp="mcp:filesystem", duration_seconds=30):
    """Block all MCP connections for duration_seconds."""
    # Method 1: Socket-level injection (if MCP uses local sockets)
    # Method 2: Mock-based injection (wrap MCP client)
    # Method 3: iptables-based (Linux) / pf-based (macOS) firewall rules

    # Recommended: Mock-based injection for test environment
    original_connect = MCPClient.connect

    def blocked_connect(*args, **kwargs):
        raise ConnectionError(f"Chaos injection: {target_mcp} unreachable")

    MCPClient.connect = blocked_connect
    time.sleep(duration_seconds)
    MCPClient.connect = original_connect
```

**Injection Point:** During `tool_call.started` event, before tool execution completes.

**Expected Recovery Behavior:**
1. Worker detects tool_call failure (error event emitted)
2. Tool call retries according to retry budget (max_retries=3)
3. If all retries exhausted: task transitions `running → failed`
4. Retry handler checks if failure type is retryable
5. `mcp_server_unavailable` IS in `retryable_failures` list
6. Task transitions `failed → replayed → ready → running`
7. New worker acquires lease, re-executes
8. If MCP still down after 3 replays: `failed → escalated` (C4/C5) or `failed` (C1-C3)

**Pass Criteria:**
- [ ] Tool call failure detected within 5 seconds of injection
- [ ] Retry initiated within 10 seconds (including backoff)
- [ ] Task recovers when MCP restored (within 60 seconds of restoration)
- [ ] If MCP stays down: escalation occurs within 5 minutes (C4/C5)
- [ ] All state transitions recorded in events.jsonl
- [ ] No orphaned leases after recovery

**Telemetry Events Expected:**
```
tool_call.failed → retry.initiated → task.state_transition(failed) →
task.state_transition(replayed) → task.state_transition(ready) →
task.state_transition(running) → [recovery or escalation]
```

### 3.2 INFRA-002: LLM API Timeout

**What:** Simulate LLM provider (OpenRouter, Direct API) returning timeout or 503 during task execution.

**How:**
```python
# scripts/chaos/inject_llm_timeout.py

def inject(target_model_alias="$MODEL_ENGINEER_PRIMARY", duration_seconds=60):
    """Simulate LLM API timeout for specific model alias."""
    # Method: HTTP proxy that injects 503/timeout for specific requests
    # or patch the HTTP client at the model provider layer
    pass
```

**Injection Point:** During task execution, after `running` state entered, before `validating`.

**Expected Recovery Behavior:**
1. LLM timeout detected (configurable timeout, default 300s for C3)
2. Worker emits `tool_call.failed` or execution error
3. Task transitions `running → failed`
4. Failure type = `tool_timeout` → retryable
5. Retry with exponential backoff: 5s → 10s → 20s
6. Task transitions `failed → replayed → ready → running`
7. If timeout persists after max_retries: escalate or fail

**Pass Criteria:**
- [ ] Timeout detected and reported within timeout window + 5s
- [ ] Retry backoff follows exponential schedule (±20% jitter)
- [ ] Recovery within 2 minutes if LLM restored before retry exhaustion
- [ ] Escalation within 10 minutes if LLM stays down (C4/C5)

### 3.3 INFRA-003: Disk Full (Artifact Store)

**What:** Simulate disk space exhaustion in `.agents/store/` during artifact writing.

**How:**
```bash
# scripts/chaos/inject_disk_full.sh
# macOS: create a large sparse file to fill disk
# Or: use ulimit to restrict file size for the process

# Method 1: Fill disk with dummy data
# dd if=/dev/zero of=/tmp/disk_fill bs=1m count=10000

# Method 2: Restrict process file size (safer for dev)
# ulimit -f 1024  # 1MB limit

# Method 3: Bind mount a tmpfs with limited size (Linux)
# mount -t tmpfs -o size=10m tmpfs /path/to/artifact/store
```

**Injection Point:** During `artifact.created` event, when worker writes output files.

**Expected Recovery Behavior:**
1. File write fails with ENOSPC or IOError
2. Worker emits error event, task transitions `running → failed`
3. Failure type = `disk_full` → NOT in `retryable_failures` (non-retryable)
4. For C1-C3: `failed` terminal
5. For C4-C5: `failed → escalated` (human must free disk space)
6. Operator resolves (frees disk), resolves escalation: `escalated → ready → running`

**Pass Criteria:**
- [ ] Disk full error detected and reported (not swallowed)
- [ ] Non-retryable failure correctly classified
- [ ] C4/C5 tasks escalated, not silently failed
- [ ] Artifacts from partial writes cleaned up (no corrupt files)
- [ ] System continues operating for other tasks (isolation)

### 3.4 INFRA-004: Process Crash (Worker)

**What:** Kill the worker process mid-task execution (SIGKILL).

**How:**
```bash
# scripts/chaos/inject_worker_crash.sh

# Find worker process
WORKER_PID=$(ps aux | grep "worker" | grep -v grep | awk '{print $2}')

# Send SIGKILL
kill -9 $WORKER_PID

# Log the injection
echo "$(date): Worker crash injected, PID=$WORKER_PID" >> /tmp/chaos.log
```

**Injection Point:** During `running` state, after at least 1 tool call completed.

**Expected Recovery Behavior (per Execution State Machine §5.4):**
1. Lease manager detects missed heartbeats (2 consecutive misses = 90s)
2. Lease revoked: `task.lease_expired` event emitted
3. Task transitions: `running → failed` (via lease expiry guard)
4. Retry handler: `worker_crash` IS retryable
5. Task transitions: `failed → replayed → ready`
6. New worker acquires lease, re-executes from scratch
7. If checkpoint exists: resume from checkpoint (future optimization)

**Pass Criteria:**
- [ ] Lease revoked within 90 seconds of crash (2 missed heartbeats)
- [ ] Task replayed within 120 seconds of lease revocation
- [ ] No duplicate execution (old worker's partial results discarded)
- [ ] New worker completes task successfully
- [ ] If replay also fails: retry budget enforced correctly

**Telemetry Events Expected:**
```
task.heartbeat_missed (×2) → task.lease_expired →
task.state_transition(running→failed) → retry.initiated →
task.state_transition(failed→replayed) → task.state_transition(replayed→ready) →
task.state_transition(ready→running) [new worker]
```

### 3.5 STATE-001: Lease Expiry Without Notification

**What:** Let a task's lease expire naturally (no crash, no heartbeat) — simulates a hung worker that holds the lease but does nothing.

**How:**
```python
# scripts/chaos/inject_lease_hang.py

def inject(task_id, lease_id):
    """Stop sending heartbeats for a specific lease."""
    # Find the worker managing this lease
    # Disable heartbeat timer for this lease only
    # Let the lease expire naturally
    pass
```

**Injection Point:** After lease acquired, stop heartbeats.

**Expected Recovery Behavior:**
Same as INFRA-004 (worker crash) but slower:
1. Miss 1 (60s overdue): Warning logged
2. Miss 2 (90s overdue): Lease revoked, task failed → replayed → ready
3. New worker acquires and re-executes

**Pass Criteria:**
- [ ] Warning at miss 1 (60s)
- [ ] Lease revocation at miss 2 (90s)
- [ ] Task replayed within 120s of revocation

### 3.6 STATE-002: State File Corruption

**What:** Corrupt a `state.json` file on disk while the system is running.

**How:**
```bash
# scripts/chaos/inject_state_corruption.sh

STATE_FILE=".agents/store/runs/run_001/waves/wave_001/workflows/wf_001/tasks/task_001/state.json"

# Truncate file
truncate -s 0 "$STATE_FILE"

# Or: write invalid JSON
echo '{"state": "INVALID_CORRUPTED_DATA' > "$STATE_FILE"
```

**Injection Point:** Any entity's `state.json` during or after execution.

**Expected Recovery Behavior:**
1. System attempts to read state.json
2. JSON parse fails or schema validation fails
3. If running entity: treat as crashed (lease expired path)
4. If queued/ready entity: mark as failed, emit error event
5. Attempt recovery from events.jsonl (rebuild state from event history)
6. If state cannot be rebuilt: escalate

**Pass Criteria:**
- [ ] Corruption detected (JSON parse error or schema validation failure)
- [ ] Error event emitted with severity=error or critical
- [ ] Recovery attempted from event log
- [ ] If unrecoverable: escalated (not silently ignored)
- [ ] Other entities not affected (isolation)

### 3.7 STATE-003: Stale State (Crash Before Write)

**What:** Crash the system after a state transition is logged in events.jsonl but before state.json is updated.

**How:**
```python
# scripts/chaos/inject_stale_state.py

def inject(task_id):
    """Crash between event write and state.json write."""
    # This requires hooking the state transition handler:
    # 1. Write event to events.jsonl (normal)
    # 2. CRASH before writing state.json
    # 3. On restart, state.json shows old state, events.jsonl shows new state
    pass
```

**Injection Point:** Between `events.jsonl` append and `state.json` write (atomic write window).

**Expected Recovery Behavior:**
1. On restart, crash recovery scans state.json files
2. Detects inconsistency: events.jsonl has newer events than state.json reflects
3. Rebuilds state from events.jsonl (event sourcing)
4. State corrected to match event history
5. Execution resumes from corrected state

**Pass Criteria:**
- [ ] State inconsistency detected on startup
- [ ] State rebuilt from events.jsonl correctly
- [ ] No data loss (events preserved)
- [ ] Execution resumes without manual intervention

### 3.8 PROTO-001: Heartbeat Timeout

**What:** Already covered under INFRA-004 and STATE-001. This is the protocol-level failure.

**Additional test:** Send malformed heartbeats.

```python
# scripts/chaos/inject_bad_heartbeat.py

def inject(task_id, malformed_payload):
    """Send heartbeats with invalid payload."""
    # Missing worker_id
    # Invalid lease_id
    # Timestamp in the future/past
    pass
```

**Expected Recovery Behavior:**
- Malformed heartbeat rejected
- Warning event emitted
- Treated as missed heartbeat if no valid heartbeat received within window

**Pass Criteria:**
- [ ] Malformed heartbeat rejected (not accepted)
- [ ] Warning event emitted (severity=warn)
- [ ] Lease management continues correctly

### 3.9 POLICY-001: Policy Engine Unavailable

**What:** Simulate policy engine being unreachable during execution (policy gate checks).

**How:**
```python
# scripts/chaos/inject_policy_down.py

def inject(duration_seconds=120):
    """Make policy engine unreachable."""
    # Shutdown policy engine process
    # Or: block network access to policy engine
    pass
```

**Injection Point:** During task execution when a policy gate is required (C4/C5 human audit, council review).

**Expected Recovery Behavior:**
1. Policy gate check fails (unreachable)
2. Task transitions `running → blocked` (external dependency unavailable)
3. Block reason recorded: "policy_engine_unreachable"
4. Block timeout timer started
5. If policy engine restored: `blocked → ready → running`
6. If block timeout exceeded: `blocked → failed`

**Pass Criteria:**
- [ ] Task blocked (not failed immediately)
- [ ] Block reason accurately recorded
- [ ] Recovery when policy engine restored
- [ ] Failure after timeout if not restored

### 3.10 POLICY-002: Budget Exceeded Mid-Execution

**What:** Task exceeds its tool_budget during execution.

**How:**
```python
# scripts/chaos/inject_budget_exceeded.py

def inject(task_id, tool_count_override):
    """Artificially increment tool call count to exceed budget."""
    # Modify task's tool_calls_made counter
    # Or: set tool_budget to 1 and trigger 2 tool calls
    pass
```

**Injection Point:** During task execution, after tool_budget threshold crossed.

**Expected Recovery Behavior:**
1. Tool budget check fails
2. Task transitions `running → failed`
3. Failure type = `budget_exceeded` → NOT retryable
4. Terminal failure (or escalate for C4/C5)

**Pass Criteria:**
- [ ] Budget check enforced at boundary
- [ ] Non-retryable failure correctly classified
- [ ] No further tool calls after budget exceeded

### 3.11 COORD-001: Dependency Deadlock (Injected)

**What:** Create a circular dependency between tasks that the dependency resolver should detect.

**How:**
```python
# scripts/chaos/inject_deadlock.py

def inject():
    """Create tasks A→B→C→A circular dependency."""
    # This should be caught by the dependency resolver
    # before execution begins, but test the detection
    pass
```

**Expected Recovery Behavior:**
1. Dependency resolver detects cycle during task creation
2. Error emitted: dependency cycle detected
3. Tasks never enter `running` state
4. Operator notified

**Pass Criteria:**
- [ ] Cycle detected before execution (not during)
- [ ] Clear error message identifying the cycle
- [ ] No deadlock occurs

### 3.12 COORD-002: Worker Pool Exhaustion

**What:** All workers busy, new task queued.

**How:**
```python
# scripts/chaos/inject_worker_exhaustion.py

def inject(worker_count, task_count):
    """Submit more tasks than available workers."""
    # Submit task_count tasks with worker_count workers
    # where task_count > worker_count
    # Tasks should queue, not fail
    pass
```

**Expected Recovery Behavior:**
1. Excess tasks enter `queued` state (not failed)
2. As workers complete tasks, queued tasks transition `queued → ready → running`
3. Priority ordering respected

**Pass Criteria:**
- [ ] Excess tasks queued (not failed)
- [ ] All tasks eventually executed
- [ ] Priority ordering preserved
- [ ] No starvation (low-priority tasks eventually run)

---

## 4. Injection Schedule

### 4.1 Regular Schedule

| Frequency | Tests | Environment |
|-----------|-------|-------------|
| **Weekly** | INFRA-001, INFRA-002, INFRA-004, STATE-001, PROTO-001 | Staging |
| **Bi-weekly** | STATE-003, PROTO-002, PROTO-003, POLICY-002 | Staging |
| **Monthly** | INFRA-003, INFRA-005, STATE-002, POLICY-001, COORD-001, COORD-002 | Staging + Pre-prod |
| **Pre-release** | All 15 tests | Pre-prod |
| **Post-incident** | Relevant test(s) | Staging |

### 4.2 Execution Window

- **Day:** Tuesday 02:00-06:00 UTC (low-traffic window)
- **Duration:** 2 hours per category
- **Cooldown:** 30 minutes between injections
- **Rollback:** Immediate stop if any production-like environment affected

### 4.3 Chaos Automation Framework

```yaml
# scripts/chaos/chaos_plan.yaml
version: "1.0"
schedule:
  day: tuesday
  time: "02:00"
  timezone: "UTC"
  max_duration_hours: 4

environment:
  target: "staging"
  production_prohibited: true

injections:
  - id: INFRA-001
    enabled: true
    cooldown_minutes: 30
    pre_check: "all_tasks_idle_or_completed"
    post_check: "no_orphaned_leases"

  - id: INFRA-002
    enabled: true
    cooldown_minutes: 30
    pre_check: "llm_api_healthy"
    post_check: "no_orphaned_leases"

  # ... all injections listed ...

safety:
  kill_switch: "scripts/chaos/abort.sh"
  max_injection_duration_minutes: 30
  auto_abort_on_production_detection: true
  notification_channel: "#chaos-engineering"
```

---

## 5. Pass/Fail Summary

| Test ID | Name | Max Recovery Time | Criticality | Pass Criterion |
|---------|------|-------------------|-------------|----------------|
| INFRA-001 | MCP unreachable | 60s | High | Retry + recovery or escalation |
| INFRA-002 | LLM timeout | 120s | High | Retry + recovery or escalation |
| INFRA-003 | Disk full | N/A | Critical | Correct classification, no data loss |
| INFRA-004 | Worker crash | 120s | Critical | Lease expiry → replay → recovery |
| INFRA-005 | DNS failure | 60s | Medium | Retry + recovery |
| STATE-001 | Lease hang | 120s | High | 2-miss detection → replay |
| STATE-002 | State corruption | 60s | Critical | Detection → rebuild or escalate |
| STATE-003 | Stale state | 60s | High | Event sourcing recovery |
| PROTO-001 | Heartbeat timeout | 120s | High | Covered by INFRA-004/STATE-001 |
| PROTO-002 | Duplicate events | 30s | Medium | Idempotent handling |
| PROTO-003 | Out-of-order events | 30s | Medium | Correct ordering restored |
| POLICY-001 | Policy engine down | 300s | Critical | Block → recovery or timeout fail |
| POLICY-002 | Budget exceeded | 10s | High | Immediate termination, non-retryable |
| COORD-001 | Deadlock injection | 10s | Critical | Pre-execution detection |
| COORD-002 | Worker exhaustion | N/A | High | Queued, no starvation |

---

## 6. Safety Guardrails

### 6.1 Absolute Prohibitions

- **NEVER** inject failures in production environment
- **NEVER** inject during active user-facing runs
- **NEVER** inject multiple failure types simultaneously (unless explicitly testing cascade)
- **NEVER** inject without pre-checks passing
- **NEVER** inject without post-checks defined

### 6.2 Abort Conditions

Chaos injection aborts immediately if:
1. Any production-like environment detected (check `ENVIRONMENT` variable)
2. Active user-facing run detected (check for non-chaos runs in progress)
3. System enters safe mode
4. Operator sends abort signal (via CLI or UI)
5. Injection duration exceeds max (30 minutes)
6. Unexpected cascade failure detected

### 6.3 Abort Command

```bash
# Immediate abort all chaos injections
python3 scripts/chaos/abort.py --all

# Abort specific injection
python3 scripts/chaos/abort.py --injection INFRA-004

# Check abort status
python3 scripts/chaos/status.py
```

---

## 7. Telemetry Alignment

Every chaos injection produces telemetry conforming to v2.1 schema:

| Telemetry Field | Chaos Mapping |
|-----------------|---------------|
| `event_type` | `chaos.injection_started`, `chaos.injection_completed`, `chaos.recovery_verified`, `chaos.recovery_failed` |
| `severity` | `warn` (injection), `info` (recovery), `error` (recovery failed) |
| `component` | `chaos` |
| `payload.injection_id` | Test ID (e.g., `INFRA-004`) |
| `payload.target_entity_id` | Task/entity being injected |
| `payload.recovery_time_ms` | Measured recovery duration |
| `payload.pass_criteria_met` | Boolean |
| `span.name` | `chaos.inject.{injection_id}` |
| `artifact` | Chaos injection report, recovery timeline, event capture |

All chaos events are tagged with `tags: ["chaos", "failure_injection", "{injection_id}"]` for filtering in the dashboard.
