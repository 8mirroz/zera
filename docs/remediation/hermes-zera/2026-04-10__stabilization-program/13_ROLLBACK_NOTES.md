# 13 Rollback Notes

## Scope
Rollback instructions for fixes currently represented in `artifacts/fix_manifest.json`.

## Per-Fix Rollback

1. `FIX-001` (`configs/tooling/analyze_benchmark.py`)  
   Rollback: revert file to previous revision.
2. `FIX-002` (`scripts/internal/test_mcp_profiles.py`, `scripts/test_mcp_profiles.py`)  
   Rollback: revert fail-fast/root-fix changes and wrapper entrypoint.
3. `FIX-003` (`repos/packages/agent-os/src/agent_os/runtime_registry.py`)  
   Rollback: revert parity APIs and availability-aware resolve.
4. `FIX-004` (`repos/packages/agent-os/scripts/workflow_model_alias_validator.py`)  
   Rollback: remove hard-fail reporting for missing workflow files.
5. `FIX-005` (`configs/tooling/agent_os_trace_schema.json`, trace parity test)  
   Rollback: restore prior mirror schema and remove parity test.
6. `FIX-006` (`repos/packages/agent-os/src/agent_os/agent_runtime.py`)  
   Rollback: remove `_record_provider_health_safe` compatibility path.
7. `FIX-007` (`configs/tooling/trace_schema.json`, `configs/tooling/agent_os_trace_schema.json`)  
   Rollback: restore duplicate-key schema content (not recommended).

## Bulk Rollback (Targeted)

```bash
git checkout HEAD -- \
  configs/tooling/analyze_benchmark.py \
  scripts/internal/test_mcp_profiles.py \
  scripts/test_mcp_profiles.py \
  repos/packages/agent-os/src/agent_os/runtime_registry.py \
  repos/packages/agent-os/scripts/workflow_model_alias_validator.py \
  repos/packages/agent-os/src/agent_os/agent_runtime.py \
  repos/packages/agent-os/tests/test_swarmctl_run_integration.py \
  configs/tooling/trace_schema.json \
  configs/tooling/agent_os_trace_schema.json \
  repos/packages/agent-os/tests/test_trace_schema_mirror.py
```

## Rollback Risk

Rolling back truth-layer fixes can reintroduce false-green behavior and hide critical failures.
