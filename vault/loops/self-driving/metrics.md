---
type: knowledge
created: 2026-04-09
tags: [synced, healed]
---

# Self-Driving Loop — Metrics (2026-04-09)

## 4 Core Metrics

| Metric | Baseline | Current | Target | Trend |
|--------|----------|---------|--------|-------|
| evolution_completion_rate | 0/1 cycles | 3/3 cycles | >80% | ↑ |
| governance_coverage | 0/15 classes | 15/15 weighted | 100% | ↑ |
| fallback_depth | 2 levels | 10 levels | >5 | ↑ |
| signal_population | 0 signals | 3/4 sources | >3 | ↑ |

## A/B Test Candidates
- Fallback model ordering: capability-first vs token-cost-first
- Evolution execution: in-process vs sub-agent (in-process wins)
- Pre-search compliance: system prompt vs behavioral pattern (behavioral wins)

## Winner This Cycle
- In-process evolution: ACCEPTED (no timeout, full traceability)
- Capability-first fallback: ACCEPTED (better models available)
- Behavioral pre-search: ACCEPTED (100% compliance by design)

## Cycle 2 Update (2026-04-09)

| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| evolution_completion_rate | 3/3 | 5/5 | +2 |
| governance_coverage | 15/15 | 15/15 | stable |
| fallback_depth | 10 | 10 | stable |
| signal_population | 3/4 | 4/4 | +1 (decisions logged) |

## A/B Test Results
- In-process evolution: WINNER (no timeout)
- Capability-first fallback: WINNER (better models)
- Behavioral pre-search: WINNER (100% compliance)
- Governance snapshot: NEW (audit trail improved)
