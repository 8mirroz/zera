# 03. Source-of-Truth Analysis

## Итог
- Для `zera:*` command semantics SoT достаточно ясен: `configs/tooling/zera_command_registry.yaml` + `zera_client_profiles.yaml`.
- Для runtime provider dispatch SoT формально split между `configs/tooling/runtime_providers.json` и `RuntimeRegistry`, но код имеет больший приоритет, потому что часть config surface не потребляется.
- Для workflow/orchestration SoT в живом runtime не `WorkflowRouter`, а `configs/orchestrator/router.yaml` через `RegistryWorkflowResolver`.
- Для persona и memory SoT частично narrative: persona pack богатый, но enforcement минимальный; layered memory policy задекларирован сильнее, чем реально исполняется.

## Drift Matrix
| Область | Intended SoT | Real SoT | Drift |
|---|---|---|---|
| Zera command semantics | `configs/tooling/zera_command_registry.yaml` | same | low |
| Client capability rules | `configs/tooling/zera_client_profiles.yaml` | only `clients.*.capabilities` slice | medium |
| Runtime providers | `configs/tooling/runtime_providers.json` | `RuntimeRegistry` code + consumed subset of config | high |
| Workflow routing | `WorkflowRouter` / workflow sets docs | `configs/orchestrator/router.yaml` + `RegistryWorkflowResolver` | high |
| Persona contract | `configs/personas/zera/*` | mostly `zera_mode_router.json` + heuristics in `persona_eval.py` | high |
| Memory policy | `configs/global/memory_policy.yaml` + `memory_write_policy.yaml` | `ProfileManager` injection + raw `MemoryStore` JSONL path | high |
| Benchmark truth | `benchmark_suite.json` + analyzer | analyzer output in `docs/ki/benchmark_latest.json`, but semantics broken | critical |
| Observability | `trace_schema.json` | `observability.py` + actual emitted events | high |

## Ambiguity Matrix
| Узел | Почему ambiguous |
|---|---|
| `configs/tooling/runtime_providers.json` | Declares `mlx_lm`, but `RuntimeRegistry` cannot instantiate it. |
| `configs/tooling/zera_client_profiles.yaml` | Top-level parity/transport semantics are mostly declarative in this path. |
| `configs/personas/zera/prompt_assembly.yaml` | Describes assembly order, but no direct runtime consumer found in main path. |
| `.agent/config/workflow_sets.active.json` | Rich orchestration catalog exists, but required `.agent/workflows/*.md` assets are absent. |
| `docs/guides/hermes-agent-integration-guide.md` | Describes Hermes integration against a different workspace and broader capability surface than current repo-proven path. |

## Priority Conflicts
1. `runtime_providers.json` vs `RuntimeRegistry`: code wins; config can silently overclaim.
2. `trace_schema.json` vs actual trace stream: emitted events win; schema is stale.
3. Persona docs vs `persona_eval.py`: heuristic scorer wins in live telemetry.
4. Benchmark gate vs benchmark anomalies: gate currently wins automatically, but anomalies prove that this is wrong.

## Canonical Defaults Chosen For This Audit
- Runtime truth beats narrative docs.
- Code consumer beats config producer when a field is not consumed.
- Trace evidence beats dashboard summary when they disagree.
- Historical benchmark artifacts are evidence only, not trusted verdicts.
