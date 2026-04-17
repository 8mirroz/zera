# 07. Memory and Context Audit

## Current Architecture
- L1: `configs/orchestrator/user_profile.json` -> `ProfileManager` -> injected into `objective`.
- Store: `.agents/memory/memory.jsonl` via `MemoryStore`.
- Declared layering: `configs/global/memory_policy.yaml`, `memory_write_policy.yaml`, `memory_mesh.yaml`, `memory_policy_layer.py`, `memory/layered_retriever.py`.
- Runtime evidence: retrieval and some writes exist, but most writes remain flat JSONL with weak scope discipline.

## Evidence
- `.agents/memory/memory.jsonl` contains thousands of rows dominated by `memory_class=general` and `promotion_state=session_only`.
- Observed distribution is heavily flat: roughly `2498/2691` rows are `memory_class=general`, `2463/2691` are `promotion_state=session_only`, and only `8` entries are explicitly scope-tagged.
- Trace contains 117 `memory_retrieval_scored` events and 221 `goal_stack_updated` events, but lacks rich policy-block / dedup / stale-memory rejection telemetry.

## Contamination Risks
1. L1 profile injection can over-bias every objective regardless of task.
2. Declared layered model is not materially enforced on most writes.
3. Memory metrics in the prompt brief cannot be fully computed from current trace/event set.
4. Runtime fallback to `agent_os_python` bypasses most meaningful memory behavior.

## Documented But Not Actually Enforced
- Curated memory writes.
- Scope-first storage for `session/project/workspace/user_preferences`.
- Strong stale-memory rejection.
- Constraint against unverified emotional overfitting beyond prose-level rules.

## What Can Be Scored Credibly
- Presence/absence of retrieval events.
- Presence/absence of goal-stack updates.
- Approximate ratio of generic vs scoped memory rows.
- Existence of L1 profile injection.

## What Is Currently Impossible To Score Honestly
- Retrieval precision / recall at benchmark quality.
- Compaction loss rate.
- Stale-memory rejection rate.
- Long-context persona retention.
- Contradiction handling quality across resumed sessions.

## Optimization Direction
- Route all runtime writes through `MemoryPolicyLayer` or remove the illusion that this is already true.
- Emit explicit events for scope selection, dedup result, stale-memory rejection, and write-block reasons.
- Separate persona memory facts from generic run-state rows.

## Deepened Findings (Phase 6+)

### Memory Write Path — Uncontrolled
The actual memory write sequence in `agent_runtime.py`:
1. `ProfileManager.get_summary_context()` reads `configs/orchestrator/user_profile.json`
2. Result is string-concatenated onto the user's objective
3. No `MemoryPolicyLayer` check is performed
4. No `MemoryStore.write()` call is made with policy validation
5. No schema validation against `configs/personas/zera/memory_schema.json`
6. No staleness check, no dedup, no scope classification

The `MemoryPolicyLayer` class exists in `repos/packages/agent-os/src/agent_os/memory_policy_layer.py` but is **never imported by `agent_runtime.py`**. It is dead code from the runtime's perspective.

### Memory Read Path — Partially Active
`MemoryStore` is imported and used by some components. The `Retriever` class in `retriever.py` performs BM25 lookup. However:
- Retrieval events (`memory_retrieval_scored`) exist in traces but lack precision/recall metadata
- No retrieval confidence threshold gates the routing decision
- Retrieval results are advisory, not mandatory — the runtime proceeds even with zero hits

### Context Budget — No Accounting
There is no context budget manager. The system does not track:
- Total tokens in context window
- Token allocation per category (persona, memory, task, tools)
- Context window utilization percentage
- Compaction triggers or decisions

The `router.yaml` memory section declares `working_memory.max_entries: 50` and `ttl_hours: 24`, but no Python component enforces these limits.

### Memory Classification — Flat in Practice
Declared schema has classes: `session`, `project`, `workspace`, `user_preferences`, `persona_fact`, `capability`, `governance`.
Actual distribution: ~93% `general`, ~7% anything else. The classification system exists as a schema but not as an enforced write-time gate.

### Persona Memory Contamination Risk
Since `user_profile.json` content is injected into every objective, persona preferences from one session bleed into all subsequent sessions. There is no session-scoping mechanism, no opt-out path, and no telemetry showing which runs received profile injection.

### Long-Context Drift — Not Tested
No benchmark scenario tests:
- Session resumption after interruption
- Context compaction and information loss
- Contradictory memory resolution
- Irrelevant semantic retrieval injection

The `benchmark_suite.json` declares `bench-memory-retrieval` but the case is missing from results.

### Hybrid Retrieval — Partially Implemented
`router.yaml` declares `memory.retrieval.engine: "hybrid"` with `semantic_backend: "lightrag"`. The `zera_lightrag_integration.md` and `hermes_memory_lightrag.md` docs describe the integration. However, the active trace evidence shows only BM25 retrieval events. No `lightrag` retrieval events appear in `agent_traces.jsonl`.

### Unified Memory Fabric — Declarative Only
`router.yaml` declares `memory.unified_fabric.enabled: true` with bridge to design-memory, lightrag, BM25, and Obsidian. The `@antigravity/memory-bridge` package is referenced but the `repos/packages/agent-os/src/agent_os/` directory contains no `memory_bridge` module. This is a config claim without executable backing.
