# 10. Benchmark Results

## Evidence Base
- Historical benchmark verdict: `docs/ki/benchmark_latest.json`
- Alternate local benchmark summary: `logs/benchmark-latest.json`
- Analyzer logic: `configs/tooling/analyze_benchmark.py`
- Suite definition: `configs/tooling/benchmark_suite.json`

## Result Summary
- Historical latest reports `score=0.7756`, `pass_rate=0.875`, `coverage=9.23`, `gate=pass`.
- Same historical report also says all 13 expected case IDs are missing and only suffixed/real-trace case IDs exist.
- Local log summary reports only `4` cases with `pass_rate=0.5`.
- The current validator surface is also compromised: `scripts/test_mcp_profiles.py` returns success with `7/8` routing checks.

## Audit Verdict
- **Benchmark suite is not valid for decision-making in its current form.**
- Gate status is not trustworthy because case identity normalization is broken.
- Coverage, pass rate, and trendline are inflated by repeated `::rN` variants and `real-trace-*` sample cases.

## Required Metrics: Credible vs Not Credible
| Metric family | Credible now? | Reason |
|---|---|---|
| Reliability headline metrics | partially | some counts exist, but validity is compromised |
| Persona metrics | weak | persona eval is heuristic and mode coverage is poor |
| Memory/context metrics | mostly no | instrumentation too thin |
| Tool/MCP metrics | partially | validator exists but is misleading |
| Observability metrics | partially | enough to prove drift, not enough for clean SLOs |
| Performance metrics | partially | latency exists, but linked success semantics are muddy |

## Baseline Score Summary
- Reported benchmark score: not trusted.
- Audit baseline: benchmark maturity is below production threshold and should not gate release decisions until normalized.
