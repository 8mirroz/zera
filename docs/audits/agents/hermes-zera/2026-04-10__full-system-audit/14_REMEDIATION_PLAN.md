# 14. Remediation Plan

## Immediate Safe Fixes
- Fail `scripts/test_mcp_profiles.py` on any routing mismatch or missing required parity surface.
- Add unit test that every enabled provider in `runtime_providers.json` is registered in `RuntimeRegistry`.
- Make benchmark gate fail if canonical expected IDs are missing, regardless of raw score.
- Add workflow existence validation for all `.agents/workflows/*` references.
- Mark `agent_os_python` output as simulated/unverified instead of normal completion.

## Medium Structural Fixes
- Bind `persona_eval.py` to real `configs/personas/zera/eval_cases.json` rubrics.
- Route runtime memory writes through `MemoryPolicyLayer`, or remove false layered-memory claims.
- Add Hermes/Gemini/Zera cron parity doctor.
- Collapse trace sink duplication and enforce one canonical trace ledger.

## Deep Architecture Refactors
- Replace keyword-only mode routing with richer policy-aware selection.
- Build a true provider lifecycle state machine with distinct readiness/execution/verification outcomes.
- Separate benchmark replay/sample traces from canonical suite cases.
- Convert high-value persona/memory governance rules into executable contracts.

## Optional Advanced Upgrades
- Add reproducible audit harness that writes all diagnostic outputs into one audit-local store.
- Add benchmark provenance tags for synthetic vs replay vs live runtime cases.
- Add long-session persona/memory eval corpus and replay runner.
