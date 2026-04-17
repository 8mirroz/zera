# Current Orchestration Graph — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Source:** Code forensics (not documentation claims)  
> **Scope:** How orchestration actually works in the current codebase  

---

## 1. Orchestration Model: Orchestrated, Not Choreographed

**Finding:** The system uses **centralized orchestration**, not decentralized choreography.

- Task routing decisions are made by a single `UnifiedRouter` / `ModelRouter` that reads `router.yaml`
- Workflow resolution is done by a single `RegistryWorkflowResolver` that reads registry YAML files
- Command execution is centralized through `ZeraCommandOS` which owns the command catalog
- There is **no peer-to-peer agent coordination** — agents do not directly communicate with each other
- "Swarm" is a workflow name (`path-swarm.yaml`), not an actual multi-agent parallel execution engine

**Conclusion:** The current system is a **single-agent orchestrated pipeline** with "swarm" being a workflow label, not a swarm topology.

---

## 2. Orchestration Node Graph

```
┌──────────────────────────────────────────────────────────────────────┐
│                         INPUT                                         │
│   zera chat -q / hermes -p zera chat / swarmctl.py / API call         │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 1: Intent Classification                                        │
│  Location: Implicit in caller / UnifiedRouter                         │
│  Input: Task description (text)                                       │
│  Output: C1–C5 tier classification                                    │
│  Mechanism: Keyword/pattern matching (not ML-based)                   │
│  SoT: configs/orchestrator/router.yaml (tier definitions)              │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 2: UnifiedRouter / ModelRouter                                  │
│  Location: agent_os/model_router.py                                   │
│  Input: tier (C1–C5), task description                                │
│  Output: model alias ($MODEL_*), workflow path, fallback chain        │
│  Mechanism: YAML config lookup + env var expansion                    │
│  SoT: configs/orchestrator/models.yaml                                │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 3: RegistryWorkflowResolver                                     │
│  Location: agent_os/registry_workflows.py                             │
│  Input: workflow path (e.g., configs/registry/workflows/path-swarm.yaml)│
│  Output: Workflow definition + skill metadata                         │
│  Mechanism: YAML file loading with caching                            │
│  SoT: configs/registry/workflows/*.yaml                               │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 4: PersonaModeRouter                                            │
│  Location: agent_os/persona_mode_router.py                            │
│  Input: task context, current mode                                    │
│  Output: Mode binding (research/execute/review/etc.)                   │
│  Mechanism: JSON config lookup (zera_mode_router.json)                 │
│  SoT: configs/tooling/zera_mode_router.json                           │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 5: RuntimeRegistry                                              │
│  Location: agent_os/runtime_registry.py                               │
│  Input: complexity tier, channel type                                 │
│  Output: Selected runtime provider                                    │
│  Mechanism: Selection policy from runtimes.yaml                       │
│  SoT: configs/tooling/runtime_providers.json (canonical)               │
│       configs/orchestrator/runtimes.yaml (derived view)                │
│                                                                       │
│  Providers (5):                                                       │
│  - agent_os_python: local execution, background jobs                   │
│  - zeroclaw: Telegram edge, streaming, persona mode                    │
│  - hermes: gateway, cron, vault access                                 │
│  - claw_code: code sandbox                                             │
│  - mlx_lm: local Metal inference                                       │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 6: ZeraCommandOS                                                │
│  Location: agent_os/zera_command_os.py                                │
│  Input: command_id, objective, client_id                              │
│  Output: Resolved command metadata + rendered prompt                  │
│  Mechanism: YAML registry lookup + prompt assembly                    │
│  Sub-nodes:                                                          │
│    6a. command_catalog() — list available commands                     │
│    6b. resolve() — match command to objective                          │
│    6c. render() — assemble prompt (context + skills + constraints)     │
│    6d. create_branch_manifest() — branching metadata                   │
│    6e. create_branch_merge_record() — merge metadata                   │
│    6f. evaluate_governor() — governance evaluation                     │
│    6g. validate_import_activation() — import validation                │
│  SoT: configs/tooling/zera_command_registry.yaml                       │
│       configs/tooling/zera_client_profiles.yaml                        │
│       configs/tooling/zera_branching_policy.yaml                       │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 7: Prompt Execution                                             │
│  Location: zera_command_runtime.py → _execute_prompt()                │
│  Input: Rendered prompt text                                          │
│  Output: Exit code (0 = success)                                      │
│  Mechanism: subprocess call to `zera chat -q` or `hermes chat`        │
│  Note: NO internal LLM call — delegates to external client            │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 8: Observability Emit                                           │
│  Location: agent_os/observability.py                                  │
│  Input: Event type + payload                                          │
│  Output: JSONL line appended to logs/agent_traces.jsonl               │
│  Mechanism: Append-only file write                                    │
│  SoT: configs/tooling/trace_schema.json (v2.1)                        │
│                                                                       │
│  Event types (40+): triage_decision, route_decision, agent_run_*,     │
│  ralph_*, background_job_*, tool_call, verification_result, etc.       │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 9: Memory Operations (optional)                                 │
│  Location: agent_os/memory_store.py, agent_os/memory/                 │
│  Input: Memory writes from agent execution                            │
│  Output: Updated .agents/memory/memory.jsonl, indexes                 │
│  Mechanism: Append to JSONL + BM25 index update                       │
│  Governed by: configs/tooling/memory_write_policy.yaml                 │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 10: RALPH Loop (C3+ tasks)                                      │
│  Location: agent_os/ralph_loop.py                                     │
│  Input: Task, initial output, scoring criteria                        │
│  Output: Best-of-N output (N = iterations from router.yaml)           │
│  Mechanism: Iterative refinement with scoring                         │
│  Config: router.yaml → ralph_loop (enabled, iterations, threshold)    │
│  Events: ralph_iteration_started, ralph_iteration_scored,             │
│          ralph_stop_decision, ralph_best_selected                     │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 11: Approval Engine (gated actions)                             │
│  Location: agent_os/approval_engine.py                                │
│  Input: Action requiring approval                                     │
│  Output: ApprovalTicket (pending/approved/rejected)                    │
│  Mechanism: Persistent JSON file (.agents/runtime/approvals.json)      │
│  Gates: destructive, external, privacy_sensitive, financial, etc.     │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  NODE 12: Evolution Controller (self-improvement)                     │
│  Location: scripts/zera/zera-evolutionctl.py                          │
│  Input: Evolution command (start/stop/promote/rollback)                │
│  Output: Evolution state changes, promotion artifacts                  │
│  Mechanism: Lifecycle management of self_evolution_loop.py             │
│  Sub-nodes:                                                          │
│    12a. shadow-prepare — clone Hermes profile                          │
│    12b. shadow-upgrade — test in shadow                                │
│    12c. promote-enable — enable promotion with attempt binding         │
│    12d. promote-rollback — rollback to snapshot                        │
│    12e. status/doctor — health checks                                  │
│  SoT: .agents/evolution/state.json, promotion_state.json               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Key Orchestration Files

| File | Role | Lines | Complexity |
|------|------|-------|------------|
| `agent_os/model_router.py` | UnifiedRouter + ModelRouter | 442 | Medium |
| `agent_os/registry_workflows.py` | RegistryWorkflowResolver | 140 | Low |
| `agent_os/zera_command_os.py` | ZeraCommandOS (command registry) | 426 | Medium |
| `agent_os/runtime_registry.py` | RuntimeRegistry (5 providers) | 464 | High |
| `agent_os/observability.py` | Event emission (40+ event types) | ~200 | Medium |
| `agent_os/ralph_loop.py` | RALPH iterative refinement | TBD | Medium |
| `agent_os/approval_engine.py` | Approval gates | 172 | Low |
| `agent_os/stop_controller.py` | Stop signals | 126 | Low |
| `agent_os/swarm/branch_lock.py` | Branch lock collision detection | ~50 | Low |
| `agent_os/swarm/lane_events.py` | Lane event system | TBD | Low |
| `agent_os/persona_mode_router.py` | Persona mode routing | TBD | Medium |
| `agent_os/background_scheduler.py` | Background job scheduling | TBD | Medium |
| `agent_os/background_jobs.py` | Background job registry | TBD | Low |
| `agent_os/memory_store.py` | Memory store | TBD | Medium |
| `agent_os/platform_controller.py` | Platform orchestration | TBD | High |
| `agent_os/eggent_*.py` | 8 Eggent modules | ~1000 total | High |
| `scripts/zera/zera-evolutionctl.py` | Evolution lifecycle | 2893 | Very High |
| `scripts/internal/self_evolution_loop.py` | Core evolution loop (10 phases) | ~900 | High |
| `scripts/zera/zera_command_runtime.py` | CLI bridge | ~360 | Medium |
| `repos/packages/agent-os/scripts/swarmctl.py` | Orchestration CLI | 5246 | Very High |

---

## 4. Orchestration Characteristics

### 4.1 Decision Points

| Decision | Where Made | Input | Output |
|----------|-----------|-------|--------|
| Task tier (C1–C5) | Caller / UnifiedRouter | Task description | Tier string |
| Model selection | UnifiedRouter | Tier + models.yaml | Model alias |
| Workflow selection | RegistryWorkflowResolver | Tier + router.yaml | Workflow YAML path |
| Runtime selection | RuntimeRegistry | Tier + channel | Runtime provider |
| Mode binding | PersonaModeRouter | Task context | Mode string |
| Command resolution | ZeraCommandOS | Command ID + objective | Command metadata |
| Approval required | ApprovalEngine | Action type + risk | ApprovalTicket |
| RALPH iterations | router.yaml config | Tier + scoring | N iterations |
| Evolution action | zera-evolutionctl | CLI command | Evolution state change |

### 4.2 State Management

| State | Location | Format | Writer | Reader |
|-------|----------|--------|--------|--------|
| Router config | `configs/orchestrator/router.yaml` | YAML | Human | UnifiedRouter |
| Model registry | `configs/orchestrator/models.yaml` | YAML | Human | ModelRouter |
| Runtime state | `.agents/runtime/*.json` | JSON | Runtime providers | RuntimeRegistry |
| Approval state | `.agents/runtime/approvals.json` | JSON | ApprovalEngine | Auditor |
| Stop signals | `.agents/runtime/stop-signals.json` | JSON | StopController | All agents |
| Background jobs | `.agents/runtime/background-jobs.json` | JSON | BackgroundJobRegistry | Scheduler |
| Evolution state | `.agents/evolution/state.json` | JSON | zera-evolutionctl | All evolution tools |
| Telemetry | `.agents/evolution/telemetry.jsonl` | JSONL | self_evolution_loop.py | Dashboard |
| Traces | `logs/agent_traces.jsonl` | JSONL | emit_event() | Validator, dashboard |
| Memory | `.agents/memory/memory.jsonl` | JSONL | All agents | Retriever |

### 4.3 Concurrency Model

**Current state: Single-threaded orchestration.**

- No true parallel agent execution in the current codebase
- `background_scheduler.py` supports background jobs, but they are sequential
- `branch_lock.py` detects collisions but does not enforce locks (no lock file mechanism)
- `swarm/lane_events.py` provides lane-scoped events but no lane isolation
- RALPH loop is sequential (iteration 1 → score → iteration 2 → ...)
- Evolution loop is sequential (10 phases executed in order)

---

## 5. Orchestration Flow Summary

```
Task → [Classify C1–C5] → [Route to Model] → [Resolve Workflow] → [Bind Mode]
     → [Select Runtime] → [Resolve Command] → [Render Prompt] → [Execute]
     → [RALPH Loop if C3+] → [Approval if gated] → [Emit Trace] → [Write Memory]
```

**Key insight:** The entire pipeline is a **linear sequence of config lookups** → **prompt assembly** → **external LLM call** → **trace emit**. There is no internal reasoning, no task decomposition, no subagent spawning, no parallel execution.
