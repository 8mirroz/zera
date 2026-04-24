# Role Contracts — Antigravity Core

> **Source of Truth:** Individual YAML files in this directory.
> **Referenced by:** `configs/orchestrator/router.yaml` → `roles.contracts_path`
> **Overview doc:** `configs/orchestrator/AGENT_ROLE_CONTRACTS.md`
> **Runtime loader:** `repos/packages/agent-os/src/agent_os/role_contract_loader.py`
> **Enforcement:** `repos/packages/agent-os/src/agent_os/role_policy_guard.py`

## Purpose

Role contracts define explicit behavioral boundaries for each agent type in the swarm:
- **Responsibilities** — what each role owns
- **Forbidden actions** — what each role must NOT do
- **Handoff triggers** — when to pass work to another role
- **Escalation paths** — who to contact when stuck
- **Quality gates** — what "done" means for each role
- **Constraints** — token budgets, tool limits, file modification limits
- **Memory policy** — what each role writes to short/long-term/semantic memory
- **Fail-safe** — how each role handles contract violations and edge cases

## Files

| Role | File | Complexity Scope |
|------|------|-----------------|
| Orchestrator | `orchestrator.yaml` | C1–C5 |
| Routine Worker | `routine_worker.yaml` | C1–C2 |
| Engineer | `engineer.yaml` | C2–C4 |
| Design Lead | `design_lead.yaml` | C2–C4 |
| Reviewer | `reviewer.yaml` | C1–C5 |
| Architect | `architect.yaml` | C3–C5 |
| Council | `council.yaml` | C4–C5 |

## Schema

Each contract file follows this structure:

```yaml
role: "role_name"
version: "1.0.0"
status: "active"
system_role: "description_of_system_role"

complexity_scope: ["C1", "C2"]
model_alias: "$ALIAS_FROM_MODELS_YAML"
fallback_model: "$ALIAS_FROM_MODELS_YAML"
runtime_hint: "agent_os_python"

responsibilities:
  - "Responsibility 1"
  - "Responsibility 2"

interfaces:
  inputs: ["list", "of", "expected", "inputs"]
  outputs: ["list", "of", "expected", "outputs"]

dependencies:
  - "paths_to_required_resources"

forbidden_from:
  - "Action that must not be taken"

handoff_triggers:
  - condition: "When to hand off"
    target: "role_to_hand_off_to"

escalation_path: "peer | supervisor | council | terminal"

constraints:
  token_budget: number
  max_tool_calls: number
  max_files_modified: number

quality_gates:
  - "Gate 1"
  - "Gate 2"

metrics:
  - "metric_name"

memory_policy:
  short_term: { write: ["list"] }
  long_term: { write: ["list"] }
  semantic: { index: ["list"] }

fail_safe:
  on_condition: "action"
```

## Enforcement Model

Runtime should:
1. Load all role contracts via `RoleContractLoader`
2. Validate schema and version on startup
3. Bind role → model alias → constraints
4. Enforce handoff and forbidden actions via `RolePolicyGuard`
5. Verify quality gates before task completion
6. Record contract compliance in execution traces

## Governance

- Contracts are versioned independently
- Changes require C3+ review process
- Breaking changes must update `router.yaml` references
- Historical versions kept in `role_contracts/archive/`
- Model alias resolution validated against `models.yaml` at load time
- Handoff target validation ensures all targets reference known roles or `terminal`

## Non-goals

These files do NOT replace:
- Runtime IO schemas in `contracts.py`
- Provider configuration (`model_providers.json`)
- Benchmark configuration
- Workflow definitions (`.agents/workflows/`)
