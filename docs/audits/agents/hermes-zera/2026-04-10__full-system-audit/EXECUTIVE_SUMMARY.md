# Hermes + Zera — Full System Audit Executive Summary

**Date:** 2026-04-10
**Auditor:** Principal AGI Systems Auditor (Qwen Code)
**Scope:** Hermes runtime engine, Zera persona overlay, Antigravity IDE control plane, all configs, scripts, memory, tooling, MCP, benchmarks, traces, governance
**Output Directory:** `docs/audits/agents/hermes-zera/2026-04-10__full-system-audit/`

---

## System at a Glance

| Dimension | Assessment | Score | Maturity |
|---|---|---|---|
| Architecture coherence | Core path reconstructable, but workflow/provider layers drift | 64/100 | L2 workable |
| Source-of-truth integrity | Multiple declarative surfaces overclaim control | 52/100 | L1 fragile |
| Runtime reliability | Default path no-op, fallback exists, success-washing present | 46/100 | L1 fragile |
| Persona integrity | Strong written contract, weak executable enforcement | 58/100 | L2 workable |
| Memory discipline | Layered policy mostly not realized in live writes | 44/100 | L1 fragile |
| Context engineering | L1 injection exists, broad discipline metrics weak | 57/100 | L2 workable |
| Tool/MCP quality | Useful config, misleading validation, parity drift | 49/100 | L1 fragile |
| Observability | Rich traces, stale schema, success-washing | 56/100 | L2 workable |
| Safety/governance | Good policy surface, partial enforcement, external sidecars | 63/100 | L2 workable |
| Performance efficiency | Some latency/cost controls, benchmark validity weak | 61/100 | L2 workable |
| Benchmark maturity | Gate and anomalies contradict each other | 28/100 | L0 chaotic |
| Remediation readiness | Issues localized and mostly reversible | 74/100 | L3 stable |

**Composite:** L2 workable — functional but not production-grade. Two L0-L1 blockers (benchmark validity, workflow/runtime declaration drift) prevent L3+.

---

## Critical Findings (Top 5)

### CR-1: Benchmark Suite Produces Contradictory Signals
The benchmark system reports `score=0.7756, pass_rate=0.875, gate=pass` while simultaneously listing all 13 expected case IDs as missing and 120 cases composed entirely of `::rN` repeats and `real-trace-*` sample traces. The analyzer inflates coverage by counting total cases but compares raw IDs for expected-case matching. **This renders the benchmark system useless for release gating.**

### CR-2: Runtime Success Signals Emitted Without Verification
`agent_runtime.py` emits `runtime_provider_selected` with `status=ok` the moment a provider is chosen — not when it completes successfully, not when output is verified. The fallback path returns `test_report.status: "not-run"` but the trace event still reads `status=ok`. Operators and downstream systems read false-positive health.

### CR-3: Declarative Config Surface Exceeds Executable Enforcement
`configs/tooling/` contains 85 files declaring policies, schemas, contracts, and governance rules. The Python runtime consumes a small fraction. `runtime_providers.json` declares `mlx_lm` as enabled, but `RuntimeRegistry` has no factory for it. `persona_eval.py` is not bound to `configs/personas/zera/eval_cases.json`. Zera skills declared in `configs/skills/ZERA_ACTIVE_SKILLS.md` are never published to `.agent/skills/`.

### CR-4: Zera Persona Governance Is Contract-Only, Not Runtime-Enforced
The persona constitution, identity, safety, tone, modes, and relationship boundaries are all well-written in `configs/personas/zera/`. The enforcement path is: (1) `ZeraCommandOS` resolves commands and injects metadata into prompts, (2) `PersonaModeRouter` does keyword-based mode selection. There is no runtime guardrail that prevents sycophancy, enforces truthfulness hierarchies, or blocks persona drift during long sessions. The constitution exists as a document, not as a runtime contract.

