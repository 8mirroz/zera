# System Inventory — Zera Fractal Multi-Agent Architecture Audit

> **Date:** 2026-04-13  
> **Scope:** Full workspace (`repos/*`, `configs/*`, `scripts/*`, `.agents/*`, `docs/*`)  
> **Status:** Current execution surface snapshot  

---

## 1. Control-Plane Configs

| Path | Purpose | Format | SoT? | Consumers |
|------|---------|--------|------|-----------|
| `configs/orchestrator/router.yaml` | Tier routing (C1–C5), model selection, motion-aware routing, handoff safeguards | YAML | ✅ Yes | `ModelRouter`, `UnifiedRouter`, `RegistryWorkflowResolver`, `swarmctl.py`, `zera_command_runtime.py` |
| `configs/orchestrator/models.yaml` | Model alias registry (30+ aliases), Hermes profile defaults | YAML | ✅ Yes | All routing code, `swarmctl.py` doctor |
| `configs/orchestrator/runtimes.yaml` | Runtime registry (5 runtimes), selection policy | YAML (derived from `runtime_providers.json`) | ⚠️ Derived | `RuntimeRegistry`, runtime providers |
| `configs/orchestrator/catalog.json` | Artifact catalog (100+ entries) | JSON | ✅ Yes | `AssetRegistry`, catalog queries |
| `configs/orchestrator/memory_audit_schema.yaml` | Memory audit schema | YAML | ✅ Yes | Memory audit tools |
| `configs/orchestrator/obsidian_memory.yaml` | Obsidian memory integration config | YAML | ✅ Yes | Obsidian memory scripts |
| `configs/orchestrator/AGENT_ROLE_CONTRACTS.md` | Role contract templates | Markdown | ✅ Yes | Role enforcement system |
| `configs/registry/indexes/*.yaml` | Registry indexes (agents, skills, workflows) | YAML | ✅ Yes | `RegistryWorkflowResolver` |
| `configs/registry/personas/*.yaml` | Persona definitions (6 personas) | YAML | ✅ Yes | `persona_mode_router.py`, `persona_eval.py` |
| `configs/registry/schemas/*.yaml` | JSON/YAML schemas (agent, skill, workflow, task, persona, adapter) | YAML | ✅ Yes | Validation tools |
| `configs/registry/skills/*.yaml` | Registered skills (12 skills) | YAML | ✅ Yes | Skill selection system |
| `configs/registry/workflows/*.yaml` | Registered workflows (5 workflows: path-fast, path-quality, path-swarm, etc.) | YAML | ✅ Yes | `RegistryWorkflowResolver` |
| `configs/registry/taxonomies/*.yaml` | Taxonomy definitions (domains, phases, priorities, risk-levels, tools) | YAML | ✅ Yes | Classification system |
| `configs/tooling/trace_schema.json` | Trace event schema v2.1 | JSON | ✅ Yes | `observability.py`, `trace_validator.py` |
| `configs/tooling/agent_os_trace_schema.json` | Legacy trace schema | JSON | ⚠️ Legacy | Backward compat |
| `configs/tooling/mcp_profiles.json` | MCP server profiles | JSON | ✅ Yes | MCP integration layer |
| `configs/tooling/background_jobs.yaml` | Background job definitions | YAML | ✅ Yes | `background_scheduler.py` |
| `configs/tooling/runtime_providers.json` | Runtime provider definitions (canonical for runtimes.yaml) | JSON | ✅ Yes | `RuntimeRegistry`, `runtimes.yaml` |
| `configs/tooling/zera_command_registry.yaml` | Zera command definitions | YAML | ✅ Yes | `zera_command_runtime.py`, `ZeraCommandOS` |
| `configs/tooling/zera_promotion_policy.yaml` | Promotion governance policy | YAML | ✅ Yes | `zera-evolutionctl.py` |
| `configs/tooling/evaluation-harness.yaml` | Evaluation harness config | YAML | ✅ Yes | Eval scripts |
| `configs/tooling/budget_policy.yaml` | Token/budget policy | YAML | ✅ Yes | Budget enforcement |
| `configs/tooling/autonomy_policy.yaml` | Autonomy policy | YAML | ✅ Yes | `autonomy_policy.py` |
| `configs/tooling/model_providers.json` | Model provider definitions | JSON | ✅ Yes | Model routing |
| `configs/tooling/memory_write_policy.yaml` | Memory write governance | YAML | ✅ Yes | Memory policy layer |
| `configs/tooling/drift-detection-rules.yaml` | Config drift detection | YAML | ✅ Yes | Drift detection scripts |
| `configs/tooling/zera_mode_router.json` | Zera mode routing config | JSON | ✅ Yes | `persona_mode_router.py` |
| `configs/tooling/zera_branching_policy.yaml` | Branch management policy | YAML | ✅ Yes | Branch manifest system |
| `configs/personas/zera/*` | Zera persona config (constitution, identity, modes, memory schema, tone, safety) | Mixed | ✅ Yes | Persona loader |
| `configs/adapters/hermes/*` | Hermes adapter config | YAML | ✅ Yes | Hermes integration |
| `configs/policies/import_governance.yaml` | Import governance policy | YAML | ✅ Yes | Import validation |

