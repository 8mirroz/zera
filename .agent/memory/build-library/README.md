# Build Memory Library (Global + Project)

Purpose: shared memory library for the most effective builds, settings combinations,
algorithms, and execution playbooks used by Antigravity agents.

Goals:
- Reuse proven solutions across agents and sessions
- Separate global best practices from project-specific optimizations
- Preserve evidence (metrics, traces, KI links) for each entry
- Support deterministic query/filtering for planners and orchestrators

Structure:
- `global/entries/` : reusable cross-project entries
- `projects/<project-slug>/entries/` : project-scoped entries
- `indexes/` : generated indexes and top-ranked snapshots
- `templates/` : JSON templates for new entries

Rules:
- No secrets in entries
- Prefer evidence-backed entries (trace/KI/pattern references)
- Use `status` lifecycle: `candidate` -> `validated` -> `gold`
- Keep one entry = one coherent build/combination/pattern

Recommended tooling:
- `python3 repos/packages/agent-os/scripts/build_memory_library.py rebuild-index`
- `python3 repos/packages/agent-os/scripts/build_memory_library.py query --text "telegram free-first"`

