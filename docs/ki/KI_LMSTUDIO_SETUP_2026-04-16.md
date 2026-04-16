# KI: LM Studio Setup Strategy

**Status:** Active
**Version:** 1.0 (Integration v4.3)
**Date:** 2026-04-16
**Category:** Infrastructure / Local Models

---

## Configuration Details

LM Studio is integrated as a top-priority local provider for the `orchestrator`, `routine_worker`, and `architect` roles.

### Connection
- **Base URL:** `http://127.0.0.1:1234/v1`
- **Provider ID:** `lmstudio`
- **Default Model:** `google/gemma-4-e4b`

### Integration Path
1. **Model Alias:** `MODEL_LOCAL_LMSTUDIO` mapped to `lmstudio/google/gemma-4-e4b` in `models.yaml`.
2. **OmniRoute Combos:** Inserted as the first item in the fallback chains within `omniroute_combos.yaml`.
3. **Failover:** If LM Studio is not running, OmniRoute will automatically fall back to Ollama or Cloud providers as per the defined chains.

---

## Operational Guide

### 1. Starting LM Studio
- Open LM Studio.
- Load the model: `google/gemma-4-e4b`.
- Ensure the Local Server is started on port `1234`.
- CORS should be enabled if accessing via browser tools (though OmniRoute connects directly via Python).

### 2. Verification
To verify the connection through the Antigravity stack:
```bash
python3 scripts/omniroute/sync_combos.py --test --role orchestrator
```

### 3. Adding New Models
To add more models from LM Studio:
1. Update `configs/orchestrator/models.yaml` with a new alias.
2. Add the model to relevant combos in `configs/orchestrator/omniroute_combos.yaml`.
3. Run `--verify` to confirm pathing.

---

## Troubleshooting
- **Connection Refused:** Check if LM Studio server is actually "ON".
- **Model Not Found:** Ensure the model ID in LM Studio matches the one in `omniroute_combos.yaml` (prefix `lmstudio/` is stripped by the gateway, but the identifier must match what the LM Studio API reports).
