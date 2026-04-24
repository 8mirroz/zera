# Execution Surface Map — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Scope:** End-to-end execution flow from entrypoint to artifact  

---

## 1. High-Level Execution Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ENTRYPOINT                                   │
│  zera chat -q "..."  │  hermes -p zera chat  │  swarmctl.py ...     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   CLASSIFICATION / ROUTING                            │
│                                                                       │
│  1. Intent Classification → C1–C5 tier (by prompt/task description)   │
│  2. router.yaml → workflow path (path-fast / path-quality / path-swarm)│
│  3. models.yaml → model alias resolution ($MODEL_*)                   │
│  4. RegistryWorkflowResolver → workflow definition + skill metadata   │
│  5. motion_awareness → capability activation (GSAP/Framer/CSS)        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW RESOLUTION                                │
│                                                                       │
│  RegistryWorkflowResolver.workflow_path_for_complexity(complexity)    │
│    → configs/registry/workflows/path-{fast,quality,swarm}.yaml       │
│    → loads workflow definition + referenced skills                    │
│                                                                       │
│  RegistryWorkflowResolver.load_workflow(rel_path)                     │
│  RegistryWorkflowResolver.load_skill(skill_id)                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   RUNTIME EXECUTION                                   │
│                                                                       │
│  RuntimeRegistry.select(complexity, channel) → runtime provider       │
│    agent_os_python   → local Python execution                        │
│    zeroclaw          → Telegram edge/streaming                        │
│    hermes            → Hermes gateway + cron + vault                  │
│    claw_code         → Code execution sandbox                         │
│    mlx_lm            → Local Metal inference                          │
│                                                                       │
│  ZeraCommandOS:                                                       │
│    resolve()  → command_id, mode_binding, loop_binding                │
│    render()   → assembled prompt (context + skills + constraints)      │
│    execute()  → _execute_prompt() → zera chat / hermes chat           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY EMIT                                   │
│                                                                       │
│  emit_event(event_type, payload) → logs/agent_traces.jsonl           │
│  emit_zera_command_event(...) → same sink + zera_command_runtime tag  │
│  emit_workflow_event(...) → structured lifecycle events              │
│                                                                       │
│  Trace path: logs/agent_traces.jsonl (JSONL, schema v2.1)            │
│  Event fields: ts, run_id, event_type, level, component, data + extras│
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ARTIFACTS                                          │
│                                                                       │
│  Code changes: repos/{apps,mcp,packages,telegram}/<name>/            │
│  Documentation: docs/ki/, docs/adr/, docs/patterns/                  │
│  Memory writes: .agents/memory/memory.jsonl, working_memory.json     │
│  Evolution state: .agents/evolution/state.json, telemetry.jsonl        │
│  Branch manifests: docs/remediation/hermes-zera/.../artifacts/wave4/ │
│  Reports: vault/reports/, outputs/reliability/                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Execution Files

### 2.1 Command Runtime

| File | Role | Key Functions |
|------|------|---------------|
| `scripts/zera/zera_command_runtime.py` | Bridge between CLI and ZeraCommandOS | `resolve`, `render`, `execute`, `branch-manifest`, `branch-merge`, `governor-check`, `import-validate` |
| `agent_os/zera_command_os.py` | Core command OS logic | `ZeraCommandOS`: command catalog, resolution, prompt rendering, branch management, merge records |

### 2.2 Routing & Model Selection

| File | Role | Key Functions |
|------|------|---------------|
| `agent_os/model_router.py` | `ModelRouter` + `UnifiedRouter` | `route()`, model alias resolution, tier selection |
| `agent_os/registry_workflows.py` | `RegistryWorkflowResolver` | `workflow_path_for_complexity()`, `load_workflow()`, `load_skill()` |
| `configs/orchestrator/router.yaml` | Routing config SoT | Tier definitions, model aliases, workflow assignments, motion triggers |
| `configs/orchestrator/models.yaml` | Model alias registry SoT | 30+ model aliases, Hermes profile defaults |

### 2.3 Runtime Providers

| File | Role | Capabilities |
|------|------|-------------|
| `agent_os/runtime_registry.py` | Runtime selection | `select()`, provider management |
| `agent_os/runtime_providers/agent_os_python.py` | Local Python runtime | local_execution, background_jobs, mcp_tools |
| `agent_os/runtime_providers/zeroclaw.py` | Telegram runtime | telegram, edge, streaming, persona_mode |
| `agent_os/runtime_providers/hermes.py` | Hermes gateway | local_execution, mcp, cron, vault_access |
| `agent_os/runtime_providers/claw_code.py` | Code sandbox | local_execution, code_execution, file_ops |
| `agent_os/runtime_providers/mlx_provider.py` | Local MLX inference | local_inference, metal_acceleration |

### 2.4 Observability

| File | Role | Key Functions |
|------|------|---------------|
| `agent_os/observability.py` | Event emission | `emit_event()`, `emit_workflow_event()`, `emit_zera_command_event()`, `TraceEmitter` |
| `scripts/trace_validator.py` | Trace validation | Schema validation, legacy compat |
| `scripts/trace_metrics_materializer.py` | Metrics extraction | Trace → dashboard metrics |
| `configs/tooling/trace_schema.json` | Schema SoT | v2.1, 40+ event types |

### 2.5 Evolution & Self-Improvement

| File | Role | Key Functions |
|------|------|---------------|
| `scripts/zera/zera-evolutionctl.py` | Evolution lifecycle | shadow-prepare, promote-enable, promote-rollback, status, start, stop |
| `scripts/internal/self_evolution_loop.py` | Core evolution loop | 10 phases: observe → classify → score → promote → evolve → evaluate → reflect → ... |
| `scripts/internal/reliability_orchestrator.py` | Reliability orchestration | Test suite orchestration, failure analysis |

