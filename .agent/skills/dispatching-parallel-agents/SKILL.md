---
name: dispatching-parallel-agents
description: Use when you have multiple independent tasks (e.g. creating 5 separate component files) to speed up execution.
---

# Dispatching Parallel Agents

## Overview
Speed up execution by running independent tasks in parallel using sub-agents.

## When to Use
- **Independent Files**: Creating `Button.tsx`, `Card.tsx`, `Input.tsx` (no shared deps).
- **Migration**: Updating 10 files with the same pattern.
- **Testing**: Writing tests for 5 different modules.

## The Process

1. **Identify Independent Units**: Ensure Task A doesn't depend on Task B's output.
2. **Prepare Prompts**: effective prompt for each agent.
3. **Dispatch**: Call `browser_subagent` (or similar) multiple times with `waitForPreviousTools: false`.
4. **Collect**: Wait for all to finish.
5. **Verify**: Check that all files were created and consistent.

## Risks
- **Race Conditions**: If they edit the same file (e.g. `index.ts` exports), it will conflict.
- **Inconsistency**: One agent might use `interface`, another `type`. (Provide strict standards in prompt).