### CR-5: External Cron Sidecar Operates Outside Repo Governance
Home-side `jobs.json` cron and `~/.hermes/profiles/zera/cron/*.json` define active Zera behavior outside the repo's `background_jobs.yaml`. This creates a parallel governance plane that the repo cannot audit, block, or roll back.

---

## Benchmark Results (Re-validated)

| Metric | Reported | Audited | Verdict |
|---|---|---|---|
| Composite score | 0.7756 | not trustworthy | Case identity normalization broken |
| Pass rate | 87.5% | 50% (4 cases) | Inflated by repeat traces |
| Coverage | 9.23% | 0% canonical | All 13 expected cases missing |
| Local benchmark | — | 4 cases, 50% pass | More honest but too thin |
| Maturity | claimed pass | L0 chaotic | Contradiction between gate and anomalies |

---

## Remediation Roadmap

| Lane | Timeline | Key Actions | Risk Reduction |
|---|---|---|---|
| Quick Wins (0-1 days) | Immediate | Fix benchmark case normalization, fail MCP validator on mismatch, add provider registration contract test | -25% false confidence |
| Structural (1-2 weeks) | Short-term | Bind persona_eval to eval_cases, route memory writes through MemoryPolicyLayer, add cron parity doctor, consolidate trace sinks | -40% drift surface |
| Architectural (2-6 weeks) | Medium-term | Provider state machine, executable persona contracts, benchmark provenance, canonical trace schema | -60% failure modes |
| Advanced (6+ weeks) | Long-term | Reproducible audit harness, long-session eval corpus, provider lifecycle management | L3→L4 trajectory |

---

## Artifacts Produced

| File | Content |
|---|---|
| `01_SYSTEM_INVENTORY.md` | 259-node inventory, orphan/dead reference list, drift zones |
| `02_RUNTIME_GRAPH.md` | Full Hermes + Zera dependency graph, critical/fallback paths |
| `03_SOURCE_OF_TRUTH_ANALYSIS.md` | SOT map, drift matrix, ambiguity matrix, priority conflicts |
| `04_CONFIG_AND_CONTRACT_AUDIT.md` | 85-file config audit, contract mismatches, severity ranking |
| `05_HERMES_RUNTIME_AUDIT.md` | Planning, routing, tool selection, fallback, memory write audit |
| `06_ZERA_PERSONA_AUDIT.md` | Identity coherence, anti-sycophancy, tone, refusal, drift map |
| `07_MEMORY_AND_CONTEXT_AUDIT.md` | Memory lifecycle, contamination matrix, context budget |
| `08_TOOLING_AND_MCP_AUDIT.md` | 85-tool quality matrix, retirement/rewrite candidates |
| `09_OBSERVABILITY_AND_TRACING_AUDIT.md` | Trace schema, completeness, production telemetry checklist |
| `10_BENCHMARK_RESULTS.md` | Benchmark specification, results, anomalies |
| `11_RED_TEAM_REPORT.md` | Exploit catalog, mitigation matrix, regression additions |
| `12_SCORECARD.md` | 12-domain scoring, maturity levels |
| `13_ROOT_CAUSE_ANALYSIS.md` | 4 root causes with full attribution |
| `14_REMEDIATION_PLAN.md` | 4-lane remediation roadmap |
| `15_QUICK_WINS.md` | Immediate safe fixes |
| `16_SYSTEM_EVOLUTION_PLAN.md` | Governance cadence, admission policies, rollback discipline |
| `17_CHANGE_GOVERNANCE.md` | Audit cadence, regression requirements, change-review gates |
| `artifacts/system_node_index.json` | Machine-readable inventory |
| `artifacts/source_of_truth_map.json` | Machine-readable SOT map |
| `artifacts/runtime_dependency_graph.json` | Machine-readable runtime graph |
| `artifacts/benchmark_results.json` | Machine-readable benchmark results |
| `artifacts/anomalies.json` | Machine-readable anomaly catalog |
| `artifacts/risk_register.json` | Machine-readable risk register |