### 2.6 Swarm & Coordination

| File | Role | Key Functions |
|------|------|---------------|
| `agent_os/swarm/branch_lock.py` | Branch locking | Lease-based branch isolation |
| `agent_os/swarm/lane_events.py` | Lane event system | Lane-specific event emission |
| `agent_os/approval_engine.py` | Approval gates | Human-in-the-loop approval flow |
| `agent_os/stop_controller.py` | Stop signals | Task cancellation, graceful shutdown |
| `agent_os/stop_controller.py` | Stop signals | Task cancellation, graceful shutdown |

### 2.7 CLI Orchestration

| File | Role | Key Functions |
|------|------|---------------|
| `repos/packages/agent-os/scripts/swarmctl.py` | Primary orchestration CLI | `doctor`, `publish-skills`, benchmarks, eval, trace validation, drift detection |
| `scripts/zera/zera-command.sh` | Zera command wrapper | Subprocess invocation of zera_command_runtime.py |

---

## 3. Execution Path Examples

### 3.1 Simple Task (C1/C2)

```
User: "Add a validation function to foo.py"
  → Intent classified: C2 (Simple)
  → router.yaml: C2 → path-fast.yaml, primary_model=$MODEL_LOCAL_MULTIPURPOSE
  → models.yaml: $MODEL_LOCAL_MULTIPURPOSE = ollama/qwen3.5:9b-q4_K_M
  → RegistryWorkflowResolver → loads configs/registry/workflows/path-fast.yaml
  → RuntimeRegistry → agent_os_python (prefer_local_for: C1, C2)
  → ZeraCommandOS.resolve() → command catalog lookup
  → ZeraCommandOS.render() → assemble prompt (context + skills)
  → _execute_prompt() → subprocess: zera chat -q "..."
  → emit_event("agent_run_completed", {...})
  → logs/agent_traces.jsonl ← JSONL event
```

### 3.2 Complex Task (C4/C5)

```
User: "Redesign the authentication system with OAuth2"
  → Intent classified: C4 (Complex)
  → router.yaml: C4 → path-swarm.yaml, primary_model=$MODEL_ARCHITECT_PRIMARY
  → models.yaml: $MODEL_ARCHITECT_PRIMARY = deepseek/deepseek-r1:free
  → ralph_loop: enabled, iterations=5
  → human_audit_required: true
  → RuntimeRegistry → prefer_cloud_for: C4, C5
  → ZeraCommandOS.render() → full prompt with role contracts
  → _execute_prompt() → hermes -p zera chat -q "..."
  → ralph_loop runs 5 iterations → score each → pick best
  → emit_event("ralph_iteration_started", ...) × 5
  → emit_event("ralph_best_selected", ...)
  → emit_event("agent_run_completed", ...)
```

### 3.3 Zera Command Execution

```
$ zera-command resolve --command evolve --objective "Optimize router tiers"
  → zera_command_runtime.py: main() → cmd=resolve
  → ZeraCommandOS.resolve(command_id="evolve", objective=...)
  → Returns: command_id, mode_binding, loop_binding, workflow_type
  → emit_zera_command_event("zera_command_resolved", {...})
  → logs/agent_traces.jsonl ← event
```

### 3.4 Evolution Cycle

```
$ zera-evolutionctl start --cycles 3
  → zera-evolutionctl.py: cmd_start()
  → PID file created (.agents/evolution/evolutionctl.pid)
  → Core loop: self_evolution_loop.py
    Phase 1: OBSERVE → read telemetry, gather metrics
    Phase 2: CLASSIFY → classify candidates
    Phase 3: SCORE → heuristic + LLM scoring
    Phase 4: PROMOTE → attempt-bound promotion
    Phase 5: EVOLVE → apply changes
    Phase 6: EVALUATE → run benchmarks
    Phase 7: REFLECT → self-reflection
    ... repeat for N cycles
  → emit events to .agents/evolution/telemetry.jsonl
  → emit events to logs/agent_traces.jsonl
```

---

## 4. State Transfer Mechanisms

| Transfer | Mechanism | Format |
|----------|-----------|--------|
| Router → Runtime | `router.yaml` loaded by `ModelRouter._load_config()` | YAML → Python dict |
| Command Runtime → Execution | `ZeraCommandOS.render_prompt()` → prompt text → subprocess | Text |
| Events → Traces | `emit_event()` → JSONL append | JSON lines |
| Evolution State | `.agents/evolution/state.json` → read/write | JSON |
| Memory → Retrieval | `.agents/memory/memory.jsonl` → BM25 index → retrieve | JSONL → index → results |
| Branch → Merge | Branch manifest (JSON) → `create_branch_merge_record()` | JSON |
| Skills → Execution | `.agents/skills/<name>/SKILL.md` → loaded into context | Markdown |
| Workflow → Execution | `configs/registry/workflows/*.yaml` → `load_workflow()` | YAML → Python dict |

---

## 5. Failure Handling Points

| Component | Failure Mode | Recovery |
|-----------|-------------|----------|
| `ModelRouter` | Config not found, parse error | `ModelRouterError` raised |
| `ZeraCommandOS` | Command not found | Degraded resolution, rollback path |
| `RuntimeRegistry` | Provider unavailable | Fallback to next provider in chain |
| `emit_event` | Trace file unavailable | Creates directory, appends |
| `self_evolution_loop` | Phase failure | Telemetry logged, loop continues |
| `zera-evolutionctl` | Promotion gate fail | Attempt binding, rollback available |
| `background_scheduler` | Job timeout | Dead letter queue |
| `approval_engine` | Approval timeout | Escalation path |
| `StopController` | Stop signal | Graceful shutdown, state save |