---

## 2. Workflow Registry

| Path | Purpose | Format | SoT? |
|------|---------|--------|------|
| `.agents/workflows/` | 44 workflow definition files | Markdown | ✅ Yes |
| `configs/registry/workflows/*.yaml` | 5 registry workflow definitions | YAML | ✅ Yes |
| `.agents/skills/` | 29 published skills (SKILL.md files) | Markdown | ✅ Yes |
| `configs/registry/skills/*.yaml` | 12 registered skill definitions | YAML | ✅ Yes |
| `.agents/templates/compressed/` | T1–T7 prompt templates | Markdown | ✅ Yes |

---

## 3. Runtime Entrypoints

### 3.1 CLI Scripts

| Path | Purpose | Language | State |
|------|---------|----------|-------|
| `scripts/zera/zera_command_runtime.py` | Zera command OS bridge (resolve/render/execute/branch/governor) | Python | ✅ Active |
| `scripts/zera/zera-evolutionctl.py` | Evolution lifecycle controller (shadow/promote/rollback) | Python | ✅ Active |
| `scripts/zera/zera-command.sh` | Zera command wrapper | Bash | ✅ Active |
| `scripts/zera/zera-self-evolution.sh` | Self-evolution loop | Bash | ⚠️ Legacy (superseded by evolutionctl) |
| `scripts/zera/zera-infinite-loops.sh` | Infinite loop orchestrator (8 algorithms) | Bash | ⚠️ Legacy |
| `scripts/zera/zera-agent-intelligence.sh` | Agent intelligence intake | Bash | Active |
| `scripts/zera/zera-autonomous-launcher.sh` | Autonomous background job launcher | Bash | Active |
| `scripts/zera/zera-evolve.sh` | Evolution wrapper | Bash | ⚠️ Legacy |
| `repos/packages/agent-os/scripts/swarmctl.py` | Primary orchestration CLI (doctor, publish-skills, benchmarks, etc.) | Python | ✅ Active |
| `repos/packages/agent-os/scripts/trace_validator.py` | Trace file validator | Python | ✅ Active |
| `repos/packages/agent-os/scripts/trace_metrics_materializer.py` | Trace metrics extraction | Python | ✅ Active |
| `repos/packages/agent-os/scripts/routing_consistency_checker.py` | Routing config consistency | Python | ✅ Active |
| `repos/packages/agent-os/scripts/workflow_model_alias_validator.py` | Workflow/model alias validation | Python | ✅ Active |
| `repos/packages/agent-os/scripts/skill_drift_validator.py` | Skill drift validation | Python | ✅ Active |

### 3.2 Daemons / Background

| Path | Purpose | Language | State |
|------|---------|----------|-------|
| `scripts/internal/self_evolution_loop.py` | Core self-evolution loop (10 phases) | Python | ✅ Active |
| `scripts/internal/idle_rl_daemon.py` | Idle RL background task daemon | Python | Active |
| `scripts/internal/scout_daemon.py` | Scout daemon | Python | Active |
| `scripts/internal/beta_manager.py` | Beta feature manager | Python | Active |
| `scripts/internal/scaffold_v5.py` | Project scaffolding | Python | Active |
| `scripts/internal/reliability_orchestrator.py` | Reliability orchestration | Python | ✅ Active |
| `scripts/hermes/hermes-dashboard.sh` | Hermes dashboard | Bash | Active |

