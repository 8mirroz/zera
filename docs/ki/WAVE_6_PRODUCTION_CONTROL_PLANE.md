# Wave 6 — Production-Grade Control Plane

**Date:** 2026-04-11
**Status:** Implemented
**Scope:** zera-evolutionctl, self_evolution_loop.py, policy v6.0.0

## Summary

Wave 6 превращает promotion control plane в **production-grade систему** с доказанной безопасностью:

1. **Real rehearsal** — полноценный end-to-end bounded cycle с `ZERA_EVO_NO_MUTATE=1`
2. **No-mutate enforcement** — env var enforced на уровне core loop, не только controller
3. **Session binding** — session_id extraction из hermes chat output
4. **Evidence chain** — 7-point validation целостности evidence
5. **Provider health check** — LLM provider health перед promotion
6. **Promotion calendar + metrics** — история и статистика всех attempts
7. **Rate limiting** — max 3 attempts/hour
8. **Input validation** — attempt_id format, profile name validation

## New Commands

| Command | Purpose |
|---------|---------|
| `validate-evidence-chain --attempt-id <id>` | 7-point evidence chain validation |
| `check-provider-health [--profile zera]` | LLM provider health check |
| `promotion-calendar [--since 30d]` | Historical attempt timeline |
| `promotion-metrics [--since 30d]` | Success rates, failure analysis |

## Changed Commands

| Command | Wave 6 Change |
|---------|--------------|
| `promote-rehearsal` | Real bounded cycle + no-mutate + wait for completion + evidence verification |
| `shadow-smoke` | Session ID extraction + session-scoped log checks |
| `promote-enable` | Rate limiting + input validation |
| `start` | `--no-mutate-code` flag → `ZERA_EVO_NO_MUTATE=1` in core loop env |
| `promote-status` | Includes attempt_id, calendar summary |

## Core Loop Changes

`self_evolution_loop.py` — `phase_promote()`:
```python
# Wave 6: No-mutate enforcement
no_mutate_env = os.environ.get("ZERA_EVO_NO_MUTATE", "0") == "1"
if no_mutate_env:
    logger.info("  → NO-MUTATE MODE: promotion skipped")
    return "no_mutate_skipped"
```

## Evidence Chain Validation (7 checks)

1. ✅ Snapshot exists + safe (outside zera profile)
2. ✅ Smoke report exists + ok + session_id or probe_marker
3. ✅ Policy check report exists + all gates pass + attempt_id match
4. ✅ Gateway report exists + attempt_id match
5. ✅ Promote-enable report exists + snapshot_id + attempt_id match
6. ✅ Monotonic timestamps (snapshot < smoke < policy < enable)
7. ✅ All reports reference the same attempt_id

## Rate Limiting

- Default: max 3 promotion attempts per hour
- Configurable via policy: `rate_limiting.max_attempts_per_hour`
- Stored in `promotion_state.json.attempt_timestamps`
- `promote-enable` checks before proceeding

## Artifact Schema

All artifacts validated against `configs/tooling/zera_promotion_artifact_schema.json`:
- Required: `schema_version`, `command`, `attempt_id`, `ok`, `timestamp`
- Command enum validation
- Type checking for all fields

## Policy v6.0.0

New sections:
- `rehearsal.bounded_cycle_required: true`
- `rehearsal.no_mutate_env_enforced: true`
- `rate_limiting.max_attempts_per_hour: 3`
- `provider_health.check_before_promotion: true`
- `artifact_schema.evidence_chain_validation: true`
- `promotion.input_validation_required: true`

## Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Unit | 28 | ✅ All pass |
| Integration | 11 | ✅ All pass |
| Runtime audit | CLEAN | ✅ |

## Commands Quick Reference

```bash
# Full rehearsal (safe — no real mutation)
zera-evolutionctl promote-rehearsal --profile zera-shadow --ttl 5 --no-mutate-code

# Evidence chain validation
zera-evolutionctl validate-evidence-chain --attempt-id <id>

# Provider health
zera-evolutionctl check-provider-health --profile zera

# Calendar + metrics
zera-evolutionctl promotion-calendar --since 7d
zera-evolutionctl promotion-metrics --since 30d

# Runtime audit
zera-evolutionctl audit-runtime-state

# Artifact validation
zera-evolutionctl validate-artifacts --attempt-id <id>

# Cleanup stale attempts
zera-evolutionctl cleanup-attempts --older-than 7 --dry-run
```
