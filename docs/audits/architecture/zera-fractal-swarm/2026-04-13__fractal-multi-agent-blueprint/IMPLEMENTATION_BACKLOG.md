# Implementation Backlog — Zera Fractal Multi-Agent Blueprint

**Audit Wave:** 7 — Final Recommendation + Migration Package
**Date:** 2026-04-13
**Total items:** 38
**Priority levels:** P0 (must have), P1 (should have), P2 (nice to have)

---

## Effort Scale

| Size | Duration | Description |
|------|----------|-------------|
| S | < 1 day | Single file change, well-understood |
| M | 1–3 days | Multi-file change, clear scope |
| L | 3–7 days | New component, requires design |
| XL | 1–3 weeks | New subsystem, requires cross-phase coordination |

---

## Phase 1: Instrumentation (P0)

### P0-1: Core Trace Emitter
- **Priority:** P0
- **Effort:** M
- **Dependencies:** None
- **Description:** Implement the core trace emission library that produces structured trace events. Must be lightweight (<1ms overhead per emission).
- **Acceptance criteria:**
  - Emits events: `task_start`, `task_end`, `task_error`, `tool_call`, `tool_result`, `retry`, `fallback`, `lease_issue`, `lease_expire`
  - Each event includes: `task_id`, `timestamp`, `component`, `level`, `data` (payload)
  - Overhead < 1ms per emission (measured via benchmark)
  - Thread-safe (safe to call from parallel agent goroutines/threads)

### P0-2: Orchestrator Instrumentation
- **Priority:** P0
- **Effort:** L
- **Dependencies:** P0-1
- **Description:** Instrument all code paths in the orchestrator with trace emissions. Every decision point, branch, and action must emit a trace.
- **Acceptance criteria:**
  - 100% of orchestrator code paths covered (verified by code review + trace output)
  - At least one trace emitted per task lifecycle (start, at least one action, end)
  - Fallback paths emit `level: warning` traces with reason

### P0-3: Router Instrumentation
- **Priority:** P0
- **Effort:** M
- **Dependencies:** P0-1
- **Description:** Instrument task classification (C1–C5), model selection, and fallback chain events.
- **Acceptance criteria:**
  - Classification event includes: tier, criteria matched, confidence
  - Model selection event includes: selected model, reason, fallback chain
  - Fallback events include: what failed, what was selected instead, reason

### P0-4: Agent Execution Instrumentation
- **Priority:** P0
- **Effort:** M
- **Dependencies:** P0-1
- **Description:** Instrument subagent spawn, completion, timeout, and error events.
- **Acceptance criteria:**
  - Spawn event includes: agent_id, task_id, tier, resources allocated
  - Completion event includes: agent_id, task_id, duration, output size
  - Timeout event includes: agent_id, task_id, lease_duration, action_taken
  - Error event includes: agent_id, task_id, error_type, error_message, stack_trace

### P0-5: Trace Sink (File-Based)
- **Priority:** P0
- **Effort:** M
- **Dependencies:** P0-1
- **Description:** Persistent storage backend for traces. File-based initially (JSON Lines), upgradeable to Qdrant/SQLite later.
- **Acceptance criteria:**
  - Writes are append-only (never overwrite)
  - Survives process restart (traces not lost)
  - File rotation: new file per day or per 100MB, whichever comes first
  - Trace retrieval by `task_id` in <100ms for 10,000 traces

### P0-6: Trace ID Propagation
- **Priority:** P0
- **Effort:** S
- **Dependencies:** P0-1
- **Description:** Ensure correlation IDs flow through parent→child task chains. Every subagent trace includes its parent's trace ID.
- **Acceptance criteria:**
  - Root task: `trace_id` generated
  - Child task: `trace_id` = parent's `trace_id`, `span_id` unique per child
  - Propagation verified across at least 3 nesting levels

### P0-7: CLI Trace Viewer
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P0-5, P0-6
- **Description:** `swarmctl trace <task_id>` command that displays a readable trace for any completed task.
- **Acceptance criteria:**
  - Displays: task metadata, timeline of events, tool calls, errors, duration
  - Supports `--json` flag for machine-readable output
  - Supports `--tree` flag for parent→child hierarchy view

---

## Phase 2: Hardening (P0)

### P0-8: Path Canonicalization
- **Priority:** P0
- **Effort:** M
- **Dependencies:** None
- **Description:** Resolve `.agent/.agents` mismatch. Pick one canonical path, update all references, create compat symlink for the other.
- **Acceptance criteria:**
  - Zero references to `.agents` in code (verified by grep)
  - All tests pass with canonical path
  - Compat symlink works for any external references

