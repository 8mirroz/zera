# 13. Root Cause Analysis

## RC-1. Declarative surface area exceeds executable enforcement
- Symptom: configs and docs promise more than runtime actually does.
- Root cause: large policy/config corpus was added faster than code consumers and validators.
- Affected nodes: `configs/tooling/*`, `configs/personas/zera/*`, `RuntimeRegistry`, `persona_eval.py`, workflow catalogs.
- Severity: critical.
- User impact: misleading operator confidence and false maturity signals.
- Recommended fix: reduce or validate every declarative surface against live consumers.

## RC-2. Success signals are emitted too early and too optimistically
- Symptom: selected provider and verification appear healthy even when execution is missing or degraded.
- Root cause: telemetry semantics conflate “selected”, “completed”, and “verified”.
- Affected nodes: `agent_runtime.py`, `agent_os_python.py`, `observability.py`, benchmark analyzer.
- Severity: high.
- Recommended fix: split runtime lifecycle states and hard-fail unverifiable completion.

## RC-3. Benchmark analyzer lacks identity normalization and anomaly penalties
- Symptom: gate passes with contradictory suite diagnostics.
- Root cause: raw `case_id` comparison plus total-case coverage arithmetic.
- Affected nodes: `analyze_benchmark.py`, `benchmark_latest.*`.
- Severity: critical.
- Recommended fix: normalize canonical case IDs, separate repeats/sample cases, and fail on missing canonical IDs.

## RC-4. Repo policy and operator-side active state are not reconciled continuously
- Symptom: Hermes/Gemini parity drift and extra cron sidecars.
- Root cause: sync scripts are advisory; no blocking parity doctor.
- Affected nodes: `scripts/hermes-sync-config.sh`, home profile files.
- Severity: medium.
- Recommended fix: add blocking parity healthcheck and canonical export/import discipline.

## RC-5. Persona documents are governance artifacts, not runtime inputs
- Symptom: Zera's constitution, identity, tone, safety, and relationship boundaries exist as well-written markdown files but are never loaded by the Python runtime.
- Root cause: `ZeraCommandOS.render_prompt()` injects command metadata headers, not persona content. The persona docs influence behavior only if the operator manually includes them in the LLM system prompt via external Hermes/Gemini profiles.
- Affected nodes: `configs/personas/zera/*.md`, `ZeraCommandOS`, `agent_runtime.py`, Hermes/Gemini profile configs.
- Severity: critical for persona integrity claims.
- User impact: persona behavior depends on external operator discipline, not runtime guarantees.
- Recommended fix: either (a) load persona docs into the runtime prompt assembly pipeline, or (b) demote them from "runtime contract" to "operator reference" and adjust all claims accordingly.

## RC-6. Memory policy layer exists but is bypassed by the runtime
- Symptom: `MemoryPolicyLayer`, `memory_schema.json`, `memory_write_policy.yaml` define a rich memory governance system. `agent_runtime.py` never imports or calls any of them.
- Root cause: memory write path uses direct `ProfileManager` string injection into objectives, bypassing all policy gates.
- Affected nodes: `agent_runtime.py`, `memory_policy_layer.py`, `MemoryStore`, `user_profile.json`.
- Severity: high for memory discipline and persona contamination risk.
- User impact: persona preferences bleed across sessions without scoping, dedup, or staleness checks.
- Recommended fix: route all memory reads/writes through `MemoryPolicyLayer` or remove the layered memory claims from config.

## RC-7. Benchmark system produces contradictory signals
- Symptom: benchmark reports `score=0.7756, pass_rate=0.875, gate=pass` while all 13 expected cases are missing and 120 cases are repeats/samples.
- Root cause: `analyze_benchmark.py` counts total cases for coverage arithmetic but compares raw case IDs (with `::rN` suffixes) for expected-case matching. This means 5 repeats of the same case count as 5 different cases for coverage but 0 for expected matching.
- Affected nodes: `analyze_benchmark.py`, `benchmark_latest.json`, `benchmark_anomalies.json`, `benchmark_gate.json`.
- Severity: critical — blocks all release gating decisions.
- User impact: operators cannot trust benchmark results to make go/no-go decisions.
- Recommended fix: normalize case IDs by stripping `::rN` suffixes, separate canonical cases from sample/replay traces, fail gate on missing canonical IDs regardless of raw score.

## RC-8. Motion-aware routing config surface has zero executable backing
- Symptom: `router.yaml` contains a full `motion_awareness` block with GSAP/Framer/CSS triggers, skill assignments, workflow paths, and quality gates. None of the referenced files exist.
- Root cause: config was written as a design specification but no implementation was built. The config is consumed by no Python component.
- Affected nodes: `router.yaml` motion_awareness block, `configs/capabilities/gsap_motion.yaml` (missing), `.agent/skills/gsap-*.md` (not published).
- Severity: medium — not actively harmful but creates false capability expectations.
- User impact: task descriptions containing motion keywords get no special handling despite config promising GSAP/Framer routing.
- Recommended fix: either implement the motion awareness pipeline or remove the config block to eliminate false expectations.

## RC-9. Registry workflow resolution silently fails
- Symptom: `AgentRuntime._registry_workflow_context_for_route()` always returns `None` because `configs/registry/` does not exist.
- Root cause: the method catches `Exception` and returns `None`. No telemetry is emitted. The caller does not check for `None`.
- Affected nodes: `agent_runtime.py`, `registry_workflows.py`, `configs/registry/` (missing).
- Severity: medium — silent capability loss.
- User impact: tasks that should receive workflow context proceed without it, with no visibility.
- Recommended fix: emit a `registry_workflow_missing` warn event when the directory is absent, or remove the call path entirely.

## RC-10. Persona governor and self-evolution lack runtime integration
- Symptom: `ZeraCommandOS.evaluate_governor()` implements personality axis governance with freeze/rollback. `self_evolution_loop.py` modifies persona configs. Neither is called or gated by the runtime.
- Root cause: governance methods exist as APIs but have no callers in the execution path. Self-evolution operates as an external script.
- Affected nodes: `zera_command_os.py::evaluate_governor`, `self_evolution_loop.py`, `zera_growth_governance.json`.
- Severity: high for long-session persona drift risk.
- User impact: Zera's personality can evolve without runtime governance checks, axis delta monitoring, or rollback triggers.
- Recommended fix: call `evaluate_governor()` at persona config load time, gate self-evolution changes through a review pipeline.
