#!/usr/bin/env bash
# Configure optional Obsidian MCP bridge for local AI tooling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CLINE_SETTINGS="${CLINE_SETTINGS_PATH:-$HOME/Library/Application Support/Antigravity/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json}"
OBSIDIAN_STATE="$HOME/Library/Application Support/obsidian/obsidian.json"
GEMINI_MCP_CONFIG="${GEMINI_MCP_CONFIG_PATH:-$HOME/.gemini/zera/mcp_config.json}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ -z "${OBSIDIAN_API_KEY:-}" ]]; then
  log_error "Set OBSIDIAN_API_KEY before running this script."
  echo "Example:"
  echo "  export OBSIDIAN_API_KEY='your-key-from-obsidian-local-rest-api'"
  exit 1
fi

if [[ ! -f "$OBSIDIAN_STATE" ]]; then
  log_error "Obsidian state file not found: $OBSIDIAN_STATE"
  exit 1
fi

VAULT_PATH="$(python3 - <<'PY'
import json
from pathlib import Path

state = Path.home() / "Library/Application Support/obsidian/obsidian.json"
data = json.loads(state.read_text(encoding="utf-8"))
vaults = data.get("vaults", {})
ranked = []
for item in vaults.values():
    if not isinstance(item, dict):
        continue
    path = item.get("path")
    if not path:
        continue
    score = int(bool(item.get("open"))) * 10 + int(item.get("ts", 0))
    ranked.append((score, path))
ranked.sort(reverse=True)
print(ranked[0][1] if ranked else "")
PY
)"

if [[ -z "$VAULT_PATH" ]]; then
  log_error "Could not determine an active Obsidian vault."
  exit 1
fi

mkdir -p "$(dirname "$CLINE_SETTINGS")"
if [[ ! -f "$CLINE_SETTINGS" ]]; then
  echo '{"mcpServers":{}}' > "$CLINE_SETTINGS"
fi

log_info "Configuring obsidian-mcp-server in Cline settings..."
python3 - "$CLINE_SETTINGS" "$VAULT_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
vault_path = sys.argv[2]
raw = settings_path.read_text(encoding="utf-8").strip() or '{"mcpServers":{}}'
data = json.loads(raw)
mcp = data.setdefault("mcpServers", {})
mcp["obsidian-mcp-server"] = {
    "command": "npx",
    "args": ["obsidian-mcp-server"],
    "env": {
        "OBSIDIAN_API_KEY": os.environ["OBSIDIAN_API_KEY"],
        "OBSIDIAN_BASE_URL": os.environ.get("OBSIDIAN_BASE_URL", "http://127.0.0.1:27123"),
        "OBSIDIAN_VERIFY_SSL": os.environ.get("OBSIDIAN_VERIFY_SSL", "false"),
        "OBSIDIAN_ENABLE_CACHE": os.environ.get("OBSIDIAN_ENABLE_CACHE", "true"),
        "ANTIGRAVITY_OBSIDIAN_VAULT_PATH": vault_path,
    },
    "disabled": False,
    "autoApprove": [],
}
settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

log_success "Obsidian MCP configured."
log_info "Vault path: $VAULT_PATH"
log_info "Cline settings: $CLINE_SETTINGS"

mkdir -p "$(dirname "$GEMINI_MCP_CONFIG")"
python3 - "$GEMINI_MCP_CONFIG" "$VAULT_PATH" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
vault_path = sys.argv[2]
if config_path.exists():
    raw = config_path.read_text(encoding="utf-8").strip() or "{}"
    data = json.loads(raw)
else:
    data = {}

data["version"] = str(data.get("version") or "1.0")
data["active_vault_path"] = vault_path
data["project_memory_root"] = "AI Projects"
data["preferred_human_memory"] = "obsidian"
data["preferred_library_context"] = "context7"
data["workflow_sequence"] = [
    "/obsidian-project",
    "repo-memory-refresh",
    "drift-validator",
    "triage",
    "task-blueprint-selection",
    "/bootstrap",
    "swarm-review",
    "self-learning-retro",
    "build-memory-capture",
]

summary = dict(data.get("mcp_servers") or {})
summary["context7"] = {"enabled": True}
summary["obsidian-mcp-server"] = {
    "enabled": True,
    "transport": "stdio",
    "command": "npx",
    "args": ["obsidian-mcp-server"],
    "env_keys": [
        "OBSIDIAN_API_KEY",
        "OBSIDIAN_BASE_URL",
        "OBSIDIAN_VERIFY_SSL",
        "OBSIDIAN_ENABLE_CACHE",
    ],
}
data["mcp_servers"] = summary
config_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

log_info "Gemini MCP config: $GEMINI_MCP_CONFIG"
log_info "To refresh generated local MCP transport inside the same file:"
echo "  python3 \"$PROJECT_ROOT/repos/packages/agent-os/scripts/generate_mcp_transport.py\" --write-local"
log_warn "Direct vault file access remains the primary integration path."
log_info "Project bootstrap command:"
echo "  python3 \"$PROJECT_ROOT/scripts/obsidian_project.py\" init --project-slug my-project"
echo "  bash \"$PROJECT_ROOT/scripts/bootstrap_obsidian_project.sh\" /path/to/project"
