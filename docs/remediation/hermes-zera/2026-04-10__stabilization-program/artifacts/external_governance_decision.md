# External Governance — Absorption Plan

**Date:** 2026-04-10
**Status:** Documented — decision pending

## Inventory

5 external governance surfaces identified outside repo control:

| Surface | Location | Influence | Risk | Sync |
|---|---|---|---|---|
| Hermes profile | `~/.hermes/profiles/antigravity/config.yaml` | Model selection, MCP connections, terminal behavior | Medium | Advisory sync only |
| Gemini MCP config | `~/.gemini/antigravity/mcp_config.json` | MCP server connections for Gemini runtime | Medium | No sync |
| Zera cron jobs | `~/.hermes/profiles/zera/cron/jobs.json` | Scheduled self-evolution, intelligence gathering | High | No sync |
| Zera cron individual | `~/.hermes/profiles/zera/cron/*.json` | Individual scheduled job definitions | High | No sync |
| Zera system prompt | `~/.hermes/profiles/zera/system_prompt.md` (if exists) | Actual persona content loaded by LLM | Critical | Manual operator discipline |

## Recommended Actions

### Option A: Import into Repo Governance
- Copy external configs into `configs/orchestrator/external/` directory
- Create `scripts/external_config_sync.py` for bidirectional sync
- Add parity checks to `swarmctl.py doctor`
- External files become read-only mirrors of repo source

### Option B: Quarantine with Documentation
- Document each external surface in `docs/guides/external_governance.md`
- Add health checks that verify external configs are consistent with repo intent
- Accept external surfaces as operational dependencies with documented drift risk

### Option C: Hybrid (Recommended)
- Import critical governance surfaces (Zera system prompt, cron jobs) into repo
- Document non-critical surfaces (Hermes profile, Gemini MCP) as external dependencies
- Add parity checks that warn (not fail) on drift

## Decision Required

| Surface | Recommended | Effort |
|---|---|---|
| Zera system prompt | Import to repo (Option A) | Low — file copy + prompt assembly |
| Zera cron jobs | Import to `configs/tooling/background_jobs.yaml` (Option A) | Low — merge |
| Hermes profile | Document as external dep (Option B) | Low — documentation |
| Gemini MCP config | Document as external dep (Option B) | Low — documentation |

## Implementation (When Approved)

```bash
# 1. Import Zera system prompt
cp ~/.hermes/profiles/zera/system_prompt.md configs/personas/zera/runtime_system_prompt.md
# 2. Import Zera cron jobs
python3 -c "
import json
with open(os.path.expanduser('~/.hermes/profiles/zera/cron/jobs.json')) as f:
    jobs = json.load(f)
# Merge into configs/tooling/background_jobs.yaml
"
# 3. Document external dependencies
cat > docs/guides/external_governance.md << 'EOF'
# External Governance Dependencies
...
EOF
# 4. Add parity check to swarmctl.py doctor
```

## Residual Risk (If Deferred)

- Parallel governance plane cannot be audited or rolled back by repo
- Zera behavior depends on external system prompt that may drift from repo persona docs
- Cron jobs may introduce unreviewed behavior changes
- Operator cannot verify system state from repo alone
