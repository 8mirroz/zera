---
name: systematic-debugging
description: Use when investigating a reproducible bug, failing test, or runtime error. Prevents random trial-and-error.
---

# Systematic Debugging

## The Algorithm

### 1. Reproduce
- **Goal:** Create a minimal reproduction case.
- **Output:** A script or set of steps that reliably triggers the bug.
- **Stop condition:** If you can't reproduce it, you can't fix it.

### 2. Isolate
- **Goal:** Narrow down the search space.
- **Action:** Binary search modules, mock external deps, remove config.
- **Question:** "What is the smallest system that still has the bug?"

### 3. Hypothesize
- **Goal:** Propose 2-3 theories.
- **Format:** "I suspect X because Y. If X is true, then Z should happen."

### 4. Verify Hypothesis
- **Goal:** Prove/Disprove without changing code (logs, breakpoints).
- **Action:** Add logging probe. Run reproduction.
- **Result:** Confirmed or Rejected.

### 5. Fix
- **Goal:** Implement the fix.
- **Action:** Apply the code change.

### 6. Regression Test
- **Goal:** Ensure it stays fixed.
- **Action:** Convert reproduction script into a permanent test.

## Key Rules
- **One change at a time.**
- **Read the error message** (literacy check).
- **Don't guessing.** (e.g. "maybe if I reinstall node_modules...")
