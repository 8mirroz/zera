# 01. System Inventory

## Кратко
- Audit target: Hermes runtime, Zera persona layer, Antigravity IDE control plane, operator-side Hermes/Gemini profiles.
- Canonical audit path создан: `docs/audits/agents/hermes-zera/2026-04-10__full-system-audit/`.
- Проиндексировано 259 релевантных файлов по зонам `configs/personas`, `configs/tooling`, `configs/skills`, `scripts`, `Zera`, `logs`, `outputs/reliability`, `.agent/*`.

## Классификация узлов
| Класс | Узлы |
|---|---|
| `runtime_canonical` | `configs/personas/zera/*`, `configs/tooling/zera_*`, `configs/tooling/runtime_providers.json`, `configs/tooling/autonomy_policy.yaml`, `configs/tooling/background_jobs.yaml`, `configs/global/memory_policy.yaml`, `scripts/zera-command.sh`, `scripts/zera_command_runtime.py`, `repos/packages/agent-os/src/agent_os/*`, `logs/agent_traces.jsonl` |
| `runtime_consumed_secondary` | `configs/orchestrator/router.yaml`, `configs/orchestrator/completion_gates.yaml`, `configs/orchestrator/user_profile.json`, `.agent/config/workflow_sets.active.json`, `.agent/runtime/*`, `.agent/memory/*`, `~/.hermes/profiles/antigravity/config.yaml`, `~/.gemini/antigravity/mcp_config.json`, `~/.hermes/profiles/zera/cron/*.json` |
| `derived/generated` | `docs/ki/benchmark_latest.*`, `docs/ki/benchmark_history.json`, `docs/ki/benchmark_anomalies.json`, `outputs/reliability/**`, `.agent/skills/.active_set_manifest.json`, `configs/orchestrator/catalog.json` |
| `narrative_only` | `Zera/*.md`, `docs/guides/hermes-agent-integration-guide.md`, `docs/guides/ZEROCLAW_ZERA_INTEGRATION_2026-03-11.md` |
| `legacy_or_ambiguous` | `configs/tooling/model_routing.json.DEPRECATED`, `scripts/test_mcp_profiles.py.bak`, `repos/packages/agent-os/src/logs/agent_traces.jsonl`, `logs/benchmark-latest.json` |

## Path Index
- Persona: `configs/personas/zera/manifest.yaml`, `identity.md`, `constitution.md`, `safety.md`, `relationship_boundaries.md`, `tone.md`, `modes.yaml`, `memory_schema.json`, `eval_cases.json`, `prompt_assembly.yaml`.
- Runtime bridge: `scripts/zera-command.sh`, `scripts/zera_command_runtime.py`.
- Core runtime: `repos/packages/agent-os/src/agent_os/agent_runtime.py`, `zera_command_os.py`, `runtime_registry.py`, `observability.py`, `persona_mode_router.py`, `memory_store.py`, `memory_policy_layer.py`.
- Governance/tooling: `configs/tooling/zera_command_registry.yaml`, `zera_client_profiles.yaml`, `zera_mode_router.json`, `zera_growth_governance.json`, `runtime_providers.json`, `zeroclaw_profiles.json`, `autonomy_policy.yaml`, `background_jobs.yaml`, `mcp_profiles.json`, `trace_schema.json`, `benchmark_suite.json`, `benchmark_config.json`, `evaluation-harness.yaml`, `drift-detection-rules.yaml`, `redteam_agent_failure_suite.json`.
- Operator state: `~/.hermes/profiles/antigravity/config.yaml`, `~/.gemini/antigravity/mcp_config.json`, `~/.hermes/profiles/zera/cron/*.json`.
- Evidence: `logs/agent_traces.jsonl`, `docs/ki/benchmark_latest.json`, `outputs/reliability/latest/*`.

## Orphan / Dead-Reference List
- `.agent/workflows/multi-agent-routing.md` referenced in repo instructions and workflow indexes, but absent.
- `.agent/workflows/*` cataloged in `.agent/config/workflow_sets.active.json` and `configs/tooling/workflow_sets_catalog.json`, but directory is effectively empty.
- Zera skill set declared in `configs/skills/ZERA_ACTIVE_SKILLS.md`, but `.agent/skills/.active_set_manifest.json` publishes none of `zera-core`, `zera-strategist`, `zera-researcher`, `zera-rhythm-coach`, `zera-muse`, `zera-style-curator`.
- `runtime_providers.json` declares enabled `mlx_lm`; `RuntimeRegistry` does not register it.

