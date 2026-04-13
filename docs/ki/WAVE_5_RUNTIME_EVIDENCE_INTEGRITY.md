# Wave 5 — Hermetic Tests, Real Rehearsal, Runtime Evidence Integrity

**Date:** 2026-04-11
**Status:** Implemented
**Scope:** zera-evolutionctl, test isolation, artifact schema, runtime audit

## Summary

Wave 5 превращает promotion control plane из "команды существуют" в **доказуемо безопасную систему**:

1. **Hermetic test isolation** — unit tests не пишут в `~/.hermes` или `docs/remediation`
2. **Artifact schema + validate-artifacts** — все отчеты валидируются против JSON Schema
3. **Runtime state auditor** — `audit-runtime-state` проверяет orphan процессы, expired promotion, unsafe snapshots, unsafe cron jobs
4. **Cleanup attempts** — `cleanup-attempts` удаляет старые attempt artifacts
5. **Policy v5.0.0** — gateway intent required, artifact schema required, test isolation enforced, rehearsal required
6. **Integration test v5** — 11 проверок вместо 8, включая artifact schema и policy sections

## New Commands

| Command | Purpose |
|---------|---------|
| `validate-artifacts --attempt-id <id>` | Validate all attempt artifacts against schema |
| `audit-runtime-state` | Check runtime for safety issues (orphan PIDs, expired promotion, unsafe snapshots, unsafe cron) |
| `cleanup-attempts --older-than 7d --dry-run` | Clean up stale attempt artifacts |

## Changed Behavior

| Change | Before | After |
|--------|--------|-------|
| Policy version | 3.0.0 | **5.0.0** |
| Test isolation | Partial patching | **Full hermeticity guard** — writes to real paths fail tests |
| Artifact paths | Legacy only | **Scoped (wave4) + legacy** for backward compat |
| Gateway check | `disabled_allowed` passes on "not running" | **Intent required** — config flag or `.gateway_disabled` artifact |
| `_load_promotion_policy` | Fallback default | **Fail-closed** — missing policy is an error |
| `_run_gate` | `FileNotFoundError` = skip/ok | **Fail-closed** — `FileNotFoundError` = fail for required gates |

## Artifact Schema

All promotion artifacts must conform to `configs/tooling/zera_promotion_artifact_schema.json`:

**Required fields:**
- `schema_version` (integer)
- `command` (enum: shadow-smoke, promote-policy-check, promote-enable, promote-disable, promote-rollback, promote-rehearsal, gateway-check)
- `attempt_id` (string)
- `ok` (boolean)
- `timestamp` (ISO 8601)

**Optional fields:**
- `artifact_path`, `runtime_profile`, `evidence_refs`, `gates`, `snapshot_id`, `ttl_minutes`, `results`, `hermes_version_before`

## Test Architecture

### Hermeticity Guard

All tests patch these constants to temp directories:
- `HERMES_ZERA_PROFILE` → `tmp/zera`
- `HERMES_PROFILES_DIR` → `tmp/profiles`
- `HERMES_ROOT` → `tmp/.hermes`
- `SNAPSHOT_ROOT` → `tmp/snapshots`
- `PROMOTION_STATE_FILE` → `tmp/evolution/promotion_state.json`
- `PROMOTION_ARTIFACTS_DIR` → `tmp/remediation`
- `HERMES_ZERA_ARTIFACT_BASE` → `tmp/scoped_artifacts`
- `EVOLUTION_DIR` → `tmp/evolution`
- `CTL_STATE_FILE` → `tmp/evolution/evolutionctl-state.json`
- `LEGACY_STATE_FILE` → `tmp/vault/loops/.evolve-state.json`
- `KILL_SWITCH_FILE` → `tmp/evolution/KILL_SWITCH`

**Guard on `Path.write_text` and `Path.mkdir`** — any write to real `~/.hermes` or `docs/remediation` raises `PermissionError` and fails the test.

### Test Coverage (28 tests)

