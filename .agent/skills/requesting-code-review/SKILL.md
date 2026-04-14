---
name: requesting-code-review
description: Use when you want a second opinion on your code before human review.
---

# Requesting Code Review

## Overview
Self-review using a separate agent instance to simulate fresh eyes.

## The Process

1. **Diff Context**: Gather the diffs of your changes.
2. **Subagent Call**: Call `browser_subagent` with `code-reviewer.md`.
3. **Instruction**: "Review this diff. Focus on: Safety, Logic, Style."
4. **Action**:
   - If subagent finds issues -> **Fix them**.
   - If subagent says LGTM -> **Submit to human**.

## Why?
- Catches stupid mistakes (console.logs, typos).
- Validates the "Definition of Done".
