# 07 Zera Enforcement Upgrade

## Objective
Move Zera from declarative persona quality toward runtime-enforced behavior.

## Current State

- Mode/eval scaffolding exists (`artifacts/persona_eval_diff.json`), but runtime enforcement remains partial.
- No complete measured evidence yet that all required behavioral constraints are enforced at runtime.

## Validation

- Artifactual evidence: `artifacts/persona_eval_diff.json`
- Runtime-enforcement completeness: not proven in this stabilization cycle.

## Exit Criteria

- ⚠️ Partial: evaluation coverage improved.
- ❌ Not complete: runtime boundary/truth enforcement is not fully measurable yet.

## Rollback Notes

Revert related persona-router/eval changes if needed; keep audit trail in `artifacts/fix_manifest.json`.
