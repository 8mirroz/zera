---
description: Show system information and available workflows.
---

# /infa

## Purpose

Give the operator a compact map of available workflows, commands, and health checks.

## Procedure

1. Read active workflow set config.
2. List available workflow files and missing references.
3. Show the safest next command for the operator's goal.
4. Flag red gates instead of hiding them.

## Output

- Workflow inventory.
- Health status.
- Recommended next command.

## Gate

System information must distinguish configured, available, and missing capabilities.
