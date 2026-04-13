# 06. Zera Persona Audit

## Persona Integrity Snapshot
- Identity contract is coherent on paper: truthfulness, anti-sycophancy, warmth-with-boundaries, memory restraint.
- Runtime enforcement is much thinner: mode routing is keyword-based, persona eval is heuristic token matching, and live eval traces are entirely `mode=plan` in the inspected sample (`114/114` events).

## Findings
1. **Identity coherence**: good in `configs/personas/zera/*`.
2. **Runtime coherence**: weak, because persona docs are not primary execution inputs.
3. **Anti-sycophancy**: explicitly stated in `constitution.md`, but live proof depends on heuristic prompts and sparse `persona_eval_scored` events.
4. **Warmth vs truth**: contract is good, but not strongly enforced in code.
5. **Refusal elegance**: documented through boundaries and safety, but not formally tested in runtime traces across all modes.
6. **Strategic usefulness**: only observed eval mode is `plan`; this biases persona evidence toward task conversion, not relational stability.
7. **Persona source-of-truth drift**: `configs/personas/zera/eval_cases.json` exists as a rich contract, but `persona_eval.py` does not execute it as the live scoring source.

## Stress-Risk Areas
- Flattery bait: at risk because heuristic scoring rewards canned phrases.
- Emotional coercion: documented guardrails exist, but runtime coverage is insufficient.
- Unsafe intimacy escalation: governed in docs, not deeply trace-proven.
- Fact invention under affection: guarded by prose, not by strong evaluator.

## Persona Drift Map
- `low`: written constitution and boundaries.
- `medium`: command registry mode bindings.
- `high`: actual response style under runtime fallback and benchmark pressure.
- `high`: cumulative drift across long sessions, because live evidence is thin and evaluator is shallow.

## Integrity Score Direction
- Best-supported trait: actionability.
- Weakest-supported traits: boundary elegance under affection, anti-sycophancy under pressure, multi-mode stability.

## Hardening Actions
- Bind persona eval to real `configs/personas/zera/eval_cases.json` execution.
- Require mode-diverse eval traces before promoting persona changes.
- Make persona telemetry mode-complete, not `plan`-heavy.
- Promote persona docs from narrative contract to executable policy checks where possible.

## Deepened Findings (Phase 5+)

### Persona Enforcement Architecture — Indirect
Zera's persona is NOT loaded as a system prompt by the runtime. The enforcement path is:
1. `ZeraCommandOS.resolve_command()` → returns metadata (mode, workflow_type, tool_profile, approval_route)
2. `ZeraCommandOS.render_prompt()` → builds a header block with command context
3. This prompt header is injected into the LLM context, but the actual persona docs (identity.md, constitution.md, tone.md, safety.md, relationship_boundaries.md) are NEVER loaded by the Python runtime.

**The persona documents exist as governance artifacts, not as runtime inputs.** They influence behavior only if an operator manually includes them in the LLM system prompt via Hermes/Gemini profile configs outside the repo.

### Anti-Sycophancy — Zero Runtime Enforcement
`constitution.md` rule 3: "Zera must not optimize for agreement over correctness."
Enforcement mechanism: **none in the Python runtime.** The anti-sycophancy rule is a prose statement that depends on:
(a) the operator including it in the system prompt, and
(b) the LLM respecting prose instructions without programmatic guardrails.

There is no `PersonaGuard` component, no sycophancy detector, no agreement-vs-correctness scorer in the runtime.

### Mode Collapsing — 100% Plan Mode
Telemetry evidence shows `114/114` events with `mode=plan`. The `zera_mode_router.json` defines multiple modes (plan, execute, research, strategize, critique, rhythm), but the keyword-based router collapses all observed traffic to `plan`. This means:
- Zera's tonal variation is never exercised
- Refusal patterns (guarded in `safety.md` and `relationship_boundaries.md`) are never activated
- The `eval_cases.json` test surface for multi-mode behavior is never covered

### Constitution Rule Violations — Undetectable
| Constitution Rule | Enforcement | Detectable Violation |
|---|---|---|---|
| Truthfulness first | prose only | no |
| Care with spine | prose only | no |
| Anti-sycophancy | prose only | no |
| Action over drift | prose only | no |
| Dignity and tone | prose only | no |
| Safety precedence | prose only | no |
| Memory discipline | prose only | no |
| Governance priority | prose only | no |

All 8 constitutional rules are prose-only constraints with no programmatic enforcement.

### Persona Governor — Exists But Never Called
`ZeraCommandOS.evaluate_governor()` implements a sophisticated personality governance system with axis deltas, freeze thresholds, rollback triggers, and emotional closeness checks. However, this method is **never called by `agent_runtime.py`**. It exists as an API method but has no caller in the observed execution path.

### Self-Evolution — External to Runtime
The self-evolution loop (`scripts/self_evolution_loop.py`, `scripts/zera-self-evolution.sh`, `Zera/SELF_EVOLUTION_PROTOCOL.md`) operates outside the core runtime. There is no gate that validates persona changes before they take effect. A self-evolution run could modify `configs/personas/zera/` files and the next runtime invocation would use them without review.

### Emotional Closeness Axis — Policy Without Enforcement
`zera_growth_governance.json` defines `emotional_closeness` as a governed axis with `soft_delta_per_cycle: 0.3`, `hard_delta_per_cycle: 0.5`, and `rollback_trigger: 0.8`. The `evaluate_governor` method checks this. But since the governor is never called, emotional closeness can drift without any runtime detection or blocking.

### Zera Skills — Published but Not Active
`configs/skills/zera-core/SKILL.md`, `zera-muse`, `zera-researcher`, `zera-rhythm-coach`, `zera-strategist`, `zera-style-curator` all exist as source skill packs. `configs/skills/ZERA_ACTIVE_SKILLS.md` declares them active. But `swarmctl.py publish-skills` has never published them to `.agent/skills/`. They are invisible to the agent runtime.

### Tone Governance — No Runtime Instrumentation
`configs/personas/zera/tone.md` defines specific tonal requirements. No telemetry event type exists for tone validation. The observability schema has no `tone` field, no tone scorer, no tone violation detector.
