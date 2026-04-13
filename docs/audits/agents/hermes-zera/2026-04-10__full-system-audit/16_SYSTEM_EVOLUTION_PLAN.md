# 16. System Evolution Plan

## Cadence
- Full system audit: monthly or after any C4-C5 control-plane change.
- Benchmark rerun: after routing/provider/benchmark analyzer changes.
- Persona regression run: after any persona, eval, mode-router, or memory-policy change.
- Adapter parity check: after Hermes/Gemini profile sync changes.

## Regression Requirements
- No change to runtime provider config without provider-registration test.
- No change to benchmark analyzer without case-identity regression tests.
- No change to persona or memory governance without eval-harness update.
- No workflow catalog change without existence validation for assets.

## Storage Policy
- All future full-system audits live under `docs/audits/agents/hermes-zera/<date>__full-system-audit/`.
- Historical benchmark artifacts remain evidence-only unless regenerated under a validated analyzer.
- Home-profile drift snapshots should be captured into audit artifacts, not scattered repo docs.

## Rollback Discipline
- Every config change must declare a rollback path in the PR/commit.
- Persona changes require `evaluate_governor()` call evidence before merge.
- Provider changes require a registration test and a fallback path test.
- Benchmark changes require a rerun showing score delta is real, not normalization artifact.

## Persona Update Governance
- All changes to `configs/personas/zera/*.md` must be reviewed for executable impact.
- If a persona doc change has no corresponding code/consumer change, it must be labeled "narrative only" in the PR.
- Self-evolution loop changes require persona regression run evidence before merge.
- Emotional closeness axis changes require `evaluate_governor()` call evidence.

## Memory Policy Governance
- All memory writes must route through `MemoryPolicyLayer` (once implemented).
- Memory schema changes require a migration plan for existing `.agent/memory/memory.jsonl` entries.
- Profile injection changes require context budget impact assessment.

## Tool/MCP Admission Policy
- New tools must declare: purpose, trigger condition, failure behavior, timeout, rollback path.
- MCP servers must pass `test_mcp_profiles.py` with non-zero exit on failure.
- Tool descriptions must be tested for planner parseability.

## Trace Schema Governance
- All emitted event types must be in `trace_schema.json`.
- New event types require schema update before merge.
- Schema drift checks run as part of quality gates.

## Artifact Naming/Storage Policy
- Audits: `docs/audits/agents/hermes-zera/<YYYY-MM-DD>__full-system-audit/`
- Benchmarks: `docs/ki/benchmark_<YYYYMMDD_HHMMSS>.md` + `docs/ki/benchmark_<YYYYMMDD_HHMMSS>.json`
- No audit artifacts outside canonical audit directory.
- No benchmark artifacts in `logs/` directory.

## Deepened: Source-of-Truth Maintenance
- `router.yaml` is source of truth for routing — but must be validated against executable consumers quarterly.
- `configs/personas/zera/` is source of truth for persona — but must be loaded at runtime or relabeled "reference."
- `runtime_providers.json` is source of truth for providers — but must have factory registration for every enabled entry.
- A quarterly "declarative surface audit" should identify and clean up configs without consumers.

## Deepened: Benchmark Provenance
- Every benchmark result must tag each case as: `canonical`, `repeat`, `sample`, or `real-trace`.
- Only `canonical` cases count toward coverage and gate decisions.
- `repeat` cases are for stability measurement only.
- `sample` and `real-trace` cases are excluded from gate arithmetic.

## Deepened: Long-Session Eval Corpus
- Build a corpus of 50+ persona evaluation scenarios covering: flattery, emotional pressure, contradiction traps, refusal, multi-mode switching, long-context retention.
- Run quarterly as a regression suite.
- Store results in `docs/audits/agents/hermes-zera/<date>/persona-eval/`.
