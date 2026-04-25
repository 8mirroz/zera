# Zera/Hermes Runtime Control Plane v2 Migration Plan

## Overview
This document outlines the staged rollout of the v2 Runtime Control Plane overlay. The strategy emphasizes safety, maintaining backward compatibility with the `v1` base configuration, and validating each capability block progressively.

## Phase 1: Stabilization & Foundation (Current)
*   [x] Generate `zera_runtime_control_plane.v2.json` overlay.
*   [x] Place overlay in `/Users/user/zera/configs/runtime/`.
*   [x] Document audit findings, test plans, and rollback procedures.
*   [ ] Implement JSON schema validation for the overlay format.
*   [ ] De-duplicate tools: Ensure `obsidian-disk` is fully disabled in favor of `obsidian`.

## Phase 2: MCP Capability Registry Rollout
*   [ ] Parse the new `mcp_capability_matrix` block in the runtime.
*   [ ] Verify that all required secrets (e.g., `STITCH_API_KEY`, `TWENTY_FIRST_API_KEY`) are properly resolved via environment variables without hardcoding.
*   [ ] Execute a test run of the `safe_default` profile to ensure the agent correctly infers its allowed tools.

## Phase 3: Memory Control Plane Activation
*   [ ] Route all explicit project documentation and durable logic updates to Obsidian.
*   [ ] Route all semantic queries to LightRAG.
*   [ ] Route volatile execution context to the standard memory MCP.
*   [ ] Test the semantic hash deduplication logic to prevent redundant artifact generation in Obsidian.

## Phase 4: Archicad Runtime Hardening (BIM Bridge)
*   [ ] Explicitly invoke the `bim_archicad` profile.
*   [ ] Verify the 120s extended timeout is applied.
*   [ ] Verify the `archicad_session_check` and port availability preflights.
*   [ ] **CRITICAL:** Perform a BIM handoff explicitly in `dry_run` / `preview` mode first.
*   [ ] Ensure live mutations are blocked until a manual approval gate is cleared.

## Phase 5: Agentic Orchestration Shift
*   [ ] Map existing linear workflows to the new role-based swarm model.
*   [ ] Test the `Governor` role's ability to block unsafe filesystem writes based on `blocked_patterns`.
*   [ ] Verify the execution handoff between `Planner`, `Implementer`, and `Validator` agents.

## Phase 6: Observability & Reporting
*   [ ] Standardize runtime logs using the new `trace_schema`.
*   [ ] Automate the generation of the `latest_health_report.md` on system startup.
*   [ ] Automate the generation of the `latest_drift_report.md` during the analysis phase of workflows.
