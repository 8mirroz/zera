# Drift & Duplication Report — Zera Multi-Agent Architecture

> **Date:** 2026-04-13  
> **Scope:** Identified drift, duplication, mismatches, silent fallbacks  
> **Severity:** 🔴 Critical  |  🟡 Medium  |  🟢 Low  

---

## 1. Critical: `.agent/` vs `.agents/` Mismatch

### 1.1 The Problem

The workspace has **two parallel directory trees** for agent runtime state:

| Directory | Files Present | Used By |
|-----------|--------------|---------|
| `.agent/` | `evolution/`, `memory/`, `skills/`, `workflows/`, `templates/` | `zera-evolutionctl.py`, `self_evolution_loop.py`, legacy scripts |
| `.agents/` | `config/`, `evolution/`, `memory/`, `rules/`, `runtime/`, `skills/`, `templates/` | Current runtime expectations, `core-zera.md`, newer tooling |

**Specific mismatches:**

| Path (`.agent/`) | Path (`.agents/`) | Status |
|------------------|-------------------|--------|
| `.agent/evolution/state.json` | `.agents/evolution/state.json` | ⚠️ Both exist, different content |
| `.agent/evolution/telemetry.jsonl` | `.agents/evolution/` (no telemetry.jsonl) | 🔴 Only `.agent/` has telemetry |
| `.agent/evolution/evolutionctl-state.json` | `.agents/evolution/evolutionctl-state.json` | ⚠️ Both exist |
| `.agent/evolution/promotion_state.json` | `.agents/evolution/promotion_state.json` | ⚠️ Both exist |
| `.agent/evolution/meta_memory.json` | `.agents/evolution/meta_memory.json` | ⚠️ Both exist |
| `.agent/memory/` | `.agents/memory/` | ⚠️ `.agents/memory/` has more structure (indexes, quarantine, solutions) |
| `.agent/skills/` (29 skills) | `.agents/skills/` (29 skills) | ⚠️ Same count, but may diverge |
| `.agent/workflows/` (44 workflows) | `.agents/workflows/` (not found) | 🔴 Only `.agent/` has workflows |
| `.agent/templates/compressed/T1–T7` | `.agents/templates/compressed/T1–T7` | ✅ Both exist (duplicated) |
| — | `.agents/config/workflow_sets.active.json` | 🔴 Only `.agents/` has this |
| — | `.agents/rules/core-zera.md` | 🔴 Only `.agents/` has this |

### 1.2 Impact

- **State divergence:** Writes to `.agent/evolution/` by `zera-evolutionctl.py` are NOT visible to readers expecting `.agents/evolution/`
- **Telemetry loss:** `.agent/evolution/telemetry.jsonl` is the active sink, but newer code may look for `.agents/`
- **Skill inconsistency:** Two skill directories; `swarmctl.py publish-skills` targets `.agent/skills/`, but `.agents/skills/` exists independently
- **Workflow isolation:** Workflows only in `.agent/workflows/`, not mirrored to `.agents/`

### 1.3 Root Cause

Historical naming migration: `.agent/` → `.agents/` was partially applied. The `zera-evolutionctl.py` code explicitly uses:
```python
EVOLUTION_DIR = ROOT / ".agent" / "evolution"
```
While the audit spec and newer conventions expect `.agents/`.

### 1.4 Recommended Fix

1. **Canonical:** `.agents/` (plural, per audit spec)
2. **Migration:** Create symlink `.agent → .agents` OR update all code to use `.agents/`
3. **Verification:** After migration, validate that all 4 evolution state files, telemetry, skills, and workflows are accessible via `.agents/`

---

## 2. Routing Logic Duplication

### 2.1 `router.yaml` vs In-Code Routing

| Location | What It Does | Duplication? |
|----------|-------------|--------------|
| `configs/orchestrator/router.yaml` | SoT for tiers, models, workflows, motion triggers | ✅ Canonical |
| `agent_os/model_router.py` (`ModelRouter.route()`) | "Baseline implementation for v3 compatibility" | ⚠️ Stub — real logic in UnifiedRouter |
| `agent_os/model_router.py` (`UnifiedRouter`) | Actual routing implementation | ✅ Correct (consumes router.yaml) |
| `agent_os/registry_workflows.py` (`RegistryWorkflowResolver`) | Workflow resolution from registry | ✅ Correct (consumes router.yaml) |
| `agent_os/routing_vector.py` | Routing vector computation | ⚠️ Potential duplication if not aligned with router.yaml |
| `agent_os/persona_mode_router.py` | Persona-based mode routing | ⚠️ Parallel routing path; may conflict with tier-based routing |

### 2.2 Motion-Aware Routing

