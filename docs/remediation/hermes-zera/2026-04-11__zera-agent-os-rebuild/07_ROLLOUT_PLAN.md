# 07 Rollout Plan

## Stage 1 — Stabilized Manual Mode

Criteria:

- `zera-evolutionctl` installed.
- Unsafe self-evolution cron disabled.
- Controller dry-run passes.
- No unmanaged evolution process remains.

Allowed:

- Manual chat.
- Manual repo-native commands.
- Manual `zera-evolutionctl dry-run`.

Forbidden:

- Forever evolution mode.
- Promotion.
- Gateway claim.

## Stage 2 — Single-Cycle No-Promote Mode

Criteria:

- Stage 1 complete.
- `zera-evolutionctl start --cycles 1 --no-promote` starts and exits cleanly.
- `zera-evolutionctl stop` leaves no process.

Allowed:

- One controlled live cycle.
- Report generation.
- No-promote eval runs.

Forbidden:

- Cron-driven mutation.
- Beta promotion.

## Stage 3 — Aggressive Observation Mode

Criteria:

- External cron governance passes.
- Red gates are either fixed or explicitly accepted in a report.

Allowed:

- Frequent lightweight observation/report jobs.
- Read-only memory use for cron where available.

Forbidden:

- Direct stable config mutation from cron.
- Self-evolution through raw prompt jobs.

## Stage 4 — Controlled Recurring Evolution

Criteria:

- Hardening validator passes.
- MCP active profile has no missing required servers.
- Trace and workflow red gates are resolved or formally accepted.
- Hermes provider auth smoke passes.

Allowed:

```bash
zera-evolutionctl start --forever --interval 900 --no-promote
```

Promotion remains a separate operator-approved flow.

## Stage 5 — Promotion-Eligible Evolution

Criteria:

- A dedicated promotion runbook exists.
- Beta manager is verified.
- Rollback rehearsal passes.
- Operator approves promotion scope.

Allowed:

- Candidate promotion only after evidence, eval, report, and rollback artifact.

Forbidden:

- Silent personality or governance mutation.
