# PATTERN: Robust MCP Server Wrapping in Hermes Profiles

## Problem Statement
MCP servers in Hermes Agent profiles often fail to initialize or lack necessary tools/capabilities because:
1. They are executed in a clean shell that lacks Node.js (`npx`) or NVM paths.
2. They do not have access to environmental secrets defined in the profile's `.env`.
3. They are misconfigured in the `config.yaml` due to incorrect key names or indentation.

## The Pattern: "The Shell-Wrapped Exec"

Instead of calling the server command directly, wrap it in a `bash -lc` command that sets up the environment first.

### Implementation

1. **Location**: The configuration must be in the `mcp_servers:` section at the **root level** of `~/.hermes/profiles/<profile>/config.yaml`.
2. **Command Structure**:
```yaml
mcp_servers:
  <name>:
    command: /bin/bash
    args:
    - -lc
    - source "$HOME/.hermes/profiles/<profile>/.env" >/dev/null 2>&1 && 
      source "$HOME/.nvm/nvm.sh" >/dev/null 2>&1 && 
      exec npx -y <package-name> [args...]
    enabled: true
```

### Key Components

- **`/bin/bash -lc`**: Invokes a login shell (loading profile files) and executes the command.
- **`source .../.env`**: Explicitly loads the profile's environment variables (secrets, keys).
- **`source .../nvm.sh`**: Ensures Node.js and `npx` are available in the path.
- **`exec`**: Replaces the shell process with the MCP server process, ensuring signals (like SIGTERM) are passed correctly.
- **`>/dev/null 2>&1`**: Prevents shell initialization noise from polluting the `stdio` stream of the MCP protocol.

## Applicability
- **Node-based servers**: Always use this if using `npx`.
- **Python-based servers**: Use this if you need specific `venv` or `uv` environments.
- **Secrets-dependent servers**: Always use this to ensure `EXA_API_KEY`, `GITHUB_TOKEN`, etc. are correctly inherited.

## Constraints
- Windows: This pattern requires adjustments for PowerShell or WSL.
- Performance: Spawning a shell adds a slight delay (~100-200ms) to the server startup.
