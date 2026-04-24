# Source of Truth Matrix — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Scope:** What is authoritative, what is derived, what is drift-prone  

---

## 1. Canonical Sources of Truth

| SoT Artifact | Domain | Owner | Update Path | Validation Hook | Consumers |
|--------------|--------|-------|-------------|-----------------|-----------|
| `configs/orchestrator/router.yaml` | Task routing (C1–C5), model selection, workflow assignment, motion triggers | Platform architect | Direct edit → `swarmctl.py doctor` | `routing_consistency_checker.py`, `workflow_model_alias_validator.py` | `ModelRouter`, `UnifiedRouter`, `RegistryWorkflowResolver`, `swarmctl.py`, all CLI tools |
| `configs/orchestrator/models.yaml` | Model alias registry (30+ aliases), Hermes profile defaults | Platform architect | Direct edit → `swarmctl.py doctor` | `swarmctl.py doctor` (alias resolution check) | All routing code, runtime providers |
| `configs/orchestrator/runtimes.yaml` | Runtime view | Platform architect | Derived from `runtime_providers.json` | `swarmctl.py doctor` (sync check) | `RuntimeRegistry`, runtime providers |
| `configs/tooling/runtime_providers.json` | Runtime provider definitions (canonical) | Platform architect | Direct edit | Sync validation with `runtimes.yaml` | `runtimes.yaml`, `RuntimeRegistry` |
| `configs/tooling/trace_schema.json` | Trace event schema (v2.1) | Platform architect | Direct edit | `trace_validator.py --json` | `observability.py`, all event emitters, dashboard |
| `configs/registry/indexes/*.yaml` | Registry indexes (agents, skills, workflows) | Platform architect | Direct edit | `swarmctl.py doctor` (index integrity) | `RegistryWorkflowResolver` |
| `configs/registry/workflows/*.yaml` | Registered workflow definitions | Platform architect | Direct edit | Schema validation | `RegistryWorkflowResolver` |
| `configs/registry/skills/*.yaml` | Registered skill definitions | Platform architect | Direct edit | Schema validation | `RegistryWorkflowResolver` |
| `configs/registry/schemas/*.yaml` | Schema definitions | Platform architect | Direct edit | YAML validation | All validation tools |
| `configs/registry/personas/*.yaml` | Persona definitions | Platform architect | Direct edit | Schema validation | `persona_mode_router.py`, `persona_eval.py` |
| `.agents/skills/<name>/SKILL.md` | Published skill definitions (29 skills) | Skill author | `swarmctl.py publish-skills` | Skill drift validator | Agent context injection |
| `.agents/workflows/*.md` | Workflow definitions (44 workflows) | Workflow author | Direct edit | Workflow consistency check | Agent execution |
| `configs/personas/zera/*` | Zera persona configuration | Zera owner | Direct edit | `swarmctl.py doctor` | Persona loader |
| `configs/tooling/zera_command_registry.yaml` | Zera command definitions | Platform architect | Direct edit | `zera_command_runtime.py catalog` | `ZeraCommandOS` |
| `configs/tooling/zera_promotion_policy.yaml` | Promotion governance policy | Platform architect | Direct edit | `promote-policy-check` | `zera-evolutionctl.py` |
| `.agents/evolution/state.json` | Evolution state | Evolution controller | `zera-evolutionctl.py` writes | State integrity check | All evolution tools |
| `configs/tooling/mcp_profiles.json` | MCP server profiles | Platform architect | Direct edit | MCP profile consistency checker | MCP integration layer |

---

## 2. Runtime State (Ephemeral / Append-Only)

| Artifact | Type | Writer | Reader | Lifetime |
|----------|------|--------|--------|----------|
| `logs/agent_traces.jsonl` | Append-only event log | `emit_event()` (all components) | Dashboard, validator, auditor | Persistent (rotated manually) |
| `.agents/evolution/telemetry.jsonl` | Append-only evolution log | `self_evolution_loop.py` | Dashboard, evolution auditor | Persistent |
| `.agents/evolution/loop.log` | Text log | `self_evolution_loop.py` | Human operator | Persistent |
| `.agents/evolution/evolutionctl.out.log` | Text log | `zera-evolutionctl.py` | Human operator | Persistent |
| `.agents/memory/memory.jsonl` | Append-only memory | All agents | `Retriever`, `MemoryStore` | Persistent |
| `.agents/memory/goal-stack.json` | Volatile state | Goal manager | Agent runtime | Volatile (session) |
| `.agents/runtime/approvals.json` | Approval state | `ApprovalEngine` | Auditor | Persistent |
| `.agents/runtime/background-jobs.json` | Job state | `BackgroundJobRegistry` | Scheduler, monitor | Persistent |
| `.agents/evolution/promotion_state.json` | Promotion state | `zera-evolutionctl.py` | Promotion system | Persistent |
| `vault/loops/.evolve-state.json` | Legacy evolution state | Legacy loops | Legacy readers | Persistent (deprecated) |

---

## 3. Derived / Narrative Artifacts (Drift-Prone)

