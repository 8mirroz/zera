# 12. Scorecard

| Domain | Score | Maturity | Basis |
|---|---:|---|---|
| Architecture coherence | 64 | L2 workable | Core path reconstructable, but workflow and provider layers drift |
| Source-of-truth integrity | 52 | L1 fragile | Multiple declarative surfaces overclaim control |
| Runtime reliability | 46 | L1 fragile | Default path no-op, fallback exists, success-washing present |
| Persona integrity | 58 | L2 workable | Strong written contract, weak executable enforcement |
| Memory discipline | 44 | L1 fragile | Layered policy mostly not realized in live writes |
| Context engineering quality | 57 | L2 workable | L1 injection exists, but broad context discipline metrics are weak |
| Tool/MCP quality | 49 | L1 fragile | Useful config, misleading validation, parity drift |
| Observability | 56 | L2 workable | Rich traces, stale schema, success-washing |
| Safety/governance | 63 | L2 workable | Good policy surface, partial enforcement, external sidecars leak scope |
| Performance efficiency | 61 | L2 workable | Some latency/cost controls exist, but benchmark validity is weak |
| Benchmark maturity | 28 | L0 chaotic | Gate and anomalies contradict each other |
| Remediation readiness | 74 | L3 stable | Issues are localized and mostly reversible |

## Composite Read
- Overall maturity: **L2 workable**, with two L0-L1 blockers:
  - benchmark validity
  - workflow/runtime declaration drift

## Scoring Rationale — Detailed

### Architecture coherence: 64/100 (L2)
- Core execution path (zera-command.sh → ZeraCommandOS → AgentRuntime → RuntimeRegistry) is reconstructable and coherent.
- But: 10 root causes identified, 6 of which are medium-to-critical severity. The architecture has a clear spine but significant dead-code and declarative surfaces.

### Source-of-truth integrity: 52/100 (L1)
- `router.yaml` claims to be source of truth for routing, but declares capabilities (motion awareness, registry workflows) that don't exist.
- `configs/personas/zera/` claims to be the persona contract, but is never loaded at runtime.
- `runtime_providers.json` declares providers that aren't registered.
- Multiple files overclaim their control surface.

### Runtime reliability: 46/100 (L1)
- Default path (`agent_os_python`) is a functional no-op — it emits telemetry but doesn't execute or verify.
- Fallback chain exists but is untested in production traces.
- Success-washing present at 3 layers: provider selection, verification, and benchmark reporting.

### Persona integrity: 58/100 (L2)
- Written contracts are excellent — constitution, identity, tone, safety, boundaries are all coherent.
- Runtime enforcement is near-zero: all 8 constitutional rules are prose-only constraints.
- Mode collapsing (100% plan mode) means Zera's full persona is never exercised.
- Governor exists but is never called.

### Memory discipline: 44/100 (L1)
- `MemoryPolicyLayer` exists but is never called by the runtime.
- Memory classification is 93% flat `general`.
- Profile injection bleeds persona across sessions without scoping.
- Hybrid retrieval declared but only BM25 active in traces.

### Context engineering quality: 57/100 (L2)
- L1 profile injection works but is blunt.
- No context budget management.
- Goal stack updates are active (221 events) but lack quality metrics.
- Long-context retention and compaction are untested.

### Tool/MCP quality: 49/100 (L1)
- MCP validator returns success on failure — critical credibility issue.
- Tool surface is split across repo configs, operator profiles, and external cron.
- Hermes/Gemini parity is declared but not proven.

### Observability: 56/100 (L2)
- Rich trace volume (18,919 lines read by benchmark) but stale schema.
- Success-washing makes traces misleading.
- No tone, persona integrity, or memory quality events.
- Rerun comparability is broken by benchmark case identity issues.

### Safety/governance: 63/100 (L2)
- Good policy surface (autonomy policy, kill switches, approval gates declared).
- Partial enforcement — autonomy levels are metadata, not gates.
- External cron sidecars operate outside repo governance.

### Performance efficiency: 61/100 (L2)
- Latency and token tracking exist.
- But benchmark validity is weak, so cost-to-success ratios are not trustworthy.
- No p99 latency tracking, no token budget enforcement.

### Benchmark maturity: 28/100 (L0)
- Gate and anomalies contradict each other.
- Case identity normalization is broken.
- All canonical cases missing from results.
- 120 cases are repeats and samples, not distinct test scenarios.

### Remediation readiness: 74/100 (L3)
- Issues are well-localized to specific files and functions.
- Most fixes are reversible and low-risk.
- Clear remediation roadmap exists.
- But benchmark fix is a prerequisite for measuring improvement.
