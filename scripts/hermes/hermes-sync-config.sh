#!/bin/bash
# ============================================
# ZeRa ↔ Antigravity Core Integration
# Syncs runtime-adjacent configs from Antigravity Core → Hermes.
# Secret value copying is opt-in; default mode only validates references.
# Usage: bash scripts/hermes-sync-config.sh [--dry-run] [--sync-secrets]
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HERMES_ENV="$HOME/.hermes/.env"
HERMES_CONFIG="$HOME/.hermes/config.yaml"
HERMES_PROFILE="$HOME/.hermes/profiles/zera/config.yaml"
GEMINI_CONFIG="$HOME/.gemini/zera/mcp_config.json"
DRY_RUN=false
SYNC_SECRETS=false

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            echo "🔍 DRY RUN — no changes will be made"
            ;;
        --sync-secrets)
            SYNC_SECRETS=true
            ;;
    esac
    shift
done

log() { echo -e "\033[0;34m[SYNC]\033[0m $1"; }
ok()  { echo -e "\033[0;32m[OK]\033[0m   $1"; }
warn(){ echo -e "\033[1;33m[WARN]\033[0m $1"; }

# ============================================
# 1. Validate API Key References for Hermes
# ============================================
sync_api_keys() {
    log "Validating API key references for Hermes"
    
    if [ -f "$PROJECT/.env" ]; then
        # Keys available to Hermes. Secret values are only copied with --sync-secrets.
        local keys=(
            "OPENROUTER_API_KEY"
            "GEMINI_API_KEY"
            "GROQ_API_KEY"
            "CLOUDFLARE_API_TOKEN"
            "HF_TOKEN"
            "GITHUB_PERSONAL_ACCESS_TOKEN"
            "CONTEXT7_API_KEY"
            "PERPLEXITY_API_KEY"
            "SUPABASE_ACCESS_TOKEN"
            "STITCH_API_KEY"
            "QDRANT_API_KEY"
            "COMPOSIO_API_KEY"
            "MAGIC_API_KEY"
            "EXA_API_KEY"
            "TAVILY_API_KEY"
            "FIRECRAWL_API_KEY"
            "FAL_KEY"
            "MEMU_API_KEY"
        )
        
        for key in "${keys[@]}"; do
            value=$(grep "^${key}=" "$PROJECT/.env" 2>/dev/null | head -1 | cut -d'=' -f2-)
            if [ -n "$value" ] && [ "$value" != "" ]; then
                if [ "$SYNC_SECRETS" = true ]; then
                    current=$(grep "^${key}=" "$HERMES_ENV" 2>/dev/null | head -1 | cut -d'=' -f2-)
                    if [ "$current" != "$value" ]; then
                        if [ "$DRY_RUN" = true ]; then
                            warn "[DRY RUN] Would update $key"
                        else
                            if grep -q "^${key}=" "$HERMES_ENV" 2>/dev/null; then
                                sed -i '' "s|^${key}=.*|${key}=${value}|" "$HERMES_ENV"
                            else
                                echo "${key}=${value}" >> "$HERMES_ENV"
                            fi
                            ok "Synced $key"
                        fi
                    fi
                else
                    ok "Reference available for $key"
                fi
            fi
        done
    else
        warn "No .env found in Antigravity Core project"
        warn "Using environment references only; secret values are not copied by default"
    fi
}

# ============================================
# 2. Sync Skills
# ============================================
sync_skills() {
    log "Syncing skills from Antigravity Core → Hermes"
    
    mkdir -p "$HOME/.hermes/skills/zera"
    local count=0
    
    # Superpowers
    for skill_dir in "$PROJECT"/configs/skills/superpowers/*/; do
        skill_name=$(basename "$skill_dir")
        if [ -f "$skill_dir/SKILL.md" ]; then
            if [ "$DRY_RUN" = false ]; then
                cp "$skill_dir/SKILL.md" "$HOME/.hermes/skills/zera/${skill_name}.md" 2>/dev/null
            fi
            ok "skill: $skill_name"
            ((count++))
        fi
    done
    
    # Domain skills
    for skill_dir in "$PROJECT"/configs/skills/*/; do
        skill_name=$(basename "$skill_dir")
        if [ -f "$skill_dir/SKILL.md" ] && [[ ! "$skill_name" =~ ^(superpowers|packs|zera-) ]]; then
            if [ "$DRY_RUN" = false ]; then
                cp "$skill_dir/SKILL.md" "$HOME/.hermes/skills/zera/${skill_name}.md" 2>/dev/null
            fi
            ok "domain: $skill_name"
            ((count++))
        fi
    done
    
    ok "$count skills synced"
}

