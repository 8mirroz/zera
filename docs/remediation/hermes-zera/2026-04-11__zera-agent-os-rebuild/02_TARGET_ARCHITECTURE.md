# 02 Target Architecture — Zera Agent OS

## Architecture

Zera becomes an Agent OS with six controlled planes:

- Runtime plane: Hermes chat, repo-native command runtime, and optional gateway.
- Command plane: `zera:*` command registry in repo owns semantics.
- Tool plane: MCP profiles with allowlisted servers and task-based expansion.
- Memory plane: profile memory, repo knowledge, session summaries, and cron read-only memory.
- Autonomy plane: cron and evolution jobs only through governed controllers.
- Observability plane: traces, telemetry, reports, and validation gates.

## Source Of Truth

Repo is canonical. Hermes profile is a rendered runtime target.

Canonical repo surfaces:

- `configs/tooling/zera_command_registry.yaml`
- `configs/tooling/zera_client_profiles.yaml`
- `configs/tooling/zera_growth_governance.json`
- `configs/tooling/zera_branching_policy.yaml`
- `configs/orchestrator/router.yaml`
- `configs/orchestrator/models.yaml`
- `configs/tooling/mcp_profiles.json`

External surfaces:

- `~/.hermes/profiles/zera/config.yaml`
- `~/.hermes/profiles/zera/cron/*.json`
- `~/.hermes/profiles/zera/state.db`
- `~/.qwen/oauth_creds.json`

External surfaces must be backed up before mutation and checked against repo contracts after mutation.

## Autonomy Contract

Aggressive autonomy is allowed only as bounded autonomy:

- Observe/report jobs may run frequently.
- Mutation jobs require `zera-evolutionctl`.
- Promotion is disabled by default in test/live smoke runs via `--no-promote`.
- Forever mode requires explicit `--forever`; interval under 300s requires `--force`.
- Kill switch file: `.agents/evolution/KILL_SWITCH`.
- PID file: `.agents/evolution/evolutionctl.pid`.
- Controller state: `.agents/evolution/evolutionctl-state.json`.
- Core telemetry/log: `.agents/evolution/telemetry.jsonl` and `.agents/evolution/loop.log`.

## Model Routing

Hybrid Premium policy:

- C1/C2: local or cheap model when available.
- Research/synthesis: Qwen/Gemini or equivalent fast high-context model.
- C3/C4/C5 code and architecture: premium GPT/Claude/Codex-class route.
- Qwen OAuth path is allowed only after the User-Agent fix is present or a local smoke test passes.
- Custom provider fallbacks are disabled until fallback-specific endpoint behavior is verified.

## Evolution Flow

1. `zera-evolutionctl backup`
2. `zera-evolutionctl sanitize-cron`
3. `zera-evolutionctl dry-run --cycles 1`
4. `zera-evolutionctl start --cycles 1 --no-promote`
5. `zera-evolutionctl status`
6. `zera-evolutionctl tail`
7. `zera-evolutionctl stop`
8. Run validation matrix.
9. Only then consider controlled recurring mode.
