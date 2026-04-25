---
name: pi-cli
description: Use for managing pi packages, themes, and orchestrating subagents via the pi CLI tool.
---

# Pi CLI Extension Skill

## Overview
This skill enables Zera to leverage the `pi` CLI tool for package management, environment enhancement, and advanced agent orchestration.

## Capabilities

### 1. Package Management
- **Search**: Explore available packages at [pi.dev/packages](https://pi.dev/packages).
- **Install**: Use `pi install <source>` (e.g., `npm:package-name` or `git:url`).
- **Local Mode**: Use `-l` for project-specific installations in `.pi/settings.json`.

### 2. Environment & Aesthetics
- **Themes**: Apply premium themes from `@ifi/oh-pi-themes` by modifying `~/.pi/agent/settings.json`.
- **Visualization**: Use `pi-mermaid` for ASCII diagramming and `pi-charts` for data viz.

### 3. Agent Orchestration & Loops
- **Autonomous Loops**: Use `@lnilluv/pi-ralph-loop` with `/ralph <path>` for self-healing coding cycles (requires `RALPH.md`).
- **Subagents**: Utilize `pi-subagents` and `pi-crew` for spawning specialized workers.
- **MCP Integration**: Access the `mcp` tool via the `pi-mcp-adapter` for universal tool discovery.

### 4. Advanced Research & Memory
- **Research**: Use `pi-librarian` for deep GitHub repo investigation.
- **Memory**: `pi-agent-memory` provides cross-session state (connected to `claude-mem`).
- **Security**: `pi-secret-guard` automatically blocks commits containing secrets.

## Standard Procedures

### Installing and Configuring
1. **Identify**: Find the required package on `pi.dev`.
2. **Install**: Run `run_command` with `pi install npm:<pkg>`.
3. **Validate**: Check `~/.pi/agent/settings.json` for successful registration.
4. **Optimize**: Adjust `toolDisplay` and `agentMemory` settings in `settings.json` for minimal context noise.

### Autonomous Coding (RALPH)
1. **Create `RALPH.md`**: Define commands (tests, lint) and the task prompt.
2. **Launch**: Run `pi /ralph .`.
3. **Monitor**: The loop will run until `max_iterations` or `completion_promise` is met.

### Using MCP Proxy
When the `pi` MCP server is active, use the `mcp` tool to:
- `mcp({ search: "..." })` to find specialized tools.
- `mcp({ tool: "...", args: "..." })` to execute them.

## Governance
All `pi` operations must respect the **Zero Law**. Installations should be justified by the task and avoid environmental clutter.
