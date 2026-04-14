---
description: Validate that configs, runtime state, docs, and validators still agree.
---

# /drift-validator

## Purpose

Detect drift between source-of-truth config, runtime profile files, generated state, docs, and validation tooling.

## Procedure

1. List the configured source-of-truth artifacts for the task domain.
2. Compare runtime copies against repo-owned semantics.
3. Run the narrow validators that cover the changed surfaces.
4. Report drift as actionable findings, not broad cleanup requests.

## Output

- Drift summary.
- Exact files or external surfaces involved.
- Validation commands and results.

## Gate

Do not enable automation that mutates state while drift is unresolved.