# ============================================
# 3. Sync MCP Server configs
# ============================================
sync_mcp_configs() {
    log "Checking MCP server configurations"
    
    if [ -f "$PROJECT/configs/tooling/mcp_profiles.json" ]; then
        # Parse and display MCP servers
        local servers=$(python3 -c "
import json
data = json.load(open('$PROJECT/configs/tooling/mcp_profiles.json'))
servers = data.get('servers', {})
for name, cfg in servers.items():
    cmd = cfg.get('command', 'N/A')
    args = cfg.get('args', [])
    print(f'  {name}: {cmd} {\" \".join(args)}')
" 2>/dev/null)
        
        if [ -n "$servers" ]; then
            ok "MCP servers in Antigravity Core:"
            echo "$servers"
        else
            warn "No MCP servers found in Antigravity Core profiles"
        fi
    fi
}

# ============================================
# 4. Sync adapter contract references
# ============================================
sync_adapter_contract_refs() {
    log "Syncing adapter contract references (repo semantics)"

    local refs=(
        "$PROJECT/configs/tooling/zera_client_profiles.yaml"
        "$PROJECT/configs/adapters/hermes/adapter.yaml"
        "$PROJECT/configs/adapters/hermes/agent-map.yaml"
        "$PROJECT/configs/tooling/zera_mode_router.json"
        "$PROJECT/configs/tooling/zera_growth_governance.json"
    )

    for ref in "${refs[@]}"; do
        if [ -f "$ref" ]; then
            ok "contract ref exists: ${ref#$PROJECT/}"
        else
            warn "missing contract ref: $ref"
        fi
    done

    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would enforce zera_adapter_contract block in $HERMES_PROFILE"
        warn "[DRY RUN] Would enforce zera_command_control parity fields in $GEMINI_CONFIG"
        return
    fi

    python3 - "$HERMES_PROFILE" "$PROJECT" <<'PY'
import sys
from pathlib import Path
import yaml

profile = Path(sys.argv[1])
project = Path(sys.argv[2])
data = {}
if profile.exists():
    with profile.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
        if isinstance(loaded, dict):
            data = loaded

data["zera_adapter_contract"] = {
    "semantics_source": "repo",
    "command_registry_ref": str(project / "configs/tooling/zera_command_registry.yaml"),
    "client_profiles_ref": str(project / "configs/tooling/zera_client_profiles.yaml"),
    "adapter_ref": str(project / "configs/adapters/hermes/adapter.yaml"),
    "agent_map_ref": str(project / "configs/adapters/hermes/agent-map.yaml"),
    "mode_router_ref": str(project / "configs/tooling/zera_mode_router.json"),
    "growth_governance_ref": str(project / "configs/tooling/zera_growth_governance.json"),
    "branch_policy_ref": str(project / "configs/tooling/zera_branching_policy.yaml"),
    "default_namespace": "zera:*",
    "parity_mode": "strict_reference",
    "degrade_paths": {
        "unsupported_command": "zera:plan",
        "unsupported_transport": "repo_native_contract",
        "unsupported_tool_surface": "propose_and_request_review",
    },
    "transport": {
        "mode": "provider_routed_chat_runtime",
        "profile": "zera",
    },
}
data["secret_policy"] = {
    "env_ref_only": True,
    "inline_secret_forbidden": True,
}

with profile.open("w", encoding="utf-8") as fh:
    yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False)
PY
    ok "Hermes profile contract block synchronized"

    mkdir -p "$(dirname "$GEMINI_CONFIG")"
    python3 - "$GEMINI_CONFIG" "$PROJECT" <<'PY'
import json
import sys
from pathlib import Path

cfg_path = Path(sys.argv[1])
project = Path(sys.argv[2])
data = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

control = data.setdefault("zera_command_control", {})
control["command_registry"] = str(project / "configs/tooling/zera_command_registry.yaml")
control["client_profiles"] = str(project / "configs/tooling/zera_client_profiles.yaml")
control["branching_policy"] = str(project / "configs/tooling/zera_branching_policy.yaml")
control["mode_router"] = str(project / "configs/tooling/zera_mode_router.json")
control["growth_governance"] = str(project / "configs/tooling/zera_growth_governance.json")
control["default_command_namespace"] = "zera:*"
control["semantics_source"] = "repo"
control["parity_mode"] = "strict_reference"
control["degrade_paths"] = {
    "unsupported_command": "zera:plan",
    "unsupported_transport": "repo_native_contract",
    "unsupported_tool_surface": "propose_and_request_review",
}
control["transport"] = {
    "mode": "mcp_orchestrated_chat_runtime",
    "client": "gemini",
}

data["secret_policy"] = {
    "env_ref_only": True,
    "inline_secret_forbidden": True,
}

cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
    ok "Gemini MCP config contract block synchronized"
}

