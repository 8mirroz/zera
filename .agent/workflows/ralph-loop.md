---
description: Bounded evolutionary optimization loop.
---

# /ralph-loop

## Purpose

Run best-of-N improvement only when there is a measurable objective and a hard stop condition.

## Procedure

1. Define metric, baseline, and candidate budget.
2. Generate candidates in isolation.
3. Score candidates with deterministic tests before model judgment.
4. Promote only when improvement beats baseline and rollback exists.

## Output

- Baseline.
- Candidate results.
- Promotion or rejection decision.

## Gate

No infinite loop, no unbounded mutation, and no promotion without measurable improvement.
