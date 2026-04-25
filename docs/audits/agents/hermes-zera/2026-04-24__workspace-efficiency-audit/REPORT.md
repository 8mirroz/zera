# Hermes + Zera Workspace Audit (2026-04-24)

## Scope
- Workspace: `/Users/user/zera`
- Focus: фактическая эффективность и устойчивость связки `Hermes + Zera` (runtime, routing, governance, quality gates)
- Method: live command execution + config/runtime evidence (не по историческим markdown)

## Current Implementation (How It Works)
- Task routing policy задается в `configs/orchestrator/router.yaml` (tiers C1-C5, runtime `agent_os_python` по умолчанию).
- Runtime registry читает `configs/tooling/runtime_providers.json`; `hermes` задекларирован, но отключен, `zeroclaw` включен.
- Zera command semantics задаются `configs/tooling/zera_command_registry.yaml`; Hermes adapter ссылается на этот SoT.
- Внешний Hermes runtime profile живет вне репозитория: `~/.hermes/profiles/zera/config.yaml`.
- Локальный launcher `zera` идет через `/Users/user/.local/bin/zera`.

## Live Validation Results
### Passed
- `python3 scripts/validation/check_reliability_platform.py --json` -> `status: ok`
- `python3 repos/packages/agent-os/scripts/swarmctl.py doctor` -> `OK: doctor passed` (с предупреждениями)
- `AG_SKIP_PREFLIGHT=1 bash scripts/run_quality_checks.sh --quick` -> `status: ok` (smoke suite)
- `python3 scripts/zera/zera_command_runtime.py catalog --json` -> command catalog доступен

### Failed / Degraded
- `bash scripts/run_quality_checks.sh --quick` -> preflight fail (`broken_symlinks:38`)
- `cd repos/packages/agent-os && uv run python ../../../scripts/reliability_orchestrator.py run --suite governance --json` -> failed (`zera-hardening-validator` exit 1)
- `python3 scripts/validation/check_zera_hardening.py --json` -> error: `Hermes profile contains potential inline secret token (openai)`
- `cd repos/packages/agent-os && uv run python ../../../scripts/reliability_orchestrator.py run --suite benchmark --json` -> failed (`benchmark-report` exit 2)
- `python3 repos/packages/agent-os/scripts/verify_trace_coverage.py --json` -> `ImportError: cannot import name 'materialize_metrics'`
- `cd repos/packages/agent-os && uv run python src/agent_os/workflow_model_alias_validator.py --json` -> `FileNotFoundError` (wrong repo root resolution)

## Key Findings (Severity Ordered)
### Critical
1. Inline secret in Hermes profile despite policy claiming env-only.
   - `~/.hermes/profiles/zera/config.yaml` contains raw key in `custom_providers[].api_key`.
   - Security governance is currently violated in live runtime state.
2. Governance gate is hard-failing in real run.
   - Governance suite cannot pass while Hermes profile remains non-compliant.
3. Benchmark suite is broken by missing executable target.
   - `configs/tooling/test_suite_matrix.yaml` points to `configs/tooling/analyze_benchmark.py`, but file is absent in workspace.

### High
1. Launcher drift: local `zera` command points to a different repo.
   - `/Users/user/.local/bin/zera` hardcodes `ROOT="/Users/user/antigravity-core"`.
   - This breaks predictability when auditing `/Users/user/zera` as canonical runtime.
2. Runtime-path inconsistency for Hermes.
   - `runtime_providers.json` has `hermes.enabled=false` while external Hermes profile is actively used.
   - Operational behavior and declarative control plane are partially diverged.
3. Workflow/trace validators are not executable in current shape.
   - `verify_trace_coverage.py` imports `materialize_metrics` from wrapper script that does not expose this symbol.
   - `workflow_model_alias_validator.py` computes wrong root (`parents[4]` -> `/Users/user/zera/repos`).

### Medium
1. Model drift between repo policy and active Hermes profile.
   - Repo models SoT defines Hermes default as local `ollama/qwen3.5:9b-q4_K_M`.
   - Active Hermes profile default is `openrouter/free` with smart routing enabled and cheap model override.
2. RU intent routing quality is weak in fallback mode.
   - For Russian objective (`"сделай аудит..."`) resolver falls back to `zera:plan` (`decision_reason: mode_router_fallback`, confidence `0.51`).
   - English governance phrase routes correctly to `zera:governance-check` (`confidence 0.98`).
3. Preflight noise from broken symlink inventory (`38`) degrades operational trust.

## Efficiency Assessment (Hermes + Zera)
- Governance reliability: **40/100** (hard fail in governance suite)
- Runtime coherence (SoT vs live): **55/100** (launcher + model + provider drift)
- Execution throughput: **70/100** (quick smoke passes when preflight bypassed; doctor passes with warnings)
- Benchmark observability quality: **35/100** (benchmark gate path broken; latest report stale and low confidence)

### Composite score: **50/100** (Needs immediate hardening before production-grade claims)

## Evidence Pointers
- `configs/tooling/runtime_providers.json`: `zeroclaw.enabled=true`, `hermes.enabled=false`
- `/Users/user/.local/bin/zera`: hardcoded root `/Users/user/antigravity-core`
- `~/.hermes/profiles/zera/config.yaml`: inline API key + policy contradiction
- `configs/orchestrator/models.yaml`: Hermes defaults (repo SoT)
- `configs/tooling/test_suite_matrix.yaml`: benchmark commands targeting missing `analyze_benchmark.py`
- `repos/packages/agent-os/scripts/verify_trace_coverage.py`: broken import target
- `repos/packages/agent-os/src/agent_os/workflow_model_alias_validator.py`: wrong `repo_root()` depth

## Recommended Remediation Plan
### Wave 1 (Immediate, 0-1 day)
1. Remove inline secrets from `~/.hermes/profiles/zera/config.yaml`, switch to env refs only.
2. Decide canonical launcher root; repoint `/Users/user/.local/bin/zera` to `/Users/user/zera` or document explicit split.
3. Restore benchmark executable path (add missing analyzer or update `test_suite_matrix.yaml` to existing entrypoint).

### Wave 2 (Stability, 1-2 days)
1. Fix `verify_trace_coverage.py` imports to use `agent_os.trace_metrics_materializer`.
2. Fix `workflow_model_alias_validator.py` root resolution.
3. Resolve/ignore broken symlink set used by preflight to stop false operational failures.

### Wave 3 (Effectiveness tuning, 2-4 days)
1. Align Hermes live profile with repo `models.yaml` (or update SoT to intentional OpenRouter-first policy).
2. Add Russian keyword map for `zera_mode_router` / registry inference.
3. Re-run governance + benchmark + doctor and publish fresh benchmark artifacts.

## Bottom Line
- `Hermes + Zera` is operational but **not yet governance-clean and benchmark-trustworthy** in current workspace state.
- Main blockers are **config/launcher drift + validation tooling breakage**, not core command runtime architecture.
