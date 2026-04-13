---
name: triage-issue
description: Investigate a bug by exploring the codebase, identify root cause, and file a GitHub issue with a TDD-based fix plan. Use when user reports a bug, wants to file an issue, mentions "triage", or wants to investigate and plan a fix.
source: https://github.com/mattpocock/skills/tree/main/triage-issue
---

# Triage Issue

Investigate a reported problem, find root cause, create a GitHub issue with a TDD fix plan. Minimize questions — investigate first.

## Process

### 1. Capture
Get a brief description. If not provided, ask ONE question: "What's the problem you're seeing?" Then start investigating immediately.

### 2. Explore & Diagnose
Deep-dive the codebase to find:
- **Where** the bug manifests (entry points, UI, API)
- **What** code path is involved (trace the flow)
- **Why** it fails (root cause, not symptom)
- **What** related code exists (similar patterns, tests)

Check:
- Related source files and dependencies
- Existing tests (what's tested, what's missing)
- Recent changes: `git log --oneline -20 -- <file>`
- Error handling in the code path
- Similar working patterns elsewhere

### 3. Identify Fix Approach
- Minimal change to fix root cause
- Affected modules/interfaces
- Behaviors to verify via tests
- Classification: regression / missing feature / design flaw

### 4. Design TDD Fix Plan
Ordered RED-GREEN cycles (vertical slices):

```
RED:   [specific test capturing broken/missing behavior]
GREEN: [minimal code change to make test pass]
```

Rules:
- Tests verify behavior through public interfaces only
- One test at a time — NOT all tests first
- Tests survive internal refactors
- Include refactor step if needed

### 5. File GitHub Issue

```
gh issue create --title "fix: <root cause summary>" --body "<template below>"
```

Issue template:
```md
## Problem
[What's broken, from user perspective]

## Root Cause
[Technical explanation of why it fails]

## Fix Plan
RED-GREEN cycles:
1. RED: [test description] → GREEN: [code change]
2. ...

## Out of Scope
[What this fix does NOT address]
```

## Key Rules
- Investigate before asking
- Root cause, not symptom
- TDD plan = vertical slices only
- File issue without asking user to review first
- Pairs with `systematic-debugging` for complex multi-layer bugs
