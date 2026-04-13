# KI_CAPTURE_HERMES_MCP_ACCESS_2026-04-10

## Context
- **task_id**: a7adbbcf-6b8b-4d75-b41a-8c2851e772d7
- **task_type**: Configuration Repair / System Orchestration
- **complexity**: C3 (Medium)
- **model_tier**: Senior Autonomous Agent (Tier 1 Core System)
- **workflow**: /self-learning-retro

## Problem
- **symptom**: Hermes agent reported "failed" status for external MCP servers in diagnostic dashboards. `hermes mcp list` initially returned "No MCP servers configured" even when sections existed in `config.yaml`.
- **impact**: Total loss of advanced capabilities (Sequential Thinking, GitHub, Search, Context retrieval) for the Hermes agent.
- **trigger**: Consolidation of Hermes profiles on 2026-04-09 and move to the unified `zera` profile with mismatched configuration keys.

## Root Cause
- **technical_cause**: 
  1. **Schema Mismatch**: Profile configurations in Hermes require the `mcp_servers` key to be at the **root level** (top level) of the YAML file. In previous states, it was either named `mcp:` (global standard only) or indented inside other blocks (like `platform_toolsets`).
  2. **Environment Isolation**: The `hermes` process launches MCP servers in a sub-shell that often misses `nvm` paths and `.env` variables, leading to startup errors or timeouts.
  3. **Path Drift**: The `filesystem` server was configured with an outdated project path (`/Users/user/antigravity-core-v5-refactor`).
- **process_cause**: Incremental configuration edits without verifying the resulting effective config through the CLI tool itself (`hermes mcp list`).

## Fix / Decision
- **summary**: 
  1. Consolidated all MCP server definitions into a single **top-level** `mcp_servers` block in `~/.hermes/profiles/zera/config.yaml`.
  2. Wrapped all server commands in `bash -lc` that sources both the profile's `.env` and `nvm.sh` beforehand.
  3. Corrected all absolute paths and removed conflicting built-in tool aliases (e.g., `memory`).
- **rejected_alternatives**: Using `mcp:` key (only works for global config) or nesting under toolsets (not supported for auto-discovery).

## Verification
- **commands**: `bash -lc "hermes mcp list"` and `bash -lc "hermes mcp test filesystem"`
- **expected_result**: List shows all servers as `enabled`, and the test successfully connects and lists `stdio` tools.
- **actual_result**: `✓ enabled` for all 11 servers; `filesystem` test returned 10 tools including `read_file` and `list_directory`.

## Reusable Pattern
- **pattern_file**: `docs/patterns/HERMES_ROBUST_MCP_WRAPPING_2026-04-10.md`
- **applicability**: Any Hermes profile configuration where MCP servers depend on Node.js or environment variables.
- **constraints**: Requires `bash` and correct paths to `nvm` and `.env`.

## Policy / Routing Implications
- **rules_affected**: No rules changed, but the "Premium Design" principle should apply to how we structure the `.env` files.
- **skills_affected**: `telegram-bot` and `telegram-miniapp` may now rely on these restored MCP tools.
- **mcp_profile_affected**: `zera` (Profile-specific toolset restored).

## Follow-ups
- **backlog_items**: Verify the 401 errors for Gemini models detected in `errors.log`; consolidate the 164 backup profiles to free up space.
- **priority**: P1
