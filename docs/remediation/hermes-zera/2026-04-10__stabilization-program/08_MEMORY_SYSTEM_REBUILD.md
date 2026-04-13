# 08 Memory System Rebuild

## Objective
Materialize layered memory as runtime behavior rather than declaration.

## Current State

- Memory layering remains mostly declarative (`artifacts/memory_layer_metrics.json`).
- Runtime evidence for full class promotion/retrieval discipline is insufficient.

## Validation

- `artifacts/memory_layer_metrics.json` indicates unresolved layering and retrieval-discipline gaps.

## Exit Criteria

- ❌ Not complete.

## Rollback Notes

No dedicated memory-rebuild implementation landed in this cycle; rollback N/A.
