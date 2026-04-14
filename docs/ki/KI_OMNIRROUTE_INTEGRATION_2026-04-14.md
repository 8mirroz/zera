# KI: OmniRoute Integration — Role Model Provider

**Status:** Active
**Version:** 4.3
**Date:** 2026-04-14
**Category:** Infrastructure / Model Routing

---

## Overview

OmniRoute deployed as primary model provider for the Antigravity role contract system.
Replaces direct API calls with intelligent combo-based fallback chains managed via version-controlled config.

**Before:** Role → single model alias → direct API call
**After:** Role → OmniRoute combo → 4-tier fallback chain → smart routing

---

## Architecture

```
Role Contract (YAML)
    ↓
$AGENT_MODEL_<ROLE>  (models.yaml alias)
    ↓
omniroute://combo/<name>  (OmniRoute gateway)
    ↓
┌─────────────────────────────────────┐
│  OmniRoute Gateway                  │
│  http://localhost:20128/v1          │
│                                     │
│  Combo: <name>                      │
│    1. Primary model (subscription)  │
│    2. Fallback 1 (API key)          │
│    3. Fallback 2 (cheap/backup)     │
│    4. Fallback 3 (free tier)        │
│                                     │
│  Strategy: priority                 │
│  Circuit breaker: auto-healthcheck  │
│  Quota tracking: real-time          │
└─────────────────────────────────────┘
    ↓
Actual model API call
```

---

## Configuration

### Version-Controlled Combos

Source of truth: `configs/orchestrator/omniroute_combos.yaml`

Each combo defines:
- **Role mapping** — which role contract it serves
- **Strategy** — routing strategy (priority, weighted, round-robin, etc.)
- **Model chain** — ordered list of models with fallback priority
- **Reason** — why each model was chosen

### Sync to OmniRoute

```bash
# View combo summary (offline)
python3 scripts/omniroute/sync_combos.py

# Verify combos against OmniRoute available models
python3 scripts/omniroute/sync_combos.py --verify

# Test actual model routing through OmniRoute
python3 scripts/omniroute/sync_combos.py --test

# Test specific role combo
python3 scripts/omniroute/sync_combos.py --test --role engineer

# Push combos to OmniRoute dashboard
python3 scripts/omniroute/sync_combos.py --apply
```

---

## Role→Model Mapping

| Role | Primary Combo | Fallback Chain |
|------|--------------|----------------|
| **Orchestrator** | `qw/qwen3.6-plus` | qwen3-coder-next → deepseek-v3:free → qwen3.6-plus:free |
| **Routine Worker** | `qw/qwen3.6-plus` | qwen3.6-plus:free → gemma-3-27b:free → qwen3-4b |
| **Engineer** | `qw/qwen3-coder` | qwen3-coder-next → cx/codex → deepseek-v3:free → qwen-coder-32b:free |
| **Design Lead** | `qw/qwen3.6-plus` | gemma-3-27b:free → qwen3.5-plus → gc/gemini-cli |
| **Reviewer** | `qw/qwen-2.5-72b` | cc/claude-opus → qwen-coder-32b:free → deepseek-r1:free |
| **Architect** | `cc/claude-opus-4-6` | qwen3-coder-next → deepseek-r1-0528:free → deepseek-r1:free |
| **Council** | `openai/gpt-5.3` | cc/claude-opus → qwen3-coder-next → deepseek-r1:free |

---

## Files Modified

| File | Change |
|------|--------|
| `configs/orchestrator/models.yaml` | v4.2 → v4.3, added OmniRoute combo aliases |
| `configs/orchestrator/omniroute_combos.yaml` | NEW — version-controlled combo definitions |
| `configs/orchestrator/role_contracts/*.yaml` | Updated model_alias + fallback_model to use OmniRoute aliases |
| `scripts/omniroute/sync_combos.py` | NEW — sync/verify/test utility |
| `repos/packages/agent-os/src/agent_os/role_contract_loader.py` | Added omniroute:// URI support in alias resolver |
| `repos/packages/agent-os/src/agent_os/model_router.py` | Added `os` import (fix), role contract metadata in route() |

---

## Testing

```bash
# Role contract tests (41 tests)
cd repos/packages/agent-os && python3 -m pytest tests/test_role_contracts.py -v

# OmniRoute connectivity test
python3 scripts/omniroute/sync_combos.py --test

# Alias resolution verification
python3 scripts/omniroute/sync_combos.py --verify
```

---

## Migration Notes

### Backward Compatibility
- Legacy aliases (`$MODEL_ENGINEER_PRIMARY`, etc.) still work
- Direct fallback aliases (`$AGENT_MODEL_ENGINEER_DIRECT`) provide offline capability
- If OmniRoute unavailable, system falls back to direct API calls

### When OmniRoute is Down
1. Alias resolver detects `omniroute://` prefix
2. Falls back to `_DIRECT` variant of the alias
3. Direct aliases map to standard model IDs (no gateway)
4. Full system functionality preserved

### Adding New Combos
1. Edit `configs/orchestrator/omniroute_combos.yaml`
2. Run `python3 scripts/omniroute/sync_combos.py --verify`
3. Run `python3 scripts/omniroute/sync_combos.py --test`
4. Commit changes (version-controlled)
5. Manually update OmniRoute dashboard if `--apply` not available

---

## Known Limitations

1. **No programmatic combo creation** — OmniRoute doesn't expose API for creating combos. Must be done via dashboard.
2. **Dashboard sync required** — YAML config is source of truth, but must be manually synced to OmniRoute.
3. **Health check endpoint varies** — Different OmniRoute versions may have different health endpoints.

---

## Future Work

- [ ] Contribute combo API to OmniRoute upstream for programmatic management
- [ ] Auto-sync on git hook (pre-commit → sync to OmniRoute)
- [ ] Per-request model selection based on task content analysis
- [ ] Cost tracking per role → optimize combo ordering by cost/quality ratio
- [ ] A/B testing: compare combo model outputs for quality scoring