### P0-9: Duplicate Script Removal
- **Priority:** P0
- **Effort:** M
- **Dependencies:** None
- **Description:** Audit `scripts/` directory; identify duplicates by content hash and purpose; consolidate or remove.
- **Acceptance criteria:**
  - Zero duplicate scripts (verified by `swarmctl audit --duplicates`)
  - Each script has a unique purpose documented in header comment
  - No broken imports after removal

### P0-10: Missing Path Creation
- **Priority:** P0
- **Effort:** S
- **Dependencies:** None
- **Description:** Create all directories referenced by code but not present on disk. Prevents runtime errors from missing paths.
- **Acceptance criteria:**
  - All `os.makedirs(path, exist_ok=True)` calls verified against actual filesystem
  - No runtime "directory not found" errors in test suite

### P0-11: Silent Fallback Elimination
- **Priority:** P0
- **Effort:** L
- **Dependencies:** P0-2, P0-3, P0-4
- **Description:** Replace all silent fallbacks with explicit error + trace. Every fallback must log why it happened.
- **Acceptance criteria:**
  - Zero `except: pass` patterns in production code
  - Every fallback emits a trace with `level: warning` or higher
  - All fallbacks have a documented reason in code comments

### P0-12: Config Validation at Startup
- **Priority:** P0
- **Effort:** M
- **Dependencies:** None
- **Description:** Schema-validate all YAML configs at startup. Invalid config → process exits with clear message.
- **Acceptance criteria:**
  - All YAML configs validated against JSON Schema at startup
  - Invalid config → exit code 1 + message: which file, what's wrong, suggested fix
  - Valid config → no delay (<100ms validation)

### P0-13: Error Message Standardization
- **Priority:** P1
- **Effort:** L
- **Dependencies:** P0-11
- **Description:** Standardize all error messages to format: `[component] action failed: reason. Suggested fix: hint`.
- **Acceptance criteria:**
  - 100% of error messages follow standard format
  - Error messages reviewed for clarity by at least 2 team members
  - No generic "something went wrong" messages

---

## Phase 3: Contracts + Leases (P0, P1)

### P0-14: Task Contract Schema
- **Priority:** P0
- **Effort:** L
- **Dependencies:** None
- **Description:** Define YAML-based task contract schema with: input schema (JSON Schema), output schema (JSON Schema), timeout (seconds), retry policy (count + backoff).
- **Acceptance criteria:**
  - Schema supports all C1–C5 tier requirements
  - Schema validated by JSON Schema validator
  - Example contracts provided for each tier

### P0-15: Contract Validator
- **Priority:** P0
- **Effort:** M
- **Dependencies:** P0-14
- **Description:** Validates that subagent output matches the contract's output schema. Returns pass/fail with details.
- **Acceptance criteria:**
  - Catches type mismatches, missing fields, extra fields
  - Returns structured error: which field failed, expected type, actual type
  - Validation completes in <50ms

### P0-16: Lease Manager
- **Priority:** P0
- **Effort:** L
- **Dependencies:** None
- **Description:** Issues, tracks, and expires leases for subagent execution. Supports 10+ concurrent leases.
- **Acceptance criteria:**
  - Lease includes: lease_id, task_id, agent_id, timeout, issued_at, status
  - Lease expiry triggers within 5 seconds of timeout
  - No lease collisions (unique IDs guaranteed)

### P0-17: Lease Expiration Handler
- **Priority:** P0
- **Effort:** M
- **Dependencies:** P0-16
- **Description:** On lease expiry: kill subagent, emit trace, retry or escalate based on policy.
- **Acceptance criteria:**
  - Subagent killed gracefully (SIGTERM, then SIGKILL after 5s)
  - Trace emitted with reason and action_taken
  - Retry policy applied (up to max retries)
  - Escalation path triggered if max retries exceeded

### P0-18: Delegation Router
- **Priority:** P0
- **Effort:** L
- **Dependencies:** P0-14, P0-16
- **Description:** Routes subtasks to subagents with contract + lease attached. The core of fractal delegation.
- **Acceptance criteria:**
  - Successfully delegates a C3 task to 2+ subagents
  - Each subagent receives its contract and lease
  - Outputs collected and returned to parent

### P0-19: RALPH Convergence Adapter
- **Priority:** P0
- **Effort:** M
- **Dependencies:** P0-15
- **Description:** Wrap RALPH as a convergence checker: takes subagent outputs, scores against contract, returns pass/fail/retry.
- **Acceptance criteria:**
  - Scores output quality (0–1 scale)
  - Pass threshold configurable per tier
  - Returns structured decision: pass | fail | retry with reason

