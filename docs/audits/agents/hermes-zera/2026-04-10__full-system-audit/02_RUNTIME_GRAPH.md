# 02. Runtime Graph

## Реальный путь исполнения
1. User/CLI вызывает `scripts/zera-command.sh`.
2. Shell bridge делает `uv run python ../../../scripts/zera_command_runtime.py`.
3. `scripts/zera_command_runtime.py` использует `agent_os.zera_command_os.ZeraCommandOS`.
4. `ZeraCommandOS` читает `configs/tooling/zera_command_registry.yaml`, `zera_client_profiles.yaml`, `zera_branching_policy.yaml`, `zera_research_registry.yaml`, `zera_skill_foundry.yaml`, `zera_external_imports.yaml`, `zera_growth_governance.json`, `zera_mode_router.json`.
5. Для runtime dispatch `agent_os.agent_runtime.AgentRuntime`:
   - инжектит `configs/orchestrator/user_profile.json` в `objective`;
   - при `zera:*` повторно прогоняет `ZeraCommandOS.resolve_command`;
   - выбирает provider через `agent_os.runtime_registry.RuntimeRegistry`.
6. `RuntimeRegistry` читает `configs/tooling/runtime_providers.json`, `configs/tooling/zeroclaw_profiles.json`, `configs/tooling/source_trust_policy.yaml`.
7. Дальше один из reachable providers:
   - `agent_os_python`: пишет telemetry и завершает run без реального исполнения/verification;
   - `zeroclaw`: может эмитить autonomy/background/memory events;
   - `claw_code`: доступен только при enable path.
8. Все ключевые runtime events уходят в `logs/agent_traces.jsonl` через `agent_os.observability.emit_event`.
9. Benchmark layer читает trace log через `configs/tooling/analyze_benchmark.py` и пишет derived outputs в `docs/ki/benchmark_*`.

## Critical Paths
- `repo_native -> zera-command.sh -> zera_command_runtime.py -> ZeraCommandOS`: рабочий и подтвержден `catalog`/`resolve`.
- `AgentRuntime -> RuntimeRegistry -> agent_os_python`: default path, но functional no-op.
- `T7 override -> zeroclaw`: reachable only when provider enabled/profile present; trace evidence exists.

## Hidden Coupling
- L1 memory injection из `configs/orchestrator/user_profile.json` меняет objective до route/provider selection.
- Benchmark validity зависит не от suite semantics, а от parser behavior в `analyze_benchmark.py`.
- Workflow control plane зависит от `.agent/config/workflow_sets.active.json`, но сами workflow assets отсутствуют.
- Operator-side Hermes/Gemini config уже содержит repo-semantics contract и влияет на live behavior вне git tree.

## Fallback Paths
- Command-level fallback: в `zera_command_registry.yaml` большинство команд деградирует в `zera:plan` или `zera:critic`.
- Runtime-level fallback: `RuntimeRegistry.resolve()` строит fallback chain из config, но provider может быть задекларирован и не зарегистрирован кодом.
- Source-tier fallback: capability promotion может быть заблокирован `source_trust_policy.yaml`, forcing default provider/profile reset.

## Hidden Behavior / Shadow Rules
- `agent_os_python` пишет `verification_result` со `status=ok`, хотя `verification_status=not-run`.
- Persona mode selection остаётся keyword-based (`persona_mode_router.py`), а не evidence-based.
- Background jobs и autonomy decisions observable главным образом через `zeroclaw`; default provider этого слоя не реализует.

## Unconsumed or Weakly Consumed Fields
- `prompt_assembly.yaml` описывает persona assembly, но прямой runtime-consumer в найденном пути не выявлен.
- Большая часть `persona_eval_suite.json` не исполняется как formal harness; `persona_eval.py` использует heuristic token checks.
- `runtime_providers.json` поле `mlx_lm` не потребляется `RuntimeRegistry`.

## Deepened Findings (Phase 2+)

### Runtime Lifecycle States — Not Modeled
`agent_runtime.py` conflates three distinct states:
1. **selected** — provider chosen (emits `runtime_provider_selected` with `status=ok`)
2. **executed** — `provider.run()` returned (may or may not be valid)
3. **verified** — output checked against quality gates (never happens in code)

Only state 1 is emitted. States 2 and 3 are assumed. This is the root cause of success-washing.

### Provider Lifecycle — No State Machine
`RuntimeRegistry.get_provider()` does lazy instantiation with no lifecycle management:
```
config exists → is_enabled check → factory lookup → instantiate → cache
```
Missing states: `initializing`, `healthy`, `degraded`, `unhealthy`, `recovering`, `draining`.

### Autonomy Boundaries — Soft Only
`autonomy_policy.yaml` defines autonomy levels but `agent_runtime.py` never checks them before calling `provider.run()`. The autonomy level is read from config, placed in `route_decision`, and emitted as telemetry — but never enforced as a gate.

### Keyword-Only Mode Routing — Fragile
`PersonaModeRouter.select_mode()` uses substring matching against a flat keyword list per rule. No semantic understanding, no context awareness, no confidence threshold. A single keyword match determines Zera's entire response mode. Scoring is additive (count of matching keywords), which means a rule with 20 keywords can win over a more specific rule with 3 keywords even if the intent is wrong.

### Memory Write Path — Uncontrolled
`agent_runtime.py` injects `ProfileManager` context into the objective string before routing. There is no `MemoryPolicyLayer` gate, no schema validation against `memory_schema.json`, no staleness check. The `MemoryPolicyLayer` class exists in `memory_policy_layer.py` but is never imported or called by `agent_runtime.py`.

### Motion-Aware Routing — Dead Config Surface
`router.yaml` contains a full `motion_awareness` block with GSAP/Framer/CSS triggers, skill assignments, and quality gates. However:
- `configs/capabilities/gsap_motion.yaml` does not exist
- Referenced skills are not published to `.agent/skills/`
- No Python code in `agent_os/` consumes `motion_awareness` from the router config
- This is a declarative surface with zero executable backing

### Registry Workflow Resolution — Silent No-Op
`RegistryWorkflowResolver` is called in `_registry_workflow_context_for_route()` but the entire `configs/registry/` directory does not exist. The method catches `Exception` and returns `None`, so this failure is invisible in telemetry.

### Pre-flight Catalog Update — Unobservable
`AgentRuntime.run()` executes `re_catalog.py` via `subprocess.run()` with `capture_output=True`. Any failure is silently swallowed by `except Exception: pass`. No telemetry event is emitted for this step.

### Profile Context Injection — Blind Concatenation
`ProfileManager.get_summary_context()` output is prepended to the user's objective string with no separator, no schema, no validation. This can change routing decisions, mode selection, and tool eligibility in ways the user cannot see or debug.
