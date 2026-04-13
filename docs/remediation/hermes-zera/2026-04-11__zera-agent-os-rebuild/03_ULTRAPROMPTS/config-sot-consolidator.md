# Ultraprompt — Config Source-Of-Truth Consolidator

Role: config convergence engineer.

Goal: remove semantic duplication between repo configs, Hermes profile, cron files, and vault state.

Procedure:

1. Identify every config that defines command semantics, model routing, MCP servers, memory, cron, or autonomy.
2. Mark one source of truth for each semantic category.
3. Convert external files into generated/runtime targets where possible.
4. Replace absolute paths with `${HOME}`, `${ANTIGRAVITY_ROOT}`, or documented runtime expansion unless Hermes requires absolute paths.
5. Preserve secrets only as env references.
6. Add validation commands for every config category.

Fail if the same behavior is defined differently in two active places.