### 3.3 Agent-OS Core Modules

| Module | Purpose | SoT? |
|--------|---------|------|
| `agent_os/model_router.py` | `ModelRouter` + `UnifiedRouter` — model selection logic | ✅ Yes |
| `agent_os/registry_workflows.py` | `RegistryWorkflowResolver` — workflow resolution from registry | ✅ Yes |
| `agent_os/observability.py` | `emit_event`, `emit_workflow_event`, `emit_zera_command_event`, `TraceEmitter` | ✅ Yes |
| `agent_os/zera_command_os.py` | `ZeraCommandOS` — command resolution, prompt rendering, branch management | ✅ Yes |
| `agent_os/runtime_registry.py` | `RuntimeRegistry` — runtime provider management | ✅ Yes |
| `agent_os/runtime_providers/*.py` | 5 runtime provider implementations | ✅ Yes |
| `agent_os/swarm/branch_lock.py` | Branch locking mechanism | ✅ Yes |
| `agent_os/swarm/lane_events.py` | Lane event system | ✅ Yes |
| `agent_os/approval_engine.py` | Approval gate engine | ✅ Yes |
| `agent_os/stop_controller.py` | Stop signal controller | ✅ Yes |
| `agent_os/background_scheduler.py` | Background job scheduler | ✅ Yes |
| `agent_os/background_jobs.py` | Background job registry | ✅ Yes |
| `agent_os/memory_store.py` | Memory store operations | ✅ Yes |
| `agent_os/ralph_loop.py` | RALPH iterative improvement loop | ✅ Yes |
| `agent_os/eggent_*.py` | 8 Eggent modules (algorithm, contracts, router adapter, escalation, etc.) | ✅ Yes |
| `agent_os/persona_mode_router.py` | Persona-based mode routing | ✅ Yes |
| `agent_os/platform_controller.py` | Platform-level orchestration | ✅ Yes |
| `agent_os/contracts.py` | Contract definitions (ModelRouteInput/Output) | ✅ Yes |
| `agent_os/registry.py` | Asset registry | ✅ Yes |

---

## 4. Memory Stores

| Path | Type | Retention | Writers | Readers |
|------|------|-----------|---------|---------|
| `.agents/memory/memory.jsonl` | Append-only memory log | Unbounded | All agents | Retriever |
| `.agents/memory/goal-stack.json` | Current goal stack | Volatile | Goal manager | Agent runtime |
| `.agents/memory/skill_index.json` | Skill index | Persistent | `swarmctl.py publish-skills` | Skill router |
| `.agents/memory/router_embeddings.json` | Router embeddings | Persistent | Embedding generator | Router |
| `.agents/memory/indexes/` | BM25 indexes | Persistent | Index builder | Retriever |
| `.agents/memory/solutions/index.yaml` | Solution index | Persistent | Solution indexer | Retriever |
| `.agents/memory/build-library/` | Build memory | Persistent | Build memory writer | Agent OS |
| `.agents/memory/quarantine/` | Quarantined entries | Persistent | Quarantine system | Auditor |
| `.agents/memory/repos-catalog/` | Repository catalog | Persistent | Catalog builder | Agent OS |
| `.agents/evolution/telemetry.jsonl` | Evolution telemetry | Persistent | `self_evolution_loop.py` | Dashboard, auditor |
| `.agents/evolution/state.json` | Evolution state | Persistent | Evolution controller | All |
| `.agents/evolution/evolutionctl-state.json` | Evolutionctl state | Persistent | `zera-evolutionctl.py` | Evolutionctl |
| `.agents/evolution/promotion_state.json` | Promotion state | Persistent | `zera-evolutionctl.py` | Promotion system |
| `.agents/evolution/meta_memory.json` | Meta memory | Persistent | Evolution system | Agent |
| `.agents/runtime/approvals.json` | Approval records | Persistent | Approval engine | Auditor |
| `.agents/runtime/background-jobs.json` | Background job state | Persistent | Background scheduler | Monitor |
| `.agents/runtime/background-control.json` | Background control state | Persistent | Background controller | Monitor |
| `.agents/runtime/model_ovl.yaml` | Model overlay config | Persistent | Model manager | Router |
| `vault/loops/.evolve-state.json` | Legacy evolution state | Persistent | Legacy loops | Legacy readers |
| `vault/knowledge/ki/` | Knowledge items | Persistent | Knowledge capture | All |
| `docs/ki/` | Knowledge items (flat) | Persistent | Knowledge capture | All |

