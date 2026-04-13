# 01 Local Forensic Audit — Zera Runtime

Date: 2026-04-11  
Scope: `/Users/user/antigravity-core` and redacted `~/.hermes/profiles/zera`.

## Current State

- Active Hermes profile: `zera`.
- Hermes CLI: `Hermes Agent v0.8.0 (2026.4.8)`.
- Hermes reported update drift: `103 commits behind`.
- Zera profile exists at `~/.hermes/profiles/zera`.
- Session database exists and is non-empty: 73 sessions, 1437 messages.
- Gateway state recorded `startup_failed`: all configured messaging platforms failed to connect.
- Cron folder exists outside repo governance and had an enabled unmanaged self-evolution job.
- `qwen -p 'ping'` worked locally after the incident, so Qwen credentials were not obviously corrupted.

## Reproduced Failures

- `swarmctl.py doctor` failed on router parsing, wiki-core paths, workflow aliases, and trace validation.
- `check_zera_hardening.py` failed because expected root entrypoints were missing while real scripts lived under `scripts/zera/`.
- `scripts/test_mcp_profiles.py` failed with 9 missing MCP servers and one route mismatch.
- `trace_validator.py --json --allow-legacy` reported invalid trace rows with missing required fields.
- The previous daemon PID was inline `python3 -c` placeholder logic and not a real agent loop.

## Root Causes

1. Source-of-truth drift: repo config, Hermes profile config, cron files, vault state, and docs all encode overlapping semantics.
2. Runtime path drift: `scripts/internal/self_evolution_loop.py` calculated repo root as `scripts/`, causing governance defaults to be used silently after the file move.
3. Lifecycle drift: raw background loops were started without a pid file, lock, kill-switch, schema validation, or supervisor.
4. State schema drift: legacy `.evolve-state.json` had `next_algorithm`, while the broken daemon expected `current_algorithm`.
5. Provider fragility: Hermes `qwen-oauth` has a known invalid JSON refresh issue fixed upstream after the installed release.
6. Cron overreach: autonomous cron prompts asked an agent to execute and mutate state every minute without a real control plane.
7. MCP overbreadth: installed/expected tool servers do not match validated availability.
8. Memory is declarative: profile memory exists, but memory layering is not enforced across chat, cron, and repo runtime.

## Corrections Already Applied In This Rebuild

- Added `zera-evolutionctl` controller.
- Installed `~/.local/bin/zera-evolutionctl` symlink.
- Created a timestamped external backup under `~/.hermes/profiles/zera/backups/`.
- Disabled the unmanaged enabled self-evolution cron job.
- Added root symlinks for hardening compatibility.
- Fixed `self_evolution_loop.py` repo root calculation.
- Added `--no-promote` to the core evolution loop.
- Normalized legacy `vault/loops/.evolve-state.json`.
- Updated the YAML compatibility parser to prefer real YAML parsing when available.

## Remaining Known Red Gates

- `swarmctl doctor` now passes after YAML compatibility, wiki-core path, workflow registry, MCP profile, and trace quarantine repairs.
- `swarmctl doctor` still warns about missing `OPENROUTER_API_KEY` and legacy compat files absent until full migration.
- Hermes upstream update or local Qwen OAuth patch still needs a guarded shadow-profile test.
- Optional MCP servers were pruned from active profiles until installed and smoke-tested.
- Gateway should remain disabled or platform extras must be installed before claiming Telegram/Slack readiness.
