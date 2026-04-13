---
name: using-git-worktrees
description: Use when starting a new complex task to isolate changes from the main working directory.
---

# Using Git Worktrees

## Overview
Git Worktrees allow you to have multiple branches checked out at once in different directories. This is SAFER than switching branches in the main root.

## Setup
```bash
# 1. Create a worktree for the feature
git worktree add -b feat/my-feature ../feat-my-feature main

# 2. Move into it
cd ../feat-my-feature

# 3. Do work (Context is isolated)
```

## Benefits
- **Safety**: No risk of accidentally committing to main.
- **Context**: Different files open, different build artifacts.
- **Parallelism**: Can work on `feat-A` and `fix-B` simultaneously.

## Cleanup
```bash
# When done:
cd ../main-repo
git worktree remove ../feat-my-feature
git branch -d feat/my-feature
```
