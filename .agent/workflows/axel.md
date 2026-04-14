---
description: Architecture-first execution flow for high-uncertainty changes.
---

# /axel

## Purpose

Force architecture clarity before automated execution on complex or high-blast-radius work.

## Procedure

1. Define the target behavior and non-goals.
2. Map affected systems, configs, and external surfaces.
3. Produce an implementation TaskSpec with gates and rollback.
4. Execute only after the TaskSpec is coherent and scoped.

## Output

- Architecture summary.
- TaskSpec.
- Rollback and validation plan.

## Gate

Do not execute if architecture ownership or rollback path is unclear.
