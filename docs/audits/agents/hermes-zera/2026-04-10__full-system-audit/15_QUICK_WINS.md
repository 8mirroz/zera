# 15. Quick Wins

## Critical (Do First)
1. **Fix benchmark case identity normalization** — strip `::rN` suffixes before matching expected cases; fail gate on missing canonical IDs regardless of raw score. (`analyze_benchmark.py`)
2. **Make `test_mcp_profiles.py` exit non-zero** on any routing mismatch or missing parity surface. Current exit-0-on-failure is a critical credibility breach.
3. **Change `agent_os_python` verification status** from `status=ok` to `status=not-run` or `status=warn`. Stop success-washing unverifiable completions.
4. **Add provider registration contract test** — every enabled provider in `runtime_providers.json` must have a factory in `RuntimeRegistry._builtin_factories`. Currently `mlx_lm` is declared but impossible.

## High Priority (Do This Week)
5. **Add workflow existence validation** — `test_workflow_catalog_paths_exist` should fail if `.agents/config/workflow_sets.active.json` references missing files.
6. **Flag `real-trace-*` cases as non-canonical** — exclude from coverage arithmetic; label as sample/replay inputs.
7. **Remove or archive `configs/tooling/model_routing.json.DEPRECATED`** — deprecated files in config paths create confusion.
8. **Remove orphan config files** — `eggent_algorithm_matrix.json`, `polyglot_execution_matrix.json`, `notebooklm_agent_router_templates.json`, `suite_manifest.json`, `plugin_schema.json`, `repo_aliases_policy.json` have no consumers.
9. **Emit `registry_workflow_missing` warn event** when `configs/registry/` is absent — stop silent no-op.
10. **Add telemetry for pre-flight catalog update** — current `except Exception: pass` swallows all failures invisibly.

## Medium Priority (Do This Sprint)
11. **Add Hermes/Gemini parity doctor** — `swarmctl.py doctor` should diff repo configs against `~/.hermes/profiles/` and `~/.gemini/antigravity/`.
12. **Document or quarantine external cron** — `~/.hermes/profiles/zera/cron/jobs.json` operates outside repo governance.
13. **Add `persona_docs_loaded` telemetry event** — prove whether `configs/personas/zera/*.md` content reaches the LLM context.
14. **Add context budget tracking** — emit `context_budget_exceeded` warn event when objective + profile + memory injection exceeds safe thresholds.
15. **Publish Zera skills** — run `swarmctl.py publish-skills` for `zera-core`, `zera-muse`, `zera-researcher`, `zera-rhythm-coach`, `zera-strategist`, `zera-style-curator`.
