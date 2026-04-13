# 04 Source-of-Truth Convergence

## Objective
Eliminate declaration/runtime drift and make control surfaces explicit.

## Changes Applied

1. Provider convergence: enabled providers now map to registered runtime factories.
2. Workflow convergence check hardened: missing referenced workflow files are explicit errors.
3. External governance surfaces cataloged in remediation artifacts.

## Validation

- `python3 scripts/validation/check_provider_health.py` → pass (`parity_ok=true`)
- `python3 repos/packages/agent-os/scripts/workflow_model_alias_validator.py --json` → fail (`18` missing workflow files)

## Exit Criteria

- ✅ Unreachable enabled providers reduced to 0.
- ❌ Workflow catalog drift not resolved (18 missing refs remain).
- ⚠️ External governance documented, not fully absorbed.

## Rollback Notes

Revert:
- `repos/packages/agent-os/src/agent_os/runtime_registry.py`
- `repos/packages/agent-os/scripts/workflow_model_alias_validator.py`
- related artifacts in `artifacts/provider_parity.json`, `artifacts/workflow_integrity.json`