| Artifact | Derived From | Drift Risk | Notes |
|----------|-------------|------------|-------|
| `docs/AGENT_ONBOARDING.md` | Actual routing/execution flow | ⚠️ HIGH | Describes system architecture; must be manually updated after any routing change |
| `README.md` | Actual file structure, capabilities | ⚠️ HIGH | Contains routing references; often lags behind actual state |
| `docs/ki/WAVES_2_12_COMPLETE_STATUS.md` | Wave execution results | ⚠️ MEDIUM | Status narrative; drift if waves continue without update |
| `docs/ki/WAVE_2_SHADOW_UPGRADE_AND_CONTROLLED_PROMOTE.md` | Wave 2 implementation | ⚠️ MEDIUM | Implementation guide; may diverge from actual code |
| `docs/ki/WAVE_5_RUNTIME_EVIDENCE_INTEGRITY.md` | Wave 5 implementation | ⚠️ MEDIUM | Evidence integrity patterns; may not reflect current state |
| `docs/ki/WAVE_6_PRODUCTION_CONTROL_PLANE.md` | Wave 6 implementation | ⚠️ MEDIUM | Control plane design; may not match current implementation |
| `docs/ki/WAVE_7_MCP_SERVER_INTEGRITY.md` | Wave 7 implementation | ⚠️ MEDIUM | MCP server analysis; may not reflect current MCP state |
| `docs/ki/WAVE_8_AGENT_OS_RUNTIME.md` | Wave 8 implementation | ⚠️ MEDIUM | Agent OS runtime analysis; may not match current code |
| `docs/ki/ZERA_SELF_EVOLUTION_LOOP_GUIDE_2026-04-09.md` | Evolution loop behavior | ⚠️ HIGH | Guide to evolution loop; drifts as loop evolves |
| `vault/reports/evolution_dashboard.md` | Evolution telemetry data | ⚠️ MEDIUM | Generated dashboard; may be stale |
| `vault/00-overview.md` | Vault structure | ⚠️ LOW | Overview; rarely changes |
| `vault/01-planning/current-plan.md` | Current evolution plan | ⚠️ HIGH | Plan evolves faster than document |
| `configs/orchestrator/catalog.json` | Auto-generated catalog | ⚠️ LOW | Programmatic; kept current by tooling |
| `docs/remediation/hermes-zera/*/artifacts/*` | Wave 4+ artifacts | ⚠️ LOW | Generated by evolutionctl; time-stamped |
| `outputs/reliability/latest/*.json` | Reliability orchestration | ⚠️ LOW | Auto-generated; kept current |

---

## 4. Drift Detection Strategy

### 4.1 Automated Validation

| Validation | Target | Command | Frequency |
|------------|--------|---------|-----------|
| Routing consistency | `router.yaml` + `models.yaml` | `swarmctl.py doctor` | On every config change |
| Trace schema compliance | `logs/agent_traces.jsonl` | `trace_validator.py` | Periodic |
| Skill drift | `.agents/skills/` | `skill_drift_validator.py` | Periodic |
| Workflow model aliases | `router.yaml` → `models.yaml` | `workflow_model_alias_validator.py` | On routing changes |
| Runtime sync | `runtimes.yaml` ↔ `runtime_providers.json` | `swarmctl.py doctor` | On runtime changes |
| Document validation | Front-matter, naming | `validate_documents.py` | Periodic |

### 4.2 Manual Validation

| Check | What to Verify | How |
|-------|---------------|-----|
| Onboarding doc accuracy | Does `AGENT_ONBOARDING.md` reflect actual routing? | Compare doc vs `router.yaml` |
| README accuracy | Are paths, commands, capabilities current? | Spot-check referenced paths |
| Knowledge items | Are `docs/ki/WAVE_*` files aligned with code? | Compare doc vs implementation |
| Vault plans | Is `vault/01-planning/current-plan.md` current? | Compare vs actual evolution state |

---

## 5. Conflict Resolution Rules

| Conflict | Winner | Resolution Path |
|----------|--------|-----------------|
| `runtimes.yaml` ≠ `runtime_providers.json` | `runtime_providers.json` wins | Regenerate `runtimes.yaml` from JSON |
| `router.yaml` model alias ≠ `models.yaml` alias | `models.yaml` wins | Fix alias in `router.yaml` |
| Onboarding doc ≠ actual code | Actual code wins | Update doc |
| `.agents/` state ≠ `.agents/` state | `.agents/` wins (canonical) | Migrate `.agents/` → `.agents/` |
| Legacy trace schema ≠ v2.1 schema | v2.1 schema wins | Migrate traces |
| Narrative doc ↔ code implementation | Code wins | Update doc |

---

## 6. SoT Health Summary

| Category | Health | Notes |
|----------|--------|-------|
| Routing config | ✅ Healthy | Single source, validated |
| Model registry | ✅ Healthy | Single source, validated |
| Runtime config | ⚠️ Dual source | `runtime_providers.json` (canonical) + `runtimes.yaml` (derived) |
| Trace schema | ✅ Healthy | Single schema, validator exists |
| Registry (workflows/skills) | ✅ Healthy | YAML + schema validation |
| Memory stores | ⚠️ Fragmented | `.agents/memory/` (canonical) + `.agents/memory/` (legacy?) |
| Evolution state | ⚠️ Dual state | `.agents/evolution/` (active) + `vault/loops/.evolve-state.json` (legacy) |
| Narrative docs | ❌ Drift-prone | Multiple outdated guides |
| Runtime traces | ✅ Healthy | Single sink, schema-validated |