# ============================================
# 5. Secret hygiene checks
# ============================================
check_secret_hygiene() {
    log "Checking adapter secret hygiene"

    local patterns='(AIza[0-9A-Za-z_-]{20,}|sbp_[0-9a-f]{20,}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})'
    local files=(
        "$HERMES_PROFILE"
        "$GEMINI_CONFIG"
    )

    local found=0
    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            continue
        fi
        if rg -n "$patterns" "$file" >/dev/null 2>&1; then
            warn "Potential inline secret pattern found in $file"
            found=1
        else
            ok "No obvious inline secret pattern in $file"
        fi
    done

    if [ "$found" -ne 0 ]; then
        warn "Secret hygiene check flagged potential inline secrets. Prefer env references."
    fi
}

# ============================================
# 6. Sync Workspace Config
# ============================================
sync_workspace() {
    log "Checking workspace configuration"
    
    # Check if Hermes is pointed to Antigravity Core
    local hermes_cwd=$(grep "cwd:" "$HERMES_CONFIG" 2>/dev/null | head -1 | awk '{print $2}')
    
    if [ "$hermes_cwd" = "$PROJECT" ]; then
        ok "Hermes workspace already set to Antigravity Core"
    else
        warn "Hermes workspace: $hermes_cwd"
        if [ "$DRY_RUN" = false ]; then
            hermes config set workspace.cwd "$PROJECT" 2>/dev/null
            hermes config set workspace.project_root "$PROJECT" 2>/dev/null
            ok "Workspace updated to: $PROJECT"
        fi
    fi
}

# ============================================
# 7. Show Model Mapping
# ============================================
show_model_mapping() {
    log "Model mapping (Antigravity Core → Hermes)"
    
    echo ""
    echo "  Antigravity Role           →  Hermes Default"
    echo "  ────────────────────────────────────────────"
    echo "  BUILDER_A (qwen3.6-plus)   →  ✓ Primary model"
    echo "  BUILDER_B (qwen3.6-plus)   →  Fallback model"
    echo "  COUNCIL (qwen3.5-plus)     →  Deep reasoning"
    echo "  REVIEWER (qwen3.6-plus)    →  Code review"
    echo "  FALLBACK (gemini-2-flash)  →  Emergency"
    echo ""
}

# ============================================
# MAIN
# ============================================
main() {
    echo ""
    echo -e "\033[0;36m╔══════════════════════════════════════════════════════════╗\033[0m"
    echo -e "\033[0;36m║  ⚕  ZeRa ↔ Antigravity Core Configuration Sync            ║\033[0m"
    echo -e "\033[0;36m╚══════════════════════════════════════════════════════════╝\033[0m"
    echo ""
    
    sync_api_keys
    sync_skills
    sync_mcp_configs
    sync_adapter_contract_refs
    check_secret_hygiene
    sync_workspace
    show_model_mapping
    
    echo ""
    echo -e "\033[0;32m✅ Sync complete!\033[0m"
    echo ""
    echo "Next steps:"
    echo "  hermes status     — check overall status"
    echo "  hermes doctor     — run diagnostics"
    echo "  hermes chat       — start chatting"
    echo "  hermes tools list — see available tools"
    echo "  bash scripts/hermes-sync-config.sh --sync-secrets  — opt-in secret copy"
    echo ""
}

main "$@"
