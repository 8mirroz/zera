# 05 Observability Hardening

## Objective
Make telemetry diagnosable and aligned with real execution states.

## Changes Applied

1. Canonical and mirror trace schemas synchronized.
2. Mirror parity is now tested (`test_trace_schema_mirror.py`).
3. Duplicate `runtime_workflow_missing` schema key removed from both schema files.

## Validation

- `python3 -m pytest -q repos/packages/agent-os/tests/test_trace_schema_mirror.py repos/packages/agent-os/tests/test_trace_validator.py` → pass
- `python3 repos/packages/agent-os/scripts/verify_trace_coverage.py` → fail (required field gaps in emitted events)

## Exit Criteria

- ✅ Schema parity for static contracts is enforced.
- ❌ Runtime field-level trace compliance not yet achieved.

## Rollback Notes

Revert:
- `configs/tooling/trace_schema.json`
- `configs/tooling/agent_os_trace_schema.json`
- `repos/packages/agent-os/tests/test_trace_schema_mirror.py`
