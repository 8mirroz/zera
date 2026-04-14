---
description: Systematic debugging workflow for failures and regressions.
---

# /error-healing

## Purpose

Fix failures by reproducing, isolating, and validating the cause instead of guessing.

## Procedure

1. Capture the exact failing command, error, and environment.
2. Form the smallest test or reproduction.
3. Inspect the responsible code/config path.
4. Apply the smallest fix and rerun the failing gate.

## Output

- Reproduction evidence.
- Root cause.
- Fix and validation command.

## Gate

No fix is accepted without rerunning the failing command or explaining why it cannot be run.
