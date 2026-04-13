---
name: subagent-driven-development
description: Use when a task is complex (C5) and requires high quality. Orchestrates specialized sub-agents.
---

# Subagent Driven Development

## Overview
Decompose a complex task into specialized roles executed by sub-agents.

## The Roles
1. **Spec Reviewer**: Critiques the plan/requirements for gaps.
2. **Implementer**: writes the code (can be multiple parallel).
3. **Code Reviewer**: Reviews the code against standards.

## The Process

### 1. Spec Review
- **Call**: `browser_subagent` (or generic subagent) with `spec-reviewer-prompt.md`.
- **Task**: "Review this implementation plan for potential issues."
- **Output**: List of risks/gaps.

### 2. Implementation
- **Call**: `browser_subagent` with `implementer-prompt.md`.
- **Task**: "Implement the plan. Write code."
- **Output**: Modified files.

### 3. Code Review
- **Call**: `browser_subagent` with `code-quality-reviewer-prompt.md`.
- **Task**: "Review the changes in [files]."
- **Output**: List of issues to fix.

## When to Use
- **Critical Features** (Payments, Auth).
- **Complex Refactoring**.
- **Security Sensitive** changes.