## Suspected Drift Zones
1. Runtime provider registry drift — `runtime_providers.json` declares `mlx_lm` enabled; `RuntimeRegistry._builtin_factories` has no `mlx_lm` key.
2. Workflow catalog drift — `.agent/workflows/*` is empty; `workflow_sets_catalog.json` and `workflow_sets.active.json` reference non-existent files.
3. Skill publication drift — `configs/skills/ZERA_ACTIVE_SKILLS.md` declares 6 Zera skills; `.agent/skills/.active_set_manifest.json` publishes none of them.
4. Benchmark validity drift — `benchmark_latest.json` reports pass while all 13 canonical cases are missing; 120 cases are repeats/samples.
5. Operator profile parity drift — `~/.hermes/profiles/` and `~/.gemini/antigravity/` operate outside repo governance; `hermes-sync-config.sh` is advisory only.
6. Memory policy enforcement drift — `memory_policy.yaml`, `memory_write_policy.yaml`, `MemoryPolicyLayer` exist but `agent_runtime.py` never invokes policy checks before memory writes.

## Additional Findings (Deepened Audit)

### Runtime Providers — Canonical vs Declared
| Provider | Declared Enabled | Factory Registered | Actually Instantiable |
|---|---|---|---|
| `agent_os_python` | ✅ yes | ✅ yes | ✅ yes |
| `zeroclaw` | ❌ disabled (env flag) | ✅ yes | conditional |
| `claw_code` | ❌ disabled (env flag) | ✅ yes | conditional |
| `mlx_lm` | ✅ yes in `runtime_providers.json` | ❌ no | ❌ impossible |

### Scripts — Invocation Analysis
| Script | Invoked By | Status | Risk |
|---|---|---|---|
| `zera_command_runtime.py` | `agent_runtime.py` via `ZeraCommandOS` | ✅ active | low |
| `hermes-sync-config.sh` | manual/advisory | ⚠️ advisory | medium — no parity enforcement |
| `hermes-dashboard.sh` | manual | ✅ passive | low |
| `hermes_consolidate_profiles.sh` | manual | ✅ passive | low |
| `zera-command.sh` | shell entry point | ✅ active | low |
| `zera-autonomous-launcher.sh` | manual | ⚠️ untested | medium |
| `zera-self-evolution.sh` | manual/cron | ⚠️ external governance | high |
| `zera-infinite-loops.sh` | manual | ⚠️ dangerous | high |
| `zera-evolve.sh` | manual | ⚠️ untested | medium |
| `zera-agent-intelligence.sh` | manual | ✅ passive | low |
| `zera-obsidian-integration.sh` | manual | ✅ passive | low |
| `test_mcp_profiles.py` | benchmark harness | ❌ misleading exit code | critical |
| `test_mcp_profiles.py.bak` | none | 🗑️ dead | low |
| `validate_global_configs.py` | quality checks | ✅ active | low |
| `drift_check.py` | quality checks | ✅ active | low |
| `kill_switch_check.py` | quality checks | ✅ active | low |
| `auto_update.py` | catalog pre-flight | ✅ active | low |
| `re_catalog.py` | runtime pre-flight | ✅ active | low |

### Dead References
- `.agent/workflows/multi-agent-routing.md` — referenced in AGENTS.md and workflow indexes but does not exist.
- `.agent/workflows/*` — entire directory effectively empty; all workflow references dangling.
- `configs/registry/workflows/path-fast.yaml` — referenced in `router.yaml` but directory `configs/registry/` does not exist.
- `configs/registry/workflows/path-quality.yaml` — same.
- `configs/registry/workflows/path-swarm.yaml` — same.
- `configs/registry/schemas/task.schema.yaml` — referenced in `router.yaml` handoff_safeguards but does not exist.
- `configs/capabilities/gsap_motion.yaml` — referenced in `router.yaml` motion_awareness but does not exist.
- `.agent/skills/gsap-animation.md`, `gsap-performance-guardrails.md`, etc. — referenced in motion routing but not published.

### Orphan Configs
- `configs/tooling/model_routing.json.DEPRECATED` — explicitly deprecated but still present.
- `configs/tooling/eggent_algorithm_matrix.json` — no consumer found in codebase.
- `configs/tooling/polyglot_execution_matrix.json` — no consumer found.
- `configs/tooling/notebooklm_agent_router_templates.json` — no consumer found.
- `configs/tooling/suite_manifest.json` — no consumer found.
- `configs/tooling/plugin_schema.json` — no consumer found.
- `configs/tooling/repo_aliases_policy.json` — no consumer found.
