---
description: Route multi-language work across bounded lanes.
---

# /polyglot-autoevo-routing

## Purpose

Split polyglot work by ownership boundaries without creating unmanaged parallel edits.

## Procedure

1. Identify language/runtime lanes and shared contracts.
2. Assign each lane a distinct file ownership scope.
3. Define integration order and cross-lane validation.
4. Keep generated improvements in no-promote mode until gates pass.

## Output

- Lane map.
- Contract surfaces.
- Integration and validation order.

## Gate

No lane may change another lane's owned files without coordination.
