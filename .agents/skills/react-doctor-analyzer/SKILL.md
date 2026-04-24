---
name: react-doctor-analyzer
description: Assess and automatically heal React/Next.js projects by fixing performance, architecture, React warnings, and dead code using millionco react-doctor CLI tool.
---

# React Doctor Analyzer

## Overview
Use this skill when you need to audit or fix performance, useEffect-related loops, unused code, or general React architecture issues in a Next.js or React application. The `react-doctor` tool analyzes compiler configuration, framework, and React version to produce a health score, warning/error descriptions, and actionable paths.

## The Algorithm

### 1. Execute Analysis
Run the `react-doctor` CLI manually in verbose mode to diagnose issues across the project.
**NEVER use `--fix` as it launches an interactive interface that hangs the agent!**

```bash
npx -y react-doctor@latest . --no-ami --verbose
```

### 2. Parse Diagnostics & Isolate
Identify the specific sub-systems or files that failed analysis.
- **Goal:** Group the problems to avoid monolithic code replacements.
- **Key Categories:** Unnecessary rerenders, broken effect dependencies (infinite loops), unused variables/exports.

### 3. Hypothesize and Patch (Iterative Repair)
Examine a specific diagnostic. Make changes that strictly fix that exact diagnostic without modifying arbitrary logic.
- Ensure dependency arrays are accurate and stable (e.g., using `useCallback` or `useMemo`).
- Remove dead code safely.

### 4. Verify Fixes
Rerun the doctor to calculate the new health score.
```bash
npx -y react-doctor@latest . --no-ami --verbose
```
**Goal:** Verify health score is $\ge 75$ ("Great") and critical errors are gone before considering the job complete.
