# Zera Self-Evolution Workflow

## Execution Pipeline

### Phase 1: Preparation
```
1. Check freeze-state.json — if frozen, halt unless --force
2. Verify all required files exist
3. Pick next loop based on .evolve-state
4. Resolve command_id and branch_type
```

### Phase 2: Research (Advisory Context)
```
1. Read loop config.yaml and algorithm.md
2. Execute algorithm within loop directory
3. Log results to results.jsonl
4. Update knowledge/progress files
5. STOP — do not mutate system directly
```

### Phase 3: Analysis & Classification
```
1. Collect signals from recent interactions
2. Generate candidates
3. Classify each candidate:
   - capability (allowed)
   - personality (review-required)
   - mixed (escalate)
   - governance (freeze + escalate)
4. Filter by governance config
```

### Phase 4: Report
```
1. signals — what was observed
2. candidates — what was found
3. promotion_decisions — what was approved
4. review_required — what needs human review
5. rollback_paths — how to undo if needed
6. drift_risks — what could go wrong
7. next_cycle_focus — what to prioritize next
```

### Phase 5: Execution (if approved)
```
1. Apply capability changes (direct)
2. Queue personality changes for review
3. Freeze governance changes
4. Update memory/stability
5. Document in vault
```

## Command Reference
```bash
# Run one bounded cycle
bash scripts/zera-self-evolution.sh

# Dry run — show prompt only
bash scripts/zera-self-evolution.sh --dry-run

# Force through freeze
bash scripts/zera-self-evolution.sh --force

# Personality loop
bash scripts/zera-self-evolution.sh --loop personality
```

## Output Locations
- Prompt: `vault/research/reports/evolution-prompt-{run_id}.txt`
- Branch manifest: `vault/research/branches/branch-{run_id}.json`
- Loop results: `vault/loops/{loop_name}/results.jsonl`

---

*Created: 2026-04-16*
