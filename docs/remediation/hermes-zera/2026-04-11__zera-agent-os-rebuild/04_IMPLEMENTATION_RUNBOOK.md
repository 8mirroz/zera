# 04 Implementation Runbook

## Phase 0 — Freeze Unsafe Autonomy

```bash
ps -Ao pid,ppid,pgid,stat,etime,command | rg 'Zera Evolution Daemon|vault/loops|current_algorithm|next_algorithm|self_evolution_loop.py|zera-evolve|zera-self-evolution' || true
zera-evolutionctl backup
zera-evolutionctl sanitize-cron
zera-evolutionctl status
```

Expected result:

- No unmanaged evolution process remains.
- External backup exists under `~/.hermes/profiles/zera/backups/`.
- Unmanaged self-evolution cron jobs are disabled.

## Phase 1 — Controller Smoke

```bash
python3 -m py_compile scripts/zera/zera-evolutionctl.py scripts/internal/self_evolution_loop.py
zera-evolutionctl dry-run --cycles 1
zera-evolutionctl start --cycles 1 --no-promote
sleep 3
zera-evolutionctl status
zera-evolutionctl tail --lines 80
zera-evolutionctl stop
```

Expected result:

- Dry-run exits cleanly.
- One live no-promote run starts under PID file control.
- Stop leaves no orphan process.

## Phase 2 — Repo Gates

```bash
python3 repos/packages/agent-os/scripts/swarmctl.py doctor
python3 scripts/validation/check_zera_hardening.py
python3 scripts/validation/check_external_cron.py
python3 scripts/test_mcp_profiles.py
python3 repos/packages/agent-os/scripts/workflow_model_alias_validator.py --json
python3 repos/packages/agent-os/scripts/trace_validator.py --json --allow-legacy
```

Expected result:

- Hardening and external cron pass.
- Remaining red gates are documented before any recurring autonomy is enabled.

## Phase 3 — Hermes Provider Repair

```bash
hermes --version
qwen -p 'ping'
```

Then choose one:

- Update Hermes in a shadow profile and verify Qwen OAuth.
- Or locally patch Hermes Qwen OAuth refresh with the User-Agent fix and verify.

Do not enable Qwen-dependent gateway/cron until Hermes Qwen auth passes through Hermes itself.

## Phase 4 — MCP Surface Repair

```bash
python3 scripts/test_mcp_profiles.py
```

For each missing server:

- install it,
- remove it from active profile,
- or mark it explicitly disabled in repo source-of-truth.

Do not rely on a tool server that is missing in validation.

## Phase 5 — Controlled Recurring Mode

Only after gates are green or accepted:

```bash
zera-evolutionctl start --forever --interval 900 --no-promote
zera-evolutionctl status
```

Promotion remains disabled until a separate operator-approved promotion run exists.