`router.yaml` contains a **motion_awareness** section (GSAP/Framer/CSS triggers) that is a separate routing path:
- Activated by keywords in task description
- Can override normal workflow assignment
- **Risk:** Not validated by `routing_consistency_checker.py` — no tool checks that motion trigger skills/workflows actually exist

---

## 3. Missing Paths Referenced in Documentation

### 3.1 `templates/` Directory

| Reference | Actual Path | Status |
|-----------|-------------|--------|
| `templates/adaptation/efficiency-dashboard.json` (in `docs/AGENT_ONBOARDING.md`) | Does not exist | ❌ Missing |
| `templates/` directory (root level) | Does not exist | ❌ Missing |
| `.agent/templates/compressed/` | Exists | ✅ Present |

**Note:** The `AGENT_ONBOARDING.md` references a `templates/` directory at the repo root that does not exist.

### 3.2 `configs/orchestrator/completion_gates.yaml`

| Reference | Actual Path | Status |
|-----------|-------------|--------|
| `configs/orchestrator/completion_gates.yaml` (referenced in `router.yaml` header comment) | Does not exist | ❌ Missing |

The `router.yaml` header states: `Completion gates: configs/orchestrator/completion_gates.yaml` — but this file is absent.

### 3.3 `configs/orchestrator/role_contracts/`

| Reference | Actual Path | Status |
|-----------|-------------|--------|
| `configs/orchestrator/role_contracts/` (referenced in `router.yaml`) | Does not exist as directory | ❌ Missing |

The `router.yaml` defines `roles.contracts_path: "configs/orchestrator/role_contracts/"` but this directory does not exist. The `AGENT_ROLE_CONTRACTS.md` file exists at `configs/orchestrator/AGENT_ROLE_CONTRACTS.md` instead.

---

## 4. Duplicate Configuration Files

### 4.1 Zera Command Runtime

| File 1 | File 2 | Duplication? |
|--------|--------|-------------|
| `scripts/zera/zera_command_runtime.py` | `scripts/zera_command_runtime.py` | 🔴 **Exact duplicate at root** — two copies of the same script |

### 4.2 MCP Profile Testing

| File 1 | File 2 | Duplication? |
|--------|--------|-------------|
| `scripts/internal/test_mcp_profiles.py` | `scripts/test_mcp_profiles.py` | 🔴 **Exact duplicate** — root and internal copies |

### 4.3 Reliability Orchestrator

| File 1 | File 2 | Duplication? |
|--------|--------|-------------|
| `scripts/internal/reliability_orchestrator.py` | `scripts/reliability_orchestrator.py` | 🔴 **Exact duplicate** — root and internal copies |

### 4.4 Skill Definitions (Dual Sources)

| Source 1 | Source 2 | Duplication? |
|----------|----------|-------------|
| `.agent/skills/zera-core/SKILL.md` | `configs/skills/zera-core/SKILL.md` | ⚠️ Two skill source directories |
| `.agent/skills/zera-muse/SKILL.md` | `configs/skills/zera-muse/SKILL.md` | ⚠️ Two skill source directories |
| `.agent/skills/zera-researcher/SKILL.md` | `configs/skills/zera-researcher/SKILL.md` | ⚠️ Two skill source directories |
| `.agent/skills/zera-rhythm-coach/SKILL.md` | `configs/skills/zera-rhythm-coach/SKILL.md` | ⚠️ Two skill source directories |
| `.agent/skills/zera-strategist/SKILL.md` | `configs/skills/zera-strategist/SKILL.md` | ⚠️ Two skill source directories |
| `.agent/skills/zera-style-curator/SKILL.md` | `configs/skills/zera-style-curator/SKILL.md` | ⚠️ Two skill source directories |

**6 skills** exist in both `.agent/skills/` AND `configs/skills/`. Unclear which is canonical.

### 4.5 Config Catalog Duplication

`configs/orchestrator/catalog.json` contains entries that reference files in both `configs/tooling/` AND describe entries that exist elsewhere:
- `METRICS_DASHBOARD_V1_RU` → `docs/ki/METRICS_DASHBOARD_V1_RU.md` (file does not exist)
- Multiple task_id entries that reference non-existent artifacts

---

## 5. Silent Fallbacks

### 5.1 YAML Parsing Fallback

In `agent_os/model_router.py`:

```python
def _safe_yaml_load(text: str) -> dict[str, Any]:
    if _yaml_mod is not None:
        try:
            result = _yaml_mod.safe_load(text)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
    return parse_simple_yaml(text)  # ← silent fallback to simple parser
```

**Risk:** If `PyYAML` is installed but fails on complex YAML, the simple parser will silently produce incorrect results (missing nested structures, lists, etc.)