---

## 5. Trace Sinks

| Path | Format | Schema | Validator | Dashboard |
|------|--------|--------|-----------|-----------|
| `logs/agent_traces.jsonl` | JSONL (one event per line) | `configs/tooling/trace_schema.json` (v2.1) | `repos/packages/agent-os/scripts/trace_validator.py` | `scripts/hermes/hermes-dashboard.sh` |
| `.agents/evolution/telemetry.jsonl` | JSONL (evolution events) | Implicit (evolution loop format) | None explicit | `vault/reports/evolution_dashboard.md` |
| `.agents/evolution/loop.log` | Plain text log | None | None | None |
| `.agents/evolution/evolutionctl.out.log` | Plain text log | None | None | None |

---

## 6. Evaluation & Benchmark Harness

| Path | Type | Thresholds | State |
|------|------|------------|-------|
| `repos/packages/agent-os/benchmark_routing.py` | Routing benchmark | Implicit | ✅ Active |
| `repos/packages/agent-os/tests/` | Test suite (~102 test files) | pytest | ✅ Active |
| `repos/packages/agent-os/scripts/run_regression_suite.py` | Regression suite | Implicit | ✅ Active |
| `repos/packages/agent-os/scripts/skill_accuracy_benchmark.py` | Skill accuracy benchmark | Implicit | ✅ Active |
| `scripts/benchmarks/21st_collect_benchmarks.sh` | Benchmark collection script | Custom | ✅ Active |
| `docs/ki/benchmark_latest.json` | Latest benchmark results | JSON | ✅ Active |
| `docs/ki/benchmark_latest.md` | Latest benchmark report | Markdown | ✅ Active |
| `docs/ki/benchmark_reports/` | Historical benchmark reports (10 reports) | Markdown | ✅ Active |
| `docs/ki/benchmark_anomalies.json` | Anomaly detection results | JSON | ✅ Active |
| `configs/tooling/benchmark_suite.json` | Benchmark suite definition | JSON | ✅ Active |
| `configs/tooling/evaluation-harness.yaml` | Evaluation harness config | YAML | ✅ Active |
| `configs/tooling/test_reliability_program.yaml` | Test reliability program | YAML | ✅ Active |
| `configs/tooling/test_suite_matrix.yaml` | Test suite matrix | YAML | ✅ Active |
| `configs/tooling/persona_eval_suite.json` | Persona evaluation suite | JSON | ✅ Active |
| `configs/tooling/runtime_benchmark_matrix.json` | Runtime benchmark matrix | JSON | ✅ Active |
| `configs/personas/zera/eval_cases.json` | Zera evaluation cases | JSON | ✅ Active |
| `outputs/reliability/latest/` | Latest reliability outputs (4 JSON files) | JSON | ✅ Active |

---

## 7. File Count Summary

| Area | Files (approximate) |
|------|-------------------|
| Total tracked files (*.py, *.ts, *.js, *.yaml, *.yml, *.json, *.md, *.sh) | ~613 |
| `.agents/` (runtime state) | 30+ |
| `configs/` (governance) | 80+ |
| `repos/packages/agent-os/src/` (core library) | 100+ |
| `repos/packages/agent-os/scripts/` (tooling) | 30+ |
| `repos/packages/agent-os/tests/` (tests) | 100+ |
| `scripts/zera/` (Zera-specific) | 15+ |
| `scripts/internal/` (internal daemons) | 8+ |
| `docs/` (documentation) | 60+ |
| `vault/` (knowledge graph) | 50+ |
| `configs/registry/` (registry) | 40+ |
| `.agents/workflows/` (workflow definitions) | 44 |
| `.agents/skills/` (skill definitions) | 29 |
