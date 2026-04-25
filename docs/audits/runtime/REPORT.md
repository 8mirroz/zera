# Runtime Control Plane v2 Audit & Upgrade Report

## 1. Executive Summary

An audit was conducted on the current Zera/Hermes runtime configuration, encompassing commands, modes, policies, and MCP integrations. The previous configuration functioned effectively as a flat registry but lacked the robust control plane mechanisms necessary for safe, scalable agent orchestration. 

The primary improvement introduces an overlay configuration (`zera_runtime_control_plane.v2.json`) that transforms the flat config into a governed **Runtime Control Plane v2**.

## 2. Key Findings from Audit

1. **Architecture:** The previous setup combined runtime, memory, commands, MCPs, and workflows into a single layer, increasing the risk of configuration drift and chaos as the system scaled.
2. **MCP Registry:** Lacked a capability matrix. Agents lacked explicit knowledge of when and how to safely utilize specific MCPs.
3. **Startup Process:** Missing staged startup procedures. A slow or broken optional MCP could halt the entire runtime initialization.
4. **Archicad Integration:** The Archicad MCP was disabled with a short timeout (30s). Simply enabling it posed risks of timeout cascades and unsafe live mutations.
5. **Memory Management:** Multiple memory layers (Obsidian, LightRAG, Agent Memory) existed without a formalized lifecycle or deduplication policy, leading to potential "memory drift".
6. **Governance & Security:** While a `secret_policy` existed, there was no comprehensive policy for destructive tools (e.g., direct filesystem writes, live Archicad mutations, git commits).
7. **Tool Duplication:** Redundant tools (e.g., `obsidian` vs `obsidian-disk`) created conflicting sources of truth.

## 3. Improvements Implemented (v2 Overlay)

The new overlay config addresses these issues without breaking the underlying `v1` base:

* **Capability Matrix:** Added explicit definitions for each MCP, detailing capabilities, risk tiers, and read/write access.
* **Runtime Profiles:** Introduced modes like `safe_default`, `research_intelligence`, `design_build`, `bim_archicad`, and `repo_governance` to load only necessary tools.
* **Staged Startup:** Implemented a circuit-breaker based startup policy prioritizing core memory and reasoning before optional extensions.
* **Archicad Activation Protocol:** Hardened the BIM bridge. It now requires a 120s timeout, read-only preflights, dry runs, and explicit human approval for live mutations.
* **Memory Control Plane:** Formalized Obsidian as the human-readable Source of Truth (SoT), LightRAG for semantic retrieval, and MCP Memory for volatile session context. Added deduplication and write-gate rules.
* **Agent Orchestration Graph:** Shifted from linear workflows to a role-based swarm model (Governor, Architect, Planner, Implementer, Validator, Memory Curator).
* **Quality Gates & Observability:** Added preflight, before-mutation, and after-mutation checks, alongside a formalized trace schema for runtime logs.

## 4. Next Steps

Refer to `MIGRATION_PLAN.md` for the rollout strategy, and `TEST_PLAN.md` to validate the new control plane. The legacy config remains intact, and `ROLLBACK.md` contains procedures to revert if necessary.
