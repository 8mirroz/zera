# MIGRATION_FIX_REPORT

Date: 2026-04-09
Scope:
- migration to new `antigravity-core`
- transition Intel -> Apple Silicon

## What Was Broken

1. Quality entrypoint failed due broken root assignment.
2. NotebookLM integration used inconsistent Python runtime and failed health.
3. `uv`/Python stack had mixed architecture and stale x86 artifacts.
4. Repository metadata depended on external worktree path.
5. Workflow links and migration paths were stale after rename.
6. Skill drift produced unstable/false-positive warnings.
7. Wiki-core used fallback behavior instead of validated semantic backend.
8. Broken symlink existed in importer subtree.
9. Multiple scripts/configs had hardcoded absolute paths reducing portability.

## What Was Fixed

### 1) Quality runner
- Fixed `scripts/run_quality_checks.sh`:
  - deterministic root resolution (`git` or script-relative fallback)
  - mode normalization (`pre-commit` -> `pre_commit`)
  - explicit preflight health execution
  - strict shell mode (`set -euo pipefail`)

### 2) NotebookLM integration
- Canonical runtime set to ARM Python 3.12 venv.
- Installed `notebooklm-py[browser,cookies]==0.3.4` + Playwright.
- Updated `configs/tooling/notebooklm_integration.json` with absolute canonical `python_bin`.
- Validated with `notebooklm-doctor` -> `status: pass`.

### 3) ARM-native runtime
- Replaced `uv` with ARM-native binary and linked into `~/.local/bin/uv`.
- Removed stale x86 uv-managed Python installations.
- Recreated `repos/packages/agent-os/.venv` on ARM Python 3.12.

### 4) Git stabilization
- Replaced `.git` worktree link-file with local `.git/` metadata directory.
- Repository no longer depends on external backup/worktree path.

### 5) Workflow stabilization
- Fixed `.agents/workflows` migration path and committed:
  - `659a493` `fix: stabilize workflows after migration`

### 6) Skill drift
- Updated `skill_drift_validator.py` to treat known optional/internal refs correctly.
- `skill_drift_validator.py --json` now returns `severity: ok`.

### 7) qmd/wiki
- Installed `qmd` and verified wiki doctor uses `active_backend: qmd`.

### 8) Symlink hygiene
- Removed broken symlink under importer subtree.
- Health check confirms `broken_symlinks_ok`.

### 9) Path portability and hardening
- Added new health gate: `scripts/system_health_check.sh`.
- Added deterministic setup: `scripts/bootstrap_env.sh`.
- Introduced repo-root resolution in multiple scripts.
- Removed hardcoded repo path in trace and test utilities.
- Updated policy config paths to `${HOME}`-based format where appropriate.

## Risks Removed

- Removed failure mode where quality runner crashed on malformed `ROOT`.
- Removed architecture mismatch risk for NotebookLM and `uv`.
- Removed catastrophic dependency on external worktree location.
- Removed silent failures from broken symlink artifacts.
- Reduced config/script portability risk from hardcoded absolute paths.

## Remaining Gaps

- NotebookLM smoke still requires operator auth bootstrap (`notebooklm login` or `NOTEBOOKLM_AUTH_JSON`).
- Governance bucket failure in quality (`check_zera_hardening.py`) remains and needs separate governance cleanup.
- Legacy compatibility warnings in doctor remain by design until migration tail is fully removed.
