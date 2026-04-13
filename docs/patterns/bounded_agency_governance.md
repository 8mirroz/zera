# Pattern: Bounded Agency Governance

**Category:** governance
**Extracted from:** zera-governance-hardening-2026-04-08
**Date:** 2026-04-08
**Confidence:** High

---

## Problem

AI agents with self-evolution capabilities need governance boundaries that:
1. Prevent silent mutation of core safety rules
2. Allow bounded capability growth
3. Detect and respond to persona drift
4. Handle adversarial manipulation attempts
5. Maintain audit trails for all changes

---

## Solution: Layered Governance Control Surface

### Layer 1: Machine-Readable Governance Config
```json
{
  "control_plane": {
    "governance_surfaces": ["constitution", "safety", "relationship_boundaries", ...],
    "source_of_truth": ["configs/personas/zera/*.md", "configs/tooling/*.yaml"]
  },
  "candidate_classes": {
    "skill_refinement": { "loop": "capability", "auto_promote_allowed": true, ... },
    "governance_affecting_candidate": { "loop": "governance", "auto_promote_allowed": false, ... }
  },
  "freeze_conditions": ["governance_surface_touched_without_approval", ...],
  "promotion_rules": { "eval_required": true, "max_significant_personality_deltas_per_cycle": 1 }
}
```

### Layer 2: Eval-Based Validation
- Comprehensive eval cases covering: persona_stability, autonomy_governance, dual_loop_safety, adversarial, long_horizon_coherence
- Each case defines: prompt, must_include, must_not_include, failure_signals
- Eval coverage enforced by automated validator

### Layer 3: Drift Detection + Automated Response
```yaml
signals:
  - persona_boundary_drift
  - governance_mutation_attempt_increase
  - personality_delta_budget_breach

responses:
  persona_boundary_drift:
    - freeze_personality_promotions
    - require_operator_review_for_next_cycle
```

### Layer 4: Safe Intelligence Intake
- All indexed intelligence marked `observed_unpromoted`
- Promotion requires explicit classification + eval + review
- Default: `PROMOTE_MEMORY=false`
- Freeze-state check before any evolution action

### Layer 5: Automated Validation
- Validator checks: config completeness, eval coverage, script guardrails
- Tests enforce: candidate class consistency, category minimums, required snippets
- Event logging: all evolution actions recorded in JSONL with rollback paths

---

## Key Design Principles

1. **Default-deny** — nothing promoted without explicit classification + eval
2. **Freeze-first safety** — corrupted state → treat as frozen (safe default)
3. **Reversibility** — all changes have rollback paths
4. **Telemetry** — all actions logged with candidate_id, loop, risk_level, governance_impact
5. **Delta budget** — max 1 significant personality change per cycle
6. **Discussion-first** — intelligence indexed to discussion folder before promotion

---

## Applicability

This pattern applies to any AI agent system that:
- Has self-evolution or self-modification capabilities
- Needs governance boundaries that can't be silently mutated
- Requires audit trails for regulatory or safety compliance
- Operates with bounded autonomy under human oversight

---

## Anti-Patterns Avoided

| Anti-Pattern | How We Avoided It |
|-------------|-------------------|
| Silent persona drift | All changes require classification + eval |
| Governance mutation | Governance surfaces are read-only without review |
| Eval gaming | Adversarial evals test reward hacking specifically |
| Safety theater | Adversarial `overcautious_safety` case prevents initiative collapse |
| Micro-drift blindness | Cumulative drift tracking + delta budget |
| Memory hoarding | Curated memory writes, not indiscriminate storage |

---

## Related Files

- `configs/tooling/zera_growth_governance.json`
- `configs/personas/zera/eval_cases.json`
- `configs/tooling/drift-detection-rules.yaml`
- `scripts/zera-agent-intelligence.sh`
- `scripts/validation/check_zera_hardening.py`
- `repos/packages/agent-os/tests/test_zera_hardening_assets.py`
