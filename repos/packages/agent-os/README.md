# Agent OS v2 (Runtime + Tooling)

Минимальный набор утилит и контрактов для Agent OS v2:
- публикация Active Skills в `.agents/skills/`
- `doctor` проверки целостности конфигов/скиллов
- `triage` и `route` для model routing
- smoke/integration/regression проверки
- контракты `ModelRouter`, `Agent`, `Tool`, `Retriever`, `MemoryStore`, `CodeEditor`

## Requirements
- Python `3.12.x`
- Node `22.x` (для app layer и mcp-profile-manager)

## Bootstrap
```bash
bash repos/packages/agent-os/scripts/bootstrap_env.sh
```

## Core commands
```bash
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills
python3 repos/packages/agent-os/scripts/swarmctl.py doctor
python3 repos/packages/agent-os/scripts/swarmctl.py triage "поправь опечатку в README"
python3 repos/packages/agent-os/scripts/swarmctl.py route "fix auth bug" --task-type T2 --complexity C4
python3 repos/packages/agent-os/scripts/swarmctl.py run "validate routing and memory contracts"
```

## Validation commands
```bash
bash repos/packages/agent-os/scripts/run_smoke_checks.sh
bash repos/packages/agent-os/scripts/run_integration_tests.sh
python3 repos/packages/agent-os/scripts/run_regression_suite.py
```

## Memory backend (JSONL vs memU Cloud)
`MemoryStore` uses local JSONL by default. You can enable a hybrid memU Cloud backend via env flags:

```bash
# Default (backward compatible)
export MEMORY_BACKEND=jsonl

# Optional memU Cloud hybrid:
# - write/read stay local-compatible (JSONL source of truth for exact key reads)
# - search is enriched with memU Cloud results
export MEMORY_BACKEND=memu_cloud
export MEMU_API_KEY=your_memu_api_key
export MEMU_BASE_URL=https://api.memu.so
export MEMU_USER_ID=antigravity-core
export MEMU_AGENT_ID=agent-os-memory-store
export MEMU_HTTP_TIMEOUT_SECONDS=5
export MEMU_FAIL_OPEN=true
```

Notes:
- `MEMU_FAIL_OPEN=true` keeps local JSONL behavior if memU init/search fails.
- No `memu-py` dependency is required in `agent-os`; integration uses stdlib HTTP calls.

## Notes
- `ROUTER_MODE=legacy` переключает route на `.agents/config/model_router.yaml`.
- Optional adapters (`autogen`, `gpt-engineer`, `letta`) выключены по умолчанию и управляются через env флаги.
