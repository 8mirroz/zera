---
description: Select the best local implementation blueprint for the task.
---

# /task-blueprint-selection

## Purpose

Reuse proven local patterns instead of inventing new architecture for each task.

## Procedure

1. Search nearby code, docs, ADRs, and patterns for matching implementations.
2. Prefer the smallest existing pattern that satisfies the requirements.
3. Note why rejected alternatives are weaker for this codebase.
4. Produce a scoped implementation blueprint.

## Output

- Chosen pattern or explicit no-match finding.
- Files likely to change.
- Validation strategy.

## Gate

Do not introduce a new abstraction when an established local pattern is sufficient.
