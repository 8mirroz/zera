---
description: Standard multi-agent routing for complex execution.
---

# /multi-agent-routing

## Purpose

Coordinate complex tasks through role separation, file ownership, and integration review.

## Procedure

1. Classify the task and determine whether delegation is justified.
2. Split work into non-overlapping ownership scopes.
3. Keep immediate blocking work local and delegate only sidecar or isolated slices.
4. Integrate changes through review and validation.

## Output

- Agent roles.
- Ownership scopes.
- Integration checklist.

## Gate

No delegated worker may revert or overwrite another worker's changes.
