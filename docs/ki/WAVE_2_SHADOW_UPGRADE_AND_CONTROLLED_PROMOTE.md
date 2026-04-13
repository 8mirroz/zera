# Wave 2+3 — Hermes Shadow Upgrade + Controlled Full Promote (Hardened)

**Date:** 2026-04-11 (Wave 2), 2026-04-11 (Wave 3 hardening)
**Status:** Wave 3 implemented
**Scope:** `zera-evolutionctl`, promotion governance, rollback hardening

## Summary

Wave 2 добавил базовые команды shadow upgrade и promotion governance.
Wave 3 закрывает критические проблемы enforcement:

1. **Promotion window enforcement** — `start --allow-promote` требует активного TTL-окна
2. **Snapshot storage outside zera** — snapshots в `~/.hermes/profiles/.backups/zera-promote-snapshots/`
3. **Clean promote-enable flow** — snapshot создаётся ДО policy check (safety net)
4. **promote-status** — новый command для просмотра состояния promotion
5. **Strict gateway check** — `gateway.mode` определяет PASS/FAIL критерии
6. **Probe marker filtering** — shadow-smoke использует уникальные маркеры
7. **Rollback safety** — unsafe snapshots (внутри zera) отклоняются без `--allow-legacy-internal-snapshot`

## Architecture

### New Commands in `zera-evolutionctl`

| Command | Purpose | Wave |
|---------|---------|------|
| `shadow-prepare` | Clone a Hermes profile into a shadow profile | 2 |
| `shadow-upgrade` | Run `hermes update` + smoke (shadow + zera read-only) | 3 |
| `shadow-smoke` | Smoke tests with probe marker filtering | 3 |
| `promote-policy-check` | Validate all 7 promotion gates | 2 |
| `promote-status` | Show current promotion window state | 3 |
| `promote-enable` | Enable controlled full promotion with TTL window | 2 |
| `promote-disable` | Disable controlled promotion | 2 |
| `promote-rollback` | Rollback to a pre-promotion snapshot (safe paths only) | 2/3 |
| `gateway-check` | Verify gateway compatibility (strict mode) | 3 |

### Promotion Gates (7 required)

| Gate | Command | Purpose |
|------|---------|---------|
| swarmctl_doctor | `swarmctl.py doctor` | Agent OS health check |
| check_zera_hardening | `check_zera_hardening.py` | Governance contract validation |
| trace_validator | `trace_validator.py --json --allow-legacy` | Trace integrity |
| test_mcp_profiles | `test_mcp_profiles.py` | MCP profile correctness |
| shadow_smoke | Latest shadow-smoke report | Provider stability verified |
| rollback_snapshot | promotion_state.json snapshot | Reversibility guaranteed |
| gateway_check | `hermes gateway status` (strict) | Gateway mode-aware check |

### Snapshot Storage

Wave 3: Snapshots are stored in `~/.hermes/profiles/.backups/zera-promote-snapshots/`
**outside** the zera profile to prevent self-destruction during rollback.
Each snapshot contains:
- `profile/` — full Hermes profile copy (excluding `_snapshots/` and `.backups/`)
- `vault_loops/` — evolution state files
- `cron/` — cron job definitions
- `snapshot_meta.json` — metadata

### Rollback Logic

Rollback performs:
1. Restore profile from snapshot (displaces current or overwrites in place)
2. Restore vault/loops state
3. Restore cron jobs
4. Disable promotion in state
5. Write artifact report

### TTL Promotion Model

```
promote-enable --scope full --ttl 30
  → policy check passes
  → snapshot created
  → promotion enabled for 30 minutes
  → expires_at set
  → evolution loop can promote within window

promote-disable (manual or auto-expiry)
  → promotion.enabled = false
  → disabled_at recorded
```

## Configuration

### Policy File

`configs/tooling/zera_promotion_policy.yaml` — machine-checkable gate definitions
with default fallback if missing.

### State File

`.agent/evolution/promotion_state.json` — tracks:
- `snapshots[]` — all created snapshots
- `latest_snapshot` — most recent snapshot ID
- `promotion` — current promotion state (enabled, TTL, expiry)

### Artifacts

