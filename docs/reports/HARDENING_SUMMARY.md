# HARDENING_SUMMARY

Date: 2026-04-09

## Architectural Improvements Implemented

## 1. Runtime Validation Layer
- Added `scripts/system_health_check.sh`.
- Coverage:
  - repo root + git integrity
  - host/runtime architecture (`arm64`)
  - canonical Python runtime (`>=3.11`, executable, arm64)
  - NotebookLM doctor status
  - qmd availability
  - broken symlink detection
  - basic env consistency check
- Modes:
  - `--quick` for preflight
  - `--json` for machine-readable checks

## 2. Deterministic Environment Layer
- Added `scripts/bootstrap_env.sh`:
  - installs/validates Homebrew Python 3.12 and `uv`
  - installs `qmd`
  - creates NotebookLM venv and installs pinned dependencies
  - updates notebooklm integration config
  - publishes active skills
- Existing `.env.example` remains canonical env template.

## 3. Path Resolution Standard
- Standardized repo-root resolution pattern in operational scripts.
- Removed hardcoded absolute repo path usage in critical tooling/runtime files.
- Updated MCP/Qwen config paths from fixed username paths to `${HOME}`-based paths for portability.

## 4. Preflight Guard
- Added quick preflight checks before execution in:
  - `scripts/run_quality_checks.sh`
  - `scripts/zera-command.sh`
- Guard is skippable only via explicit `AG_SKIP_PREFLIGHT=1`.

## 5. Dependency/Tooling Reliability
- Added `PyYAML` to `repos/packages/agent-os/pyproject.toml` (required by reliability orchestrator).
- Synced lockfile (`uv.lock`) to keep environment reproducible.

## 6. Workflow and Registry Stability
- Workflow path migration fix already committed (`659a493`).
- Skill drift validator normalized to avoid false positives on optional/internal skill refs.

## Operational Outcome

- Core quality/doctor/smoke pipeline is runnable on ARM-native environment.
- System start checks are now explicit and fail-fast.
- Migration-related path/architecture regressions are largely contained.

## Recommended Next Hardening Steps

1. Close governance debt causing `check_zera_hardening.py` failure in quality profile.
2. Finish NotebookLM auth bootstrap for local smoke e2e.
3. Remove remaining legacy-compat warnings by finalizing routing/model-router migration tail.
