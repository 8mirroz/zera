# 09 Tooling / MCP Rebuild

## Objective
Make tool/MCP surface reliable, bounded, and testable for planner/runtime use.

## Changes Applied

1. Contract tests executed and results captured in `artifacts/tool_contract_results.json`.
2. MCP validator now reports truthful non-zero failures.
3. Workflow model alias validator now surfaces missing workflows as hard errors.

## Validation

- `python3 scripts/test_mcp_profiles.py` → fail (9 missing servers, 1 routing mismatch)
- `python3 repos/packages/agent-os/scripts/workflow_model_alias_validator.py --json` → fail (18 missing workflow files)

## Exit Criteria

- ✅ Truthful contract detection is in place.
- ❌ Critical tool/MCP contract surface still failing.

## Rollback Notes

Revert validator hardening only if intentionally returning to non-blocking mode (not recommended).