All command outputs produce JSON reports in `docs/remediation/<command>/<timestamp>/report.json`.

## Usage Examples

### Shadow Upgrade Flow

```bash
# 1. Prepare shadow
zera-evolutionctl shadow-prepare --name zera-shadow --clone-from zera

# 2. Upgrade shadow
zera-evolutionctl shadow-upgrade --profile zera-shadow

# 3. Smoke test shadow
zera-evolutionctl shadow-smoke --profile zera-shadow
# Acceptance: no "Qwen OAuth refresh invalid JSON" in errors.log
```

### Controlled Full Promote

```bash
# 1. Verify all gates
zera-evolutionctl promote-policy-check

# 2. Enable promotion (30 min TTL)
zera-evolutionctl promote-enable --scope full --ttl 30

# 3. Run one bounded cycle
zera-evolutionctl start --cycles 1 --allow-promote --force

# 4. Check status
zera-evolutionctl status
zera-evolutionctl tail

# 5. Disable promotion
zera-evolutionctl promote-disable
```

### Rollback

```bash
# Rollback to latest snapshot
zera-evolutionctl promote-rollback

# Rollback to specific snapshot
zera-evolutionctl promote-rollback --snapshot snapshot-20260411_225202-pre-promote
```

## Testing

24 unit tests in `scripts/zera/test_zera_evolutionctl.py` (Wave 3):

| Test Class | Coverage |
|------------|----------|
| `TestPromotionWindowEnforcement` (5) | bypass prevention, TTL expiry, active window, missing policy report |
| `TestSnapshotStorage` (3) | outside zera, safe/unsafe detection, root creation |
| `TestCleanPromoteEnable` (2) | clean flow, snapshot always created |
| `TestRollbackSafety` (3) | safe rollback, unsafe refusal, legacy override |
| `TestGatewayFalseGreen` (3) | not-running fails when required, passes when disabled_allowed |
| `TestShadowSmokeProbeMarker` (3) | Qwen signature detection, no false positives, marker usage |
| `TestPromoteStatus` (2) | disabled state, legacy snapshot detection |
| `TestHelperFunctions` (3) | utc_now, read_json, write_json |

All tests pass with `python3 -m pytest scripts/zera/test_zera_evolutionctl.py -v`.

## Design Decisions

### Why snapshots outside profile? (Wave 3)

Wave 2 хранил snapshots в `~/.hermes/profiles/zera/backups/_snapshots/`. Это
создавало критический риск: rollback (который делает `shutil.move` профиля) мог
удалить сам snapshot вместе с профилем. Wave 3 перемещает snapshots в
`~/.hermes/profiles/.backups/zera-promote-snapshots/` — полностью вне zera.

### Why promotion window enforcement? (Wave 3)

Wave 2: `start --allow-promote --force` обходил все проверки. Wave 3:
`--allow-promote` требует активного TTL-окна, существующего snapshot и
проходящего policy report. `--force` только подтверждает намерение внутри
окна, но не обходит политику.

### Why snapshot-first promote-enable? (Wave 3)

Wave 2 требовал snapshot ДО policy check, но policy check тоже требовал
snapshot — логический deadlock. Wave 3: snapshot создаётся ВСЕГДА первым
шагом (safety net), затем policy check. Если policy fails — snapshot остаётся
как rollback artifact, promotion не включается.

### Why TTL-based promotion?

Unrestricted promotion is dangerous. A TTL window provides:
- **Time-bounded risk** — promotion can only occur within a known window
- **Easy rollback** — snapshot taken before enable
- **Manual override** — `promote-disable` can be called early
- **No permanent state** — promotion is not a "set and forget" toggle

### Why strict gateway check? (Wave 3)

Wave 2 считал `Gateway is not running` допустимым всегда. Wave 3: поведение
определяется `gateway.mode` в policy:
- `disabled_allowed` (default) — PASS если gateway не запущен
- `required` — PASS только если gateway запущен с готовыми adapters

### Why probe marker filtering? (Wave 3)

Wave 2 проверял все errors за окно `--since 30m`, включая старые нерелевантные
ошибки. Wave 3: smoke использует уникальный probe marker и фильтрует ошибки
только по Qwen OAuth signature, избегая false positives от legacy errors.
