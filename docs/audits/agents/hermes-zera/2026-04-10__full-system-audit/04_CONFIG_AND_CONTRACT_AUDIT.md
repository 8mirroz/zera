# 04. Config and Contract Audit

## Highest-Severity Mismatches
1. **`runtime_providers.json` declares `mlx_lm` as enabled, but `RuntimeRegistry` has no factory for it.**
   - Symptom: provider can be “selected” in config space but is unreachable in code.
   - Evidence: `configs/tooling/runtime_providers.json`, `repos/packages/agent-os/src/agent_os/runtime_registry.py`.
2. **`zera_command_registry.yaml.telemetry_schema.required_fields` is non-binding.**
   - Symptom: emitted `zera_command_resolved` events miss fields that config declares required.
   - Evidence: `configs/tooling/zera_command_registry.yaml`, `scripts/zera_command_runtime.py`, `logs/agent_traces.jsonl`.
3. **`mcp_profiles.json` validation contract is false-positive.**
   - Symptom: `scripts/test_mcp_profiles.py` exits `0` and prints “All tests passed (7/8)” despite routing mismatch.
   - Evidence: `scripts/test_mcp_profiles.py`, observed stdout.
4. **Workflow set contract points to absent assets.**
   - Symptom: `.agent/config/workflow_sets.active.json` and `workflow_sets_catalog.json` reference missing `.agent/workflows/*.md`.
   - Evidence: `.agent/workflows` is empty.

## Contradictory Defaults
- `runtime_providers.json` says `mlx_lm.enabled=true`; code effectively says “unavailable.”
- `zera_client_profiles.yaml` says Gemini is a normal client; `scripts/zera_command_runtime.py` says Gemini execution is render-only.
- `background_jobs.yaml` governs repo-side jobs, but `~/.hermes/profiles/zera/cron/jobs.json` adds an extra self-evolution sidecar outside repo policy.
- `benchmark_gate` passes while benchmark anomalies report full missing canonical case set.

## Unconsumed Keys
- `runtime_providers.json.providers.*.supported_task_types`
- `runtime_providers.json.providers.*.supported_channels`
- `zeroclaw_profiles.json.profiles.*.channel`
- `zeroclaw_profiles.json.profiles.*.memory_policy`
- `zeroclaw_profiles.json.profiles.*.workspace_scope`
- `zeroclaw_profiles.json.profiles.*.tool_allowlist`
- `zera_client_profiles.yaml.repo_semantics`
- `zera_client_profiles.yaml.secret_policy`
- `zera_client_profiles.yaml.parity_requirements`
- Large parts of `prompt_assembly.yaml`

## Path and Platform Brittleness
- Hermes profile `terminal.cwd` is `.` instead of an absolute repo path.
- `scripts/hermes-sync-config.sh` hardcodes `/Users/user/antigravity-core`.
- `scripts/test_mcp_profiles.py` hardcodes absolute repo paths and uses a local notion of “known servers.”
- Home-profile cron jobs create active behavior outside repo-tracked configs.

## Safe-Fix Candidates
- Add config-vs-code provider registration test for every enabled provider.
- Make MCP profile validator fail non-zero on any routing mismatch.
- Add workflow existence validator for `.agent/workflows/*`.
- Validate command telemetry against registry-required fields at emission time.
- Add home-profile parity doctor for Hermes/Gemini/Zera cron.

## Deepened Findings (Phase 3+)

### Unconsumed Config Keys — 85 Files, Many Dead
The following config keys/fields are declared but never consumed by any Python component:
- `runtime_providers.json`: `mlx_lm` provider declaration (no factory)
- `router.yaml`: `motion_awareness` entire block (no consumer)
- `router.yaml`: `memory.unified_fabric` (no memory_bridge module)
- `router.yaml`: `handoff_safeguards.contract_schema` (file doesn't exist)
- `zera_command_registry.yaml`: `telemetry_schema.required_fields` (non-binding)
- `persona_eval_suite.json`: most test case definitions (not executed as formal harness)
- `prompt_assembly.yaml`: entire file (no runtime consumer)
- `memory_schema.json`: entire file (not loaded at runtime)
- `workflow_sets_catalog.json`: references to non-existent `.agent/workflows/*.md`
- `zera_mode_router.json`: all mode definitions beyond keyword lists (no semantic routing)

### Dead Aliases
- `configs/tooling/model_routing.json.DEPRECATED` — explicitly deprecated but still present in config path
- `.agent/config/workflow_sets.active.json` — references non-existent workflows
- `scripts/test_mcp_profiles.py.bak` — backup copy in active path

### Schema Inconsistency
- `trace_schema.json` does not include 10+ event types that are actively emitted
- `zera_command_registry.yaml` declares `telemetry_schema` but `emit_event()` doesn't validate against it
- `benchmark_suite.json` declares expected case IDs but analyzer compares raw IDs with `::rN` suffixes

### Invalid Inheritance Semantics
- `routing.yaml` declares `derived: true, source_of_truth: router.yaml` but contains `task_type_map` and `escalation_triggers` not present in `router.yaml`
- `router.yaml` references `configs/registry/` paths that don't exist
- `zera_client_profiles.yaml` declares capability levels (`limited`, `full`, `low`, `medium`, `high`) that are mapped inconsistently in `ZeraCommandOS._capability_sufficient()`

### Path Brittleness
- All config paths are relative to `repo_root` with no fallback for missing files
- `RuntimeRegistry._load_json()` silently falls back to defaults on any parse error — masking config corruption
- `PersonaModeRouter._load_config()` returns empty rules on any error — silent degradation

### Silent Fallback Behavior
- `RuntimeRegistry.resolve()`: if no provider enabled, falls back to default chain, then to `agent_os_python` — all silently
- `PersonaModeRouter.select_mode()`: if no keywords match, returns default mode — silently
- `RegistryWorkflowResolver.resolve()`: catches all exceptions, returns `None` — silently
- `AgentRuntime.run()`: pre-flight catalog update swallows all exceptions — silently

### Config Complexity — 85 Tooling Files
`configs/tooling/` contains 85 files. Analysis:
- ~30 files have active Python consumers
- ~15 files are referenced but not actively validated
- ~7 files are explicitly orphan (no consumer, no reference)
- ~1 file is explicitly deprecated
- ~32 files are narrative/declarative (design docs, templates, schemas without validators)

The config-to-code ratio is approximately 3:1 declarative-to-consumer, which is unsustainable.
