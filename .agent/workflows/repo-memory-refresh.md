---
description: Refresh repository memory before planning or execution.
---

# /repo-memory-refresh

## Purpose

Load the current repository facts before taking action, so routing and implementation decisions are based on live files rather than stale assumptions.

## Procedure

1. Inspect the current task, working directory, and relevant AGENTS/RULES files.
2. Read only the nearest relevant docs, configs, manifests, and skills.
3. Capture discovered constraints, active risks, and source-of-truth locations.
4. Prefer repo-owned facts over external memory when they conflict.

## Output

- Short context summary.
- Relevant file list.
- Open risks that must affect planning.

## Gate

Do not proceed to implementation if source-of-truth ownership is unclear.
