# 03 Truth Restoration

## Objective
Remove false-green behavior and restore trustworthy validation semantics.

## Changes Applied

1. Benchmark identity and provenance handling hardened in `configs/tooling/analyze_benchmark.py`.
2. Strict gate now blocks on quality/provenance problems, not only on headline score.
3. `scripts/internal/test_mcp_profiles.py` now fails fast (non-zero) on real contract defects.
4. Runtime lifecycle semantics moved away from optimistic success markers.

## Validation

- `python3 configs/tooling/analyze_benchmark.py --strict` → exit 2 (expected while quality defects remain)
- `python3 scripts/test_mcp_profiles.py` → exit 1 (expected while MCP defects remain)

## Exit Criteria

- ✅ False-green behavior eliminated.
- ✅ Failures are now visible and block correctly.
- ⚠️ Quality gates still failing; truth restored, performance/readiness not yet restored.

## Rollback Notes

Revert:
- `configs/tooling/analyze_benchmark.py`
- `scripts/internal/test_mcp_profiles.py`
- `scripts/test_mcp_profiles.py`