### P0-20: Fractal Decomposition Engine (MVP)
- **Priority:** P0
- **Effort:** XL
- **Dependencies:** P0-14, P0-18
- **Description:** Decomposes C3+ tasks into subtasks; assigns tier to each subtask; triggers delegation.
- **Acceptance criteria:**
  - Correctly decomposes at least 10 benchmark C3 tasks
  - Each subtask has a valid contract
  - Decomposition completes in <2 seconds

### P0-21: Compat Path Layer
- **Priority:** P0
- **Effort:** M
- **Dependencies:** P0-18
- **Description:** Routes tasks through old or new path based on feature flag. Output normalized to identical format.
- **Acceptance criteria:**
  - Feature flag controls routing
  - Output format identical regardless of path
  - No downstream consumer affected by path change

### P1-1: Contract Schema Registry
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P0-14
- **Description:** Versioned registry of contract schemas. Supports schema evolution without breaking existing contracts.
- **Acceptance criteria:**
  - Schema versioning (v1, v2, ...)
  - Backward-compatible schema changes
  - Deprecated schemas flagged

### P1-2: Lease Dashboard
- **Priority:** P2
- **Effort:** S
- **Dependencies:** P0-16
- **Description:** CLI command `swarmctl leases` showing active, expired, and failed leases.
- **Acceptance criteria:**
  - Shows: lease_id, task_id, agent_id, status, time_remaining
  - Filters by status, agent, task tier

---

## Phase 4: Dashboard + Replay (P1, P2)

### P1-3: Dashboard Shell
- **Priority:** P1
- **Effort:** L
- **Dependencies:** None
- **Description:** Premium UI shell with dark mode, glassmorphism, per Design DNA. Navigation structure for all views.
- **Acceptance criteria:**
  - Renders within 2 seconds
  - Dark mode by default
  - Navigation: Traces, Kanban, Timeline, Benchmarks
  - Micro-interactions on hover/focus

### P1-4: Trace Visualization
- **Priority:** P1
- **Effort:** L
- **Dependencies:** P0-5, P1-3
- **Description:** Timeline view of task traces with parent→child relationships. Click to expand details.
- **Acceptance criteria:**
  - Displays 1000+ traces without lag
  - Parent→child hierarchy visible
  - Click any event to see details (tool calls, errors, timing)

### P1-5: Kanban View
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P1-3
- **Description:** Tasks organized by state (13 states from Wave 4) on kanban board. Drag to filter.
- **Acceptance criteria:**
  - All 13 states represented as columns
  - Real-time updates via WebSocket
  - Filter by tier, agent, date range

### P1-6: Timeline View
- **Priority:** P2
- **Effort:** M
- **Dependencies:** P1-3
- **Description:** Gantt-style view of task execution over time. Useful for capacity planning.
- **Acceptance criteria:**
  - Displays tasks on time axis
  - Color-coded by tier
  - Zoom in/out (minute → day scale)

### P1-7: Cognitive Motion Signals
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P0-4, P1-3
- **Description:** Visual indicators for agent activity: thinking, waiting, blocked, completing.
- **Acceptance criteria:**
  - Signal updates within 500ms of state change
  - 4 states: thinking (pulse), waiting (idle), blocked (red), completing (green)
  - Animations smooth and non-distracting

### P1-8: Trace Replay Engine
- **Priority:** P1
- **Effort:** L
- **Dependencies:** P0-5, P0-6
- **Description:** Replay any completed task trace; compare with expected output. CLI and UI interface.
- **Acceptance criteria:**
  - Replay produces identical output for deterministic traces
  - Comparison shows: same, diff (with details)
  - CLI: `swarmctl replay <task_id>`
  - UI: "Replay" button on trace detail view

### P1-9: Regression Detector
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P1-8
- **Description:** Compare two traces; flag differences in tool calls, timing, output.
- **Acceptance criteria:**
  - Flags all tool-call differences
  - Flags timing differences >20%
  - Flags output differences (semantic comparison for text, hash for binary)

---

## Phase 5: Eval Flywheel (P1, P2)

### P1-10: Benchmark Task Suite
- **Priority:** P1
- **Effort:** L
- **Dependencies:** None
- **Description:** 50+ representative tasks across all C1–C5 tiers. Covers: code generation, debugging, analysis, UI generation, data processing.
- **Acceptance criteria:**
  - At least 10 tasks per tier
  - Each task has: input, expected output, quality criteria
  - Suite runs in <30 minutes

### P1-11: Chaos Injection Framework
- **Priority:** P2
- **Effort:** M
- **Dependencies:** P1-10
- **Description:** Inject failures (timeout, OOM, network error) during benchmark runs. Tests system resilience.
- **Acceptance criteria:**
  - Supports: timeout injection, OOM kill, network error simulation
  - Configurable failure rate (0–100%)
  - <5% false-positive rate (flaky tests)

