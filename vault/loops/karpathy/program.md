---
type: knowledge
created: 2026-04-08
tags: [synced, healed]
---

# Karpathy Loop — Antigravity Core Router Optimization

## Goal
Optimize configs/orchestrator/router.yaml to maximize first_pass_success_rate.

## Rules
1. You can ONLY modify configs/orchestrator/router.yaml
2. Each iteration: modify → test → measure → keep if better
3. Metric: first_pass_success_rate (higher is better)
4. Time budget: 5 minutes per experiment
5. Max 50 iterations total
6. Stop if: score >= 0.90 OR plateau for 5 iterations

## What to try
- Adjust C1-C5 tier thresholds
- Change model routing (different models per tier)
- Modify max_tools limits per tier
- Enable/disable feature flags
- Adjust memory retrieval params (top_k, min_score)
- Change task type mappings

## Process
1. Read current router.yaml
2. Read current best score from results.jsonl
3. Make ONE change (or small related set)
4. Validate YAML syntax
5. If valid → save as candidate, mark as "testing"
6. After test cycle → record score
7. If score > best → keep as new best, else revert
8. Log result to results.jsonl
9. Repeat

## Safety
- Never change security-related settings
- Never change API keys or credentials
- Never disable completion gates
- Always keep backup before changes
