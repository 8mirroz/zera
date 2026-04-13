# MCP Profile Manager

CLI that selects an MCP profile based on task type and complexity and prints a JSON recommendation.

## Usage
```bash
node src/index.js --task-type T4 --complexity C4
# or
npx . --task-type T2 --complexity C2
```

## Config
- Default: `configs/tooling/mcp_profiles.json`
- Override: `--config /path/to/mcp_profiles.json`

## Output
JSON with `profile`, `servers`, `optional_servers`, and `allowlist`.