### P1-12: Eval Metrics Calculator
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P1-10
- **Description:** Compute: success rate, latency, tool efficiency, output quality for benchmark runs.
- **Acceptance criteria:**
  - Metrics: success_rate, p50_latency, p99_latency, tool_calls_per_task, output_quality_score
  - Results stored in structured format (JSON)
  - Exportable to CSV for analysis

### P1-13: Quality Gate Runner
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P1-10, P1-12
- **Description:** Run benchmarks on every orchestrator change; block merge if metrics regress.
- **Acceptance criteria:**
  - Runs automatically on PR to main branch
  - Blocks merge if success_rate regresses >2%
  - Blocks merge if p99_latency increases >10%

### P1-14: Benchmark Dashboard
- **Priority:** P2
- **Effort:** M
- **Dependencies:** P1-12
- **Description:** Visualize benchmark results over time; trend analysis. Integrated into main dashboard.
- **Acceptance criteria:**
  - Shows metrics over time (line chart)
  - Flags regressions visually (red markers)
  - Filter by tier, date range, model

---

## Phase 6: Adaptive Optimization (P1, P2)

### P1-15: Runtime Complexity Analyzer
- **Priority:** P1
- **Effort:** L
- **Dependencies:** P1-10
- **Description:** Analyzes incoming task; estimates complexity score (0–1). Used for dynamic decomposition.
- **Acceptance criteria:**
  - Correctly classifies 90%+ of benchmark tasks
  - Analysis completes in <500ms
  - Score calibrated against benchmark ground truth

### P1-16: Dynamic Decomposition Engine
- **Priority:** P1
- **Effort:** XL
- **Dependencies:** P1-15, P0-20
- **Description:** Decomposes tasks at runtime based on complexity score (not pre-configured rules).
- **Acceptance criteria:**
  - Produces valid subtasks (validated by contract checker)
  - Decomposition adapts to task content (not just tier)
  - Completes in <2 seconds

### P1-17: Dynamic Swarm Sizer
- **Priority:** P1
- **Effort:** L
- **Dependencies:** P1-16
- **Description:** Adjusts concurrency based on available resources and task priority.
- **Acceptance criteria:**
  - Respects CPU/memory/token limits
  - No OOM or token exhaustion
  - Sizing decision logged with reasoning

### P1-18: Resource Budget Manager
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P1-17
- **Description:** Allocates CPU/memory/token budgets per subagent based on tier.
- **Acceptance criteria:**
  - Budget per subagent: CPU (cores), memory (MB), tokens (max)
  - Budget enforced (hard limits)
  - Budget exhaustion triggers graceful degradation

### P1-19: Adaptive Retry Policy
- **Priority:** P2
- **Effort:** M
- **Dependencies:** P1-12
- **Description:** Retry count adapts based on historical success rate for similar tasks.
- **Acceptance criteria:**
  - Reduces total retries by 20% vs. fixed retry policy
  - Uses benchmark data for adaptation
  - Configurable min/max retry bounds

### P1-20: Performance Tuner
- **Priority:** P2
- **Effort:** L
- **Dependencies:** P1-12
- **Description:** Uses benchmark data to optimize model selection per task type.
- **Acceptance criteria:**
  - Improves success rate by 10% vs. baseline
  - Model selection considers: task type, tier, historical performance
  - Tuning runs in shadow mode before activation

### P1-21: Compat Path Sunset
- **Priority:** P1
- **Effort:** M
- **Dependencies:** P1-16, P1-17
- **Description:** Remove old routing path; all tasks use fractal orchestration. Clean up compat layer.
- **Acceptance criteria:**
  - Zero references to old routing in code
  - All tests pass without compat layer
  - Feature flag removed from config

---

## Backlog Summary by Priority

| Priority | Count | Total Effort |
|----------|-------|--------------|
| P0 | 18 | ~14 M + 6 L + 2 XL |
| P1 | 17 | ~8 S + 6 M + 5 L + 2 XL |
| P2 | 3 | ~1 S + 2 M |

## Backlog Summary by Phase

| Phase | P0 | P1 | P2 | Total |
|-------|----|----|----|-------|
| Phase 1 | 6 | 1 | 0 | 7 |
| Phase 2 | 5 | 1 | 0 | 6 |
| Phase 3 | 8 | 2 | 0 | 10 |
| Phase 4 | 0 | 6 | 1 | 7 |
| Phase 5 | 0 | 4 | 2 | 6 |
| Phase 6 | 0 | 6 | 1 | 7 |
| **Total** | **19** | **20** | **4** | **43** |
