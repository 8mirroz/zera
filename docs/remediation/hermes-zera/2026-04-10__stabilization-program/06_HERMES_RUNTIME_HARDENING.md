# 06 Hermes Runtime Hardening

## Objective
Make runtime lifecycle explicit, bounded, and verifiable.

## Changes Applied

1. Provider selection/completion and recovery events are explicit in runtime path.
2. Provider health recording compatibility guard added in `AgentRuntime` to avoid legacy stub breakage.
3. Runtime regressions introduced by hardening were closed with test-aligned changes.

## Validation

- `python3 -m pytest -q repos/packages/agent-os/tests/test_agent_runtime_dispatch.py repos/packages/agent-os/tests/test_swarmctl_run_integration.py` → 13 passed

## Exit Criteria

- ✅ Runtime lifecycle instrumentation improved and regression tests green.
- ⚠️ Degradation/fallback behavior still needs broader production-path verification.

## Rollback Notes

Revert:
- `repos/packages/agent-os/src/agent_os/agent_runtime.py`
- `repos/packages/agent-os/tests/test_swarmctl_run_integration.py`
