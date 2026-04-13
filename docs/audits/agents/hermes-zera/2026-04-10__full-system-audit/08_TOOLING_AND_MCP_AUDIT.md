# 08. Tooling and MCP Audit

## Readiness Matrix
| Area | Maturity | Notes |
|---|---|---|
| Repo MCP profile schema | workable | `mcp_profiles.json` is readable and routeable |
| MCP validator | fragile | exits `0` despite failed routing check |
| Hermes/Gemini parity | fragile | `strict_reference` declared, not proven |
| Tool discoverability | partial | names split across config, scripts, and operator profiles |
| Dangerous overlap | medium | repo-side MCP and home-profile MCP diverge silently |

## Key Findings
1. `scripts/test_mcp_profiles.py` is misleading green.
2. `mcp_profiles.json` under-describes the live client surface compared with Gemini config.
3. Hermes and Gemini adapters share semantics refs but not a verified common tool surface; `gemini` is declared as an executable client profile but the current bridge is effectively render-only.
4. Zera cron sidecar can run outside repo-governed `background_jobs.yaml`.
5. Tool readiness reports are distributed across repo outputs, home configs, and runtime traces rather than one canonical ledger.
6. `zera_client_profiles.yaml` contains parity and transport metadata that is mostly narrative because runtime consumers do not enforce most of it.

## Retirement / Rewrite Candidates
- Rewrite `scripts/test_mcp_profiles.py` as a real contract test with fail-fast exit codes.
- Retire `.bak` validator copies from trust paths.
- Collapse duplicate trace schemas or enforce mirror parity automatically.

## Phase-Gating Recommendations
- No benchmark-driven decisions while MCP validator remains false-positive.
- No “strict parity” claims until Hermes and Gemini surfaces are diff-tested.
- No autonomous promotion relying on external cron jobs outside repo policy.
