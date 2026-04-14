# Role Contracts — Antigravity Core

> **Source of Truth:** Individual YAML files in this directory.
> **Referenced by:** `configs/orchestrator/router.yaml` → `roles.contracts_path`
> **Overview doc:** `configs/orchestrator/AGENT_ROLE_CONTRACTS.md`

## Purpose

Role contracts define explicit boundaries for each agent type in the swarm:
- **Responsibilities** — what each role owns
- **Forbidden actions** — what each role must NOT do
- **Handoff triggers** — when to pass work to another role
- **Escalation paths** — who to contact when stuck
- **Quality gates** — what "done" means for each role

## Schema

Each contract file follows this structure:

```yaml
role: "role_name"
version: "1.0.0"
complexity_scope: ["C1", "C2"]
responsibilities:
  - "Responsibility 1"
  - "Responsibility 2"
forbidden_actions:
  - "Action that must not be taken"
handoff_triggers:
  condition: "When to hand off"
  target_role: "role_to_hand_off_to"
escalation_path: ["peer", "supervisor", "council"]
quality_gates:
  - "Gate 1"
  - "Gate 2"
```

## Current Roles

See `AGENT_ROLE_CONTRACTS.md` for the full role summary table.

| Role | File |
|------|------|
| Orchestrator | `orchestrator.yaml` |
| Routine Worker | `routine_worker.yaml` |
| Engineer | `engineer.yaml` |
| Design Lead | `design_lead.yaml` |
| Reviewer | `reviewer.yaml` |
| Architect | `architect.yaml` |
| Council | `council.yaml` |

## Governance

- Contracts are versioned independently
- Changes require C3+ review process
- Breaking changes must update `router.yaml` references
- Historical versions kept in `role_contracts/archive/`
