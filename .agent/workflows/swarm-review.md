---
description: Final review gate for multi-file or C3+ changes.
---

# /swarm-review

## Purpose

Review implementation quality before completion, with emphasis on regressions, missing gates, and unsafe assumptions.

## Procedure

1. Inspect changed files and external mutations.
2. Check for scope creep, hidden fallbacks, skipped validation, and rollback gaps.
3. Re-run or verify the most relevant gates.
4. Report findings by severity with file references.

## Output

- Findings first.
- Validation summary.
- Residual risks and next remediation.

## Gate

Do not approve if a required validation gate is red without a documented containment plan.