| Class | Tests | Coverage |
|-------|-------|----------|
| `TestPromotionWindowEnforcement` | 5 | bypass prevention, TTL expiry, active window with attempt-bound policy, missing policy report |
| `TestSnapshotStorage` | 3 | outside zera, safe/unsafe detection, root creation |
| `TestCleanPromoteEnable` | 2 | clean flow with attempt_id, snapshot always created |
| `TestRollbackSafety` | 3 | safe rollback, unsafe refusal, legacy override |
| `TestGatewayFalseGreen` | 3 | not-running fails when required, passes when disabled_allowed |
| `TestShadowSmokeProbeMarker` | 3 | Qwen signature detection, no false positives, marker usage |
| `TestPromoteStatus` | 2 | disabled state, legacy snapshot detection |
| `TestArtifactValidation` | 2 | schema validation passes, fails on missing fields |
| `TestRuntimeAudit` | 1 | clean runtime state |
| `TestHelperFunctions` | 4 | utc_now, read_json, write_json, generate_attempt_id |

## Integration Test (11 checks)

1. promote-disable runs
2. audit-runtime-state runs
3. refusal without active window
4. promote-rehearsal command with flags
5. promote-policy-check --attempt-id
6. validate-artifacts command
7. cleanup-attempts command
8. promote-rollback --allow-legacy-internal-snapshot
9. Policy v5.0.0 with all required sections
10. Artifact schema exists and valid
11. Scoped artifact base directory exists

## Run Commands

```bash
# Unit tests
python3 -m pytest scripts/zera/test_zera_evolutionctl.py -v

# Integration tests
bash scripts/zera/verify_zera_promotion_control_plane.sh

# Runtime audit
zera-evolutionctl audit-runtime-state

# Validate artifacts for an attempt
zera-evolutionctl validate-artifacts --attempt-id <id>

# Cleanup stale attempts
zera-evolutionctl cleanup-attempts --older-than 7 --dry-run
```

## Operator Runbook

### Normal Rehearsal Flow
```bash
# 1. Prepare shadow profile
zera-evolutionctl shadow-prepare --name zera-shadow --clone-from zera

# 2. Run shadow smoke
zera-evolutionctl shadow-smoke --profile zera-shadow

# 3. Run rehearsal
zera-evolutionctl promote-rehearsal --profile zera-shadow --ttl 5 --no-mutate-code

# 4. Validate artifacts
zera-evolutionctl validate-artifacts --attempt-id <attempt_id_from_rehearsal>

# 5. Audit runtime
zera-evolutionctl audit-runtime-state
```

### Failed Rehearsal Triage
1. Check rehearsal report in scoped artifacts
2. Run `audit-runtime-state` for safety issues
3. Fix identified issues
4. Retry rehearsal

### Rollback Drill
```bash
# 1. Create snapshot
zera-evolutionctl shadow-prepare --name zera-shadow --clone-from zera

# 2. Simulate promotion
zera-evolutionctl promote-enable --scope full --ttl 5

# 3. Rollback
zera-evolutionctl promote-rollback

# 4. Verify clean state
zera-evolutionctl audit-runtime-state
```

### Cleanup Stale Attempts
```bash
# Preview what would be cleaned
zera-evolutionctl cleanup-attempts --older-than 7 --dry-run

# Actually clean
zera-evolutionctl cleanup-attempts --older-than 7
```

### When Full Promote Is Allowed
Full promote requires ALL of:
1. `promote-rehearsal` passes (all steps)
2. `validate-artifacts` passes for the rehearsal attempt
3. `audit-runtime-state` returns CLEAN
4. All 7 promotion gates pass via `promote-policy-check`
5. Active promotion window with valid attempt_id

## Policy SOT

`configs/tooling/zera_promotion_policy.yaml` v5.0.0 contains:
- **gates** — 7 required gates with command paths
- **gateway** — mode, disabled_intent_required, required_adapters
- **artifact_schema** — required=true, path, max_report_age_minutes
- **snapshot** — root path (outside zera)
- **test_isolation** — real_runtime_writes_forbidden=true
- **rehearsal** — required_before_real_promote=true
- **promotion** — require_active_window=true, max_ttl_minutes=120
- **rollback** — refuse_internal_snapshots=true
