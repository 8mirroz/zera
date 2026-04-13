---
type: knowledge-item
created: 2026-04-08
tags: [synced, healed]
---

# Retrospective — Zera Governance Hardening & Intelligence Intake

**Task ID:** zera-governance-hardening-2026-04-08
**Tier:** C4 (Complex)
**Date:** 2026-04-08
**Author:** Agent OS

---

## What was the goal?

Harden the Zera persona system against governance mutation, persona drift, and adversarial manipulation. Add a machine-readable governance control surface, comprehensive eval coverage, and a safe intelligence intake pipeline.

---

## What changed?

### 1. Governance Control Surface
- Created `configs/tooling/zera_growth_governance.json` — single source of truth for:
  - 13 candidate classes with loop/risk/eval definitions
  - 13 governance surfaces (read-only without review)
  - 9 freeze conditions
  - Promotion rules (eval + rollback + telemetry required)
  - Memory write guards

### 2. Eval Coverage Expansion
- Expanded `configs/personas/zera/eval_cases.json` from 4 → 26 cases
- Added 5 required categories: persona_stability (6), autonomy_governance (5), dual_loop_safety (5), adversarial (6), long_horizon_coherence (4)
- Each case now has `category`, `loop_class`, `failure_signals`
- Added `coverage_contract` block

### 3. Drift Detection
- Added 5 new signals to `configs/tooling/drift-detection-rules.yaml`:
  - `persona_boundary_drift` → freeze + operator review
  - `governance_mutation_attempt_increase` → freeze all + governance audit
  - `unclassified_candidate_rate_increase` → freeze auto-promotion
  - `personality_delta_budget_breach` → rollback + freeze
  - `memory_hoarding_increase` → tighten thresholds + prune

### 4. Intelligence Intake Rewrite
- Rewrote `scripts/zera-agent-intelligence.sh` (474 → 385 lines)
- Key changes:
  - `set -euo pipefail` (was `set -e`)
  - `--dry-run`, `--promote-memory`, `--project-limit` flags
  - Freeze-state check before execution
  - Event logging with JSONL
  - **No direct persona-memory promotion by default**
  - All indexed artifacts marked `observed_unpromoted`

### 5. Validation Infrastructure
- Created `scripts/validation/check_zera_hardening.py` — validates governance config, eval coverage, script guardrails
- Created `repos/packages/agent-os/tests/test_zera_hardening_assets.py` — unit tests for config consistency

---

## What went well?

1. **Defense-in-depth approach works** — multiple layers of governance (freeze conditions, eval cases, drift signals, validation scripts)
2. **Adversarial eval cases are high-quality** — cover prompt injection, attachment bait, memory hoarding, stealth mutation, eval gaming, safety theater
3. **Intelligence intake rewrite is principled** — `observed_unpromoted` status + `discussion_first` promotion gate prevents silent persona drift
4. **Tests catch config drift** — validator ensures candidate classes, governance surfaces, and freeze conditions stay in sync

---

## What went wrong?

1. **Critical bug in freeze-state check** — corrupted JSON would bypass freeze safety. Fixed by adding `try/except` around `json.loads` and treating parse errors as frozen (safe default).
2. **`proj_count` subshell bug** — counter incremented inside `find | while read` pipeline, always reports 0. Not a correctness issue but misleading for audits.
3. **`event_log` hardcodes telemetry** — all events get same `candidate_class`, `loop`, `risk_level` regardless of actual semantics. Weakens telemetry signal.
4. **New drift signals lack threshold definitions** — 5 new signals added but no numeric thresholds defined. Could fire too eagerly or not at all.
5. **Duplicate governance constraints** — `max_significant_personality_deltas_per_cycle` defined in both `eval_cases.json` and `zera_growth_governance.json`. Risk of drift.

---

## What should we do differently next time?

1. **Define thresholds alongside signals** — when adding new drift signals, always define numeric thresholds in the same PR.
2. **Single source of truth for governance constants** — extract `REQUIRED_CANDIDATE_CLASSES` and category minimums to a shared JSON schema, imported by both validator and tests.
3. **Strengthen validation beyond substring matching** — check that governance strings appear in non-commented context, or better, run scripts with `--dry-run` and assert on behavior.
4. **Parameterize `event_log`** — accept `candidate_class`, `risk_level`, `governance_impact` as arguments for accurate telemetry.
5. **Version bump on signal changes** — `drift-detection-rules.yaml` version was not updated despite adding 5 new signals.

---

## Metrics

| Metric | Value |
|--------|-------|
| Files changed | 12 |
| Lines added | ~350 |
| Lines removed | ~150 |
| Eval cases | 4 → 26 |
| Candidate classes | 12 → 13 |
| Drift signals | 5 → 10 |
| Freeze conditions | 6 → 9 |
| Review findings | 12 total (1 Critical, 8 Suggestion, 3 Nice to have) |
| Critical fixed | 1 (freeze-state corruption bypass) |
| Test pass rate | 100% (3/3) |
| Validation pass rate | 100% |

---

## Outstanding Issues (Suggestion level)

| # | Issue | Priority |
|---|-------|----------|
| 1 | `proj_count` subshell bug | Medium |
| 2 | `event_log` hardcoded telemetry | Medium |
| 3 | Drift signal thresholds missing | Medium |
| 4 | Duplicate governance constraints | Medium |
| 5 | Orphaned `self_analysis_update` block | Low |
| 6 | `JSONDecodeError` not caught in validator | Low |
| 7 | Brittle substring validation | Low |
| 8 | `find \| grep \| grep` subprocess waste | Low |
| 9 | Freeze-file hard dependency | Low |

---

## Conclusion

The hardening change significantly improves Zera's governance posture. The Critical freeze-state bug was caught during review and fixed. Remaining suggestions are medium/low priority and can be addressed in follow-up iterations. The system now has:

- Machine-readable governance controls
- 26 adversarial + stability eval cases
- 10 drift detection signals
- Safe intelligence intake (no silent persona promotion)
- Automated validation infrastructure

**Verdict: Ready for commit with Critical fix included.**
