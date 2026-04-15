---
name: writing-plans
description: Use when you need to create a plan for implementation, after design is mostly settled
---

# Writing Implementation Plans

## Overview

Create a detailed, step-by-step plan for implementing a design or feature. The plan should be broken down into small, verifiable chunks.

## The Output

**File Location:** `docs/plans/YYYY-MM-DD-<topic>-implementation.md`

**Format:**
```markdown
# Implementation Plan - [Topic]

[Brief description of goal]

## User Review Required
[Any breaking changes or critical decisions needing sign-off]

## Proposed Changes

### [Component/Area 1]

#### [Action] [Filename]
- [ ] Detailed step 1
- [ ] Detailed step 2
- [ ] Verification step

### [Component/Area 2]
...

## Verification Plan
### Automated Tests
- Command to run tests

### Manual Verification
- Step-by-step manual test guide
```

## Key Principles
1. **Bite-sized steps**: Each tickbox should change at most 1-3 files.
2. **explicit verification**: Every major step needs a way to verify it works.
3. **No ambiguous tasks**: "Refactor X" is bad. "Extract function Y to file Z" is good.
4. **Group by Component**: Logical grouping helps reviewers.

## After the Plan
1. **Review**: specifically ask the user to review the plan.
2. **Refine**: Update based on feedback.
3. **Execute**: Use `superpowers:executing-plans` to implement.
