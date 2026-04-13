# 02 Baseline Snapshot

## Objective
Capture pre-remediation baseline so all later changes are diffable.

## Baseline State (Audit-Aligned)

- Benchmark gate behavior was untrustworthy.
- MCP profile validator could false-green.
- Provider declaration/runtime drift existed.
- Workflow catalog references were not proven as executable.
- Success semantics were optimistic in critical paths.
- Trace schema drift existed.
- Zera and memory layers were stronger in docs than in runtime enforcement.

## Evidence

- `artifacts/baseline_metrics.json`
- `docs/audits/agents/hermes-zera/2026-04-10__full-system-audit/`

## Exit Criteria

- ✅ Baseline artifacts created.
- ✅ Later changes are diffable against baseline artifacts and current validations.

## Rollback

- N/A for baseline capture (read-only historical snapshot).
