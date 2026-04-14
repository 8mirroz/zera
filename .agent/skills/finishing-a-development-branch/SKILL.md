---
name: finishing-a-development-branch
description: Use when development is complete and verified. Merges worktree changes back to main branch.
---

# Finishing a Development Branch

## Overview
Clean up the workspace and merge changes.

## The Process

### 1. Final Verification
- Run `verification-before-completion`
- Ensure all tests pass.

### 2. Commit
- Stage all changes.
- Create a semantic commit message:
  - `feat: ...`
  - `fix: ...`
  - `docs: ...`

### 3. Merge (if using Worktrees)
- Push the branch.
- Create a PR (if using GitHub flow) OR Merge locally (if using Trunk-based).
- **If Merge Locally**:
  - `git checkout main`
  - `git merge --squash <feature-branch>`
  - `git commit -m "..."`

### 4. Cleanup
- Delete the feature branch.
- Remove the worktree (if used).
- `git worktree remove <path>`
