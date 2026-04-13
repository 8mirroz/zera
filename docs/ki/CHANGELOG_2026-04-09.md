# Changelog

## 2026-04-09 - Migration Remediation + Hardening (Antigravity v5)

### Critical fixes
- Fixed `scripts/run_quality_checks.sh` root resolution and profile normalization.
- Added preflight call (`scripts/system_health_check.sh --quick`) into quality entrypoint.
- Restored NotebookLM runtime on ARM-native Python 3.12 and updated `configs/tooling/notebooklm_integration.json` (`python_bin`).
- Switched `uv` to ARM-native binary and rebuilt `repos/packages/agent-os/.venv` on ARM.
- Converted workspace git metadata from external worktree pointer to local `.git/` directory.
- Fixed `.agent/workflows` broken migration path and committed stabilization:
  - `659a493` - `fix: stabilize workflows after migration`

### Stabilization
- Published skills and reduced false-positive skill drift by updating:
  - `repos/packages/agent-os/scripts/skill_drift_validator.py`
- Enabled real `qmd` backend for wiki-core (no TF-IDF fallback in doctor):
  - validated via `swarmctl wiki doctor`.
- Removed broken symlink:
  - `sandbox/importers/repos/rjmurillo/memory_enhancement`
- Replaced legacy rename residue `antigravity-core-v5-refactor` in docs/log/report trees.

### Hardening
- Added runtime health gate:
  - `scripts/system_health_check.sh` (`--quick`, `--json`).
- Added deterministic bootstrap script:
  - `scripts/bootstrap_env.sh`.
- Added preflight guard to workflow command bridge:
  - `scripts/zera-command.sh`.
- Standardized dynamic repo-root resolution in scripts:
  - `scripts/hermes-sync-config.sh`
  - `scripts/hermes-dashboard.sh`
  - `scripts/hermes_consolidate_profiles.sh`
  - `scripts/zera-obsidian-integration.sh`
  - `scripts/zera-autonomous-launcher.sh`
- Removed hardcoded absolute repo paths in runtime/helpers:
  - `configs/tooling/trace_collector.py`
  - `scripts/test_mcp_profiles.py`
  - `configs/tooling/mcp_profiles.json`
  - `configs/tooling/qwen_context_agent.json`
  - `repos/packages/agent-os/scripts/mcp_profile_consistency_checker.py`
- Added explicit dependency required by quality orchestration:
  - `repos/packages/agent-os/pyproject.toml` (`PyYAML`)
  - updated `repos/packages/agent-os/uv.lock`.
