---
description: Plan coordinated multi-agent or multi-lane execution.
---

# /swarm-plan

## Purpose

Turn complex work into independent, reviewable slices with clear ownership and integration gates.

## Procedure

1. Decompose the task by file ownership and dependency order.
2. Identify blocking work versus parallel sidecar work.
3. Assign validation per slice and one final integration gate.
4. Keep a single authoritative status list.

## Output

- Work breakdown.
- Ownership map.
- Integration order.
- Validation matrix.

## Gate

Do not parallelize tasks that write to the same files without an explicit merge plan.
