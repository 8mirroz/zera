# Critic Workflow
# Phase 3 - AI-powered code review
# Version: 1.0

## Overview

Critic workflow activates automatically for C3+ tasks or manually via `critic` command.
It performs adversarial review of code changes to find weaknesses before they become bugs.

## Workflow Steps

### Step 1: Collect Changes

```bash
# Get diff of changes
git diff HEAD~1 --staged > /tmp/critic_diff.patch

# Or review specific files
git diff {files} > /tmp/critic_diff.patch
```

### Step 2: Analyze with Critic

```bash
# Run critic on the diff
cat /tmp/critic_diff.patch | model --role critic "Review this code critically"
```

### Step 3: Parse Results

Parse critic output into structured format:
- CRITICAL issues → BLOCK
- HIGH issues → WARN
- MEDIUM/LOW → NOTE

### Step 4: Generate Report

Output to `.agent/reviews/critic_{task_id}_{timestamp}.md`

## Usage

```bash
# Manual trigger
critic

# On specific files
critic --files src/auth.py src/users.py

# Force critic on C1/C2
critic --force
```

## Integration Points

- Triggered by: `execution_loop.yaml` Step 6
- Completion gates: `completion_gates.yaml` C3+
- Output to: Memory system for lessons learned
