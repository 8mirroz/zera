# 05 Validation Matrix

## Required Gates

| Gate | Command | Required For Done |
|---|---|---|
| Controller syntax | `python3 -m py_compile scripts/zera/zera-evolutionctl.py scripts/internal/self_evolution_loop.py` | Yes |
| Controller dry-run | `zera-evolutionctl dry-run --cycles 1` | Yes |
| Controller lifecycle | `zera-evolutionctl start --cycles 1 --no-promote && zera-evolutionctl status && zera-evolutionctl stop` | Yes |
| Promotion refusal | `zera-evolutionctl start --cycles 1 --allow-promote` | Yes; must refuse without `--force` |
| No orphan loop | `ps -Ao pid,ppid,pgid,stat,etime,command \| rg 'Zera Evolution Daemon|self_evolution_loop.py|vault/loops'` | Yes |
| Zera hardening | `python3 scripts/validation/check_zera_hardening.py` | Yes for production |
| External cron | `python3 scripts/validation/check_external_cron.py` | Yes |
| MCP profile | `python3 scripts/test_mcp_profiles.py` | Yes for tool readiness |
| Agent OS doctor | `python3 repos/packages/agent-os/scripts/swarmctl.py doctor` | Yes for full L4 claim |
| Workflow aliases | `python3 repos/packages/agent-os/scripts/workflow_model_alias_validator.py --json` | Yes |
| Trace schema | `python3 repos/packages/agent-os/scripts/trace_validator.py --json --allow-legacy` | Yes |
| Qwen CLI | `qwen -p 'ping'` | Yes for Qwen-dependent flows |
| Hermes CLI smoke | `hermes chat -Q -q 'ping'` | Yes for chat runtime smoke |

## Acceptance Criteria

- No unmanaged self-evolution cron job is enabled.
- `zera-evolutionctl` is available in `PATH`.
- `--no-promote` prevents beta promotion even after eval pass.
- Legacy `.evolve-state.json` includes `current_algorithm`, `next_algorithm`, `status`, `last_error`, and `consecutive_errors`.
- Every external mutation has a backup path in controller state.
- Full recurring mode is not enabled until red gates are reviewed.

## Known Warnings And Red Gates To Track

- `OPENROUTER_API_KEY` missing if OpenRouter-backed routing is required.
- Legacy compat files are absent until full model-router migration finishes.
- Optional MCP servers are not installed and remain out of active profiles until smoke-tested.
- Trace writer that produced incomplete v2 rows still needs root-cause repair.
- Hermes Qwen OAuth version drift.
- Hermes chat ping passes, but Qwen OAuth refresh must still be verified after update/patch.
- Gateway Telegram/Slack adapters are not verified until extras are installed or adapters are disabled.