### 5.2 ModelRouter Baseline Implementation

In `agent_os/model_router.py`:

```python
def route(self, routing_topic: str, complexity: str | dict = "C2", **kwargs) -> dict:
    # Baseline implementation for v3 compatibility
    # Real logic moved to UnifiedRouter in v4
    out = ModelRouteOutput(...)
```

**Risk:** If `ModelRouter.route()` is called directly (instead of `UnifiedRouter`), it returns a stub result, not actual routing. No warning or deprecation notice.

### 5.3 Trace Path Default

In `agent_os/observability.py`:

```python
def emit_event(event_type: str, payload: dict[str, Any]) -> None:
    trace_path = os.getenv("AGENT_OS_TRACE_FILE")
    if not trace_path:
        trace_path = str(Path("logs") / "agent_traces.jsonl")  # ← relative path
```

**Risk:** If `AGENT_OS_TRACE_FILE` is not set and the working directory is not the repo root, traces are written to a relative `logs/` directory — potentially wrong location.

### 5.4 RegistryWorkflowResolver YAML Fallback

In `agent_os/registry_workflows.py`:

```python
def _load_yaml(self, path: Path) -> dict[str, Any]:
    if yaml is not None:
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    data = parse_simple_yaml(text)  # ← silent fallback
    return data if isinstance(data, dict) else {}
```

**Risk:** Same as 5.1 — complex YAML structures may be silently lost.

### 5.5 Config Load Exception Swallowing

In `agent_os/model_router.py`:

```python
def _load_config(self) -> None:
    try:
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)  # ← loading YAML as JSON!?
    except Exception as e:
        raise ModelRouterError(f"Failed to load config: {e}")
```

**Risk:** `_load_config()` attempts to parse `router.yaml` as JSON (not YAML). This will always fail. The method is commented out in `__init__`, so not currently active, but the bug remains in the codebase.

---

## 6. Legacy Code Paths

### 6.1 Evolution Loops

| Script | Status | Notes |
|--------|--------|-------|
| `scripts/zera/zera-self-evolution.sh` | ⚠️ Legacy | Superseded by `zera-evolutionctl.py` |
| `scripts/zera/zera-infinite-loops.sh` | ⚠️ Legacy | 8 algorithms bundled, superseded by `zera-evolutionctl.py` |
| `scripts/zera/zera-evolve.sh` | ⚠️ Legacy | Superseded by `zera-evolutionctl.py` |
| `scripts/internal/self_evolution_loop.py` | ✅ Active | Core loop, called by `zera-evolutionctl.py` |

### 6.2 Vault State

`vault/loops/.evolve-state.json` is a **legacy** evolution state file. The active state is in `.agent/evolution/evolutionctl-state.json`. The vault file is maintained for backward compatibility only.

### 6.3 Trace Schema Migration

`configs/tooling/trace_schema.json` declares:
```json
"legacy_compat": {
    "accepted_for_migration": true,
    "legacy_envelope_patterns": ["{schema_version, entry:{...}}", "{ts:number, event_type, payload}"]
}
```

Traces in `logs/agent_traces.jsonl` may contain a mix of v1 and v2.1 format events. The `trace_validator.py` handles this, but the migration is not complete.

---

## 7. Drift Summary

| Category | Count | Severity | Priority |
|----------|-------|----------|----------|
| `.agent/` vs `.agents/` mismatch | 1 (systemic) | 🔴 Critical | P0 |
| Duplicate scripts (root vs internal) | 3 pairs | 🔴 Critical | P0 |
| Missing referenced paths | 3 | 🟡 Medium | P1 |
| Skill dual sources | 6 skills | 🟡 Medium | P1 |
| Silent YAML fallbacks | 2 | 🟡 Medium | P1 |
| Config loaded as JSON bug | 1 | 🟢 Low (inactive) | P2 |
| Trace path relative default | 1 | 🟡 Medium | P1 |
| Legacy evolution scripts | 3 | 🟡 Medium | P1 |
| Catalog references to missing files | Multiple | 🟢 Low | P2 |
| Motion routing unvalidated | 1 | 🟡 Medium | P1 |

---

## 8. Recommended Immediate Actions

1. **Resolve `.agent/` → `.agents/`** — symlink or full migration
2. **Remove duplicate root scripts** — keep `scripts/internal/` copies, delete root copies
3. **Create missing `configs/orchestrator/completion_gates.yaml`** or remove references
4. **Consolidate skill sources** — pick one canonical location (`.agent/skills/` recommended)
5. **Fix YAML fallback** — add validation that simple parser results match expected schema
6. **Fix trace path default** — use absolute path based on repo root
7. **Catalog cleanup** — remove references to non-existent artifacts
