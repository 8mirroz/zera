# Agent Role Contract Specifications
# Version: 4.2
# REFERENCE DOC — not source of truth.
# Source of truth: configs/orchestrator/role_contracts/*.yaml
# This document provides human-readable overview and integration guide.
# In case of conflict, the individual YAML files win.

**Status:** Reference  
**SoT:** `configs/orchestrator/role_contracts/`

---

## Overview

Role contracts define explicit boundaries for all agent types: responsibilities, forbidden actions, handoff triggers, escalation paths, and quality gates. They eliminate role bleed and establish clear execution contracts.

---

## Role Summary

| Role | Complexity Scope | Primary Model | Escalation |
|------|-----------------|---------------|------------|
| Orchestrator | C1-C5 | `$AGENT_MODEL_ORCHESTRATOR` | council |
| Routine Worker | C1-C2 | `$AGENT_MODEL_FAST_PRIMARY` | engineer |
| Engineer | C2-C4 | `$AGENT_MODEL_BUILDER_A` | architect |
| Design Lead | C2-C4 | `$AGENT_MODEL_BUILDER_B` | architect |
| Reviewer | C3-C5 | `$AGENT_MODEL_REVIEWER` | council |
| Architect | C4-C5 | `$AGENT_MODEL_COUNCIL` | council |
| Council | C5 | `$AGENT_MODEL_COUNCIL` | user |

All model aliases resolve via `configs/orchestrator/models.yaml` and utilize the **Multi-Tier Fallback Strategy** defined in `configs/orchestrator/omniroute_combos.yaml`.

### Model Selection Strategy (v4.3)
1.  **Local Primary (Free/Fast)**: High-performance local models (`Qwen 2.5 Coder 7B`, `DeepSeek R1 7B`).
2.  **Free Remote (Cost-Efficiency)**: OpenRouter free-tier models (`Qwen 3.6 Plus`, `Gemma 3`).
3.  **Premium Remote (Complex/Rare)**: Top-tier models (`OpenAI Codex`, `Claude Opus`) used only for C4-C5 tiers or critical failures.
4.  **Extreme Local Fallback**: Ultra-lightweight local models (`Gemma 4 e4b/e2b`) as the final line of defense.

---

## Role Contract Schema

```yaml
role: "string"
version: "string"
complexity_scope: ["C1".."C5"]
model_alias: "$ALIAS_FROM_MODELS_YAML"
fallback_model: "$ALIAS_FROM_MODELS_YAML"
runtime_hint: "agent_os_python | hermes | zeroclaw"

responsibilities:
  - "list of owned tasks/decisions"

forbidden_from:
  - "tasks/decisions explicitly out of scope"

handoff_triggers:
  - condition: "string"
    target: "role_name"
    contract_template: ".agent/contracts/path.md"

escalation_path: "role_name"

constraints:
  token_budget: number
  max_tool_calls: number
  max_files_modified: number

quality_gates:
  - "list of required checks before completion"
```

---

## Handoff Contract Template

```markdown
# Handoff Contract

**From:** {from_role}
**To:** {to_role}
**Task ID:** {task_id}
**Timestamp:** {ISO-8601}

## Context
### What Was Done
{list of completed actions}

### Current State
{description of current system state}

### Open Questions
{list of unresolved items}

## Handoff Reason
**Type:** {out_of_specialization | complexity_escalation | dependency_required}
**Explanation:** {detailed explanation}

## Required Action
{specific action needed from receiving role}

## Constraints
- Token budget: {X}
- Dependencies: {list}

## Acceptance Criteria
- [ ] {criterion 1}
- [ ] {criterion 2}

**Acknowledgment Required:** Yes
**Timeout:** 10 minutes
**Escalation Path:** {path}
```

---

## Role Conflict Resolution Matrix

| Conflict Type | Severity | Resolution |
|--------------|----------|------------|
| Responsibility overlap | Medium | Clarify boundaries in contract |
| Forbidden action attempted | High | Block + escalate to orchestrator |
| Handoff cycle detected | Critical | Break cycle, escalate to council |
| Token budget exceeded | Medium | Force completion or escalate |
| Quality gate failure | Medium | Return for revision (max 2x) |

---

## Integration

### Router Integration
```yaml
# configs/orchestrator/router.yaml
roles:
  contracts_path: "configs/orchestrator/role_contracts/"
  enforce_contracts: true
  conflict_detection:
    enabled: true
    auto_resolve: true
    escalation_on_repeat: true
```

### Workflow Integration
Reference role contracts in workflow files:
```markdown
<role:ARCHITECT>
contract: "configs/orchestrator/role_contracts/architect.yaml"
</role>
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Handoff success rate | > 95% |
| Forbidden action rate | < 1% |
| Role conflict incidents | < 5/month |
| Reviewer overload | Low (max 3 concurrent) |
