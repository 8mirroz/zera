---
description: Classify incoming tasks by type, complexity, risk, and required gates.
---

# /triage

## Purpose

Route work before execution so trivial tasks stay lightweight and high-risk tasks receive planning, review, and validation.

## Procedure

1. Identify task type, complexity tier, mutable surfaces, and user intent.
2. Detect whether external systems, credentials, cron, deployment, or production data are involved.
3. Select the minimum workflow set and skills required.
4. State assumptions and blockers before editing files.

## Output

- Task type and complexity.
- Selected workflow path.
- Required validation gates.

## Gate

If the task can mutate production-like state, require rollback evidence before promotion.
