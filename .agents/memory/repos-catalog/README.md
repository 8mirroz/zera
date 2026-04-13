# Repo Memory Catalog (Fast Navigation for Agents)

Purpose: fast, structured memory index for repositories under `repos/` with deterministic aliases.

Goals:
- Fast navigation for all agents (planner/orchestrator/workers)
- Stable aliases for repo references in prompts, traces, and memory
- Prioritized catalog for free/fast solution discovery
- Sync into `.agent/memory/memory.jsonl` for cross-session recall

Index files:
- `indexes/repos_index.json` : full repo records
- `indexes/aliases_index.json` : alias -> repo mapping
- `indexes/navigation_shortcuts.json` : optimized shortcut lists
- `indexes/validation_report.json` : collisions / warnings

Alias levels:
- `path_alias` (readable): `r/<domain>/<slug>`
- `compact_alias` (fast): `<domain_code>:<short>`
- `stable_key` (machine): `repo_catalog:repo:<domain>:<slug>`

Refresh command:
```bash
python3 repos/packages/agent-os/scripts/repo_memory_catalog.py refresh --sync-memory
```

