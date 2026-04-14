#!/bin/bash
# ============================================================
# ZeRa ↔ Antigravity Core Integration — Hardened Sync Layer
# Syncs runtime-adjacent configs from Antigravity Core → Hermes.
# Default mode validates references and syncs non-secret artifacts.
# Secret value copying is opt-in.
#
# Usage:
#   bash scripts/hermes-sync-config.sh [options]
#
# Options:
#   --dry-run             Preview changes only
#   --sync-secrets        Copy secret values from project .env → Hermes .env
#   --strict              Exit non-zero on missing refs / failed validations
#   --clean-skills        Remove stale ZeRa skills in Hermes not present in source
#   --no-backup           Do not create backups before file mutation
#   --verbose             Print extra diagnostics
#   --project-root PATH   Override auto-detected project root
#   --hermes-home PATH    Override default Hermes home (~/.hermes)
#   --report PATH         Write JSON sync report
#   -h, --help            Show help
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HERMES_HOME="${HOME}/.hermes"
GEMINI_HOME="${HOME}/.gemini/zera"
DRY_RUN=false
SYNC_SECRETS=false
STRICT=false
CLEAN_SKILLS=false
BACKUP=true
VERBOSE=false
REPORT_PATH=""

HERMES_ENV=""
HERMES_CONFIG=""
HERMES_PROFILE=""
HERMES_SKILLS_DIR=""
GEMINI_CONFIG=""
BACKUP_DIR=""
TMP_DIR=""

API_AVAILABLE=0
API_SYNCED=0
SKILLS_SYNCED=0
SKILLS_REMOVED=0
REFS_OK=0
REFS_MISSING=0
SECRET_FLAGS=0
WARN_COUNT=0
ERROR_COUNT=0
MCP_COUNT=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

usage() {
    cat <<EOF_USAGE
Usage: bash scripts/hermes-sync-config.sh [options]

Options:
  --dry-run             Preview changes only
  --sync-secrets        Copy secret values from project .env → Hermes .env
  --strict              Exit non-zero on missing refs / failed validations
  --clean-skills        Remove stale ZeRa skills in Hermes not present in source
  --no-backup           Do not create backups before file mutation
  --verbose             Print extra diagnostics
  --project-root PATH   Override auto-detected project root
  --hermes-home PATH    Override default Hermes home (~/.hermes)
  --report PATH         Write JSON sync report
  -h, --help            Show help
EOF_USAGE
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        --sync-secrets)
            SYNC_SECRETS=true
            ;;
        --strict)
            STRICT=true
            ;;
        --clean-skills)
            CLEAN_SKILLS=true
            ;;
        --no-backup)
            BACKUP=false
            ;;
        --verbose)
            VERBOSE=true
            ;;
        --project-root)
            shift
            PROJECT="${1:-}"
            ;;
        --hermes-home)
            shift
            HERMES_HOME="${1:-}"
            ;;
        --report)
            shift
            REPORT_PATH="${1:-}"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

HERMES_ENV="$HERMES_HOME/.env"
HERMES_CONFIG="$HERMES_HOME/config.yaml"
HERMES_PROFILE="$HERMES_HOME/profiles/zera/config.yaml"
HERMES_SKILLS_DIR="$HERMES_HOME/skills/zera"
GEMINI_CONFIG="$GEMINI_HOME/mcp_config.json"

REPORT_PATH="${REPORT_PATH:-$HERMES_HOME/state/zera-sync-report.json}"

log()    { echo -e "${BLUE}[SYNC]${NC} $1"; }
ok()     { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()   { WARN_COUNT=$((WARN_COUNT + 1)); echo -e "${YELLOW}[WARN]${NC} $1"; }
err()    { ERROR_COUNT=$((ERROR_COUNT + 1)); echo -e "${RED}[FAIL]${NC}  $1" >&2; }
info()   { [ "$VERBOSE" = true ] && echo -e "${DIM}[INFO]${NC} $1"; }
section(){ echo -e "\n${CYAN}${BOLD}$1${NC}"; }

on_error() {
    local line="$1"
    local cmd="$2"
    err "Failed at line ${line}: ${cmd}"
}
trap 'on_error "$LINENO" "$BASH_COMMAND"' ERR

need_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        err "Required command not found: $cmd"
        exit 1
    fi
}

optional_cmd() {
    command -v "$1" >/dev/null 2>&1
}

ensure_dir() {
    local dir="$1"
    if [ "$DRY_RUN" = true ]; then
        info "[DRY RUN] ensure dir: $dir"
        return
    fi
    mkdir -p "$dir"
}

backup_file() {
    local file="$1"
    [ "$BACKUP" = true ] || return 0
    [ -f "$file" ] || return 0
    ensure_dir "$BACKUP_DIR"
    local dest="$BACKUP_DIR/$(echo "$file" | sed 's#/#__#g')"
    if [ ! -f "$dest" ]; then
        cp "$file" "$dest"
        info "Backup created: $dest"
    fi
}

require_project() {
    if [ ! -d "$PROJECT" ]; then
        err "Project root not found: $PROJECT"
        exit 1
    fi
    if [ ! -d "$PROJECT/configs" ] && [ ! -f "$PROJECT/.env" ]; then
        warn "Project root does not look like Antigravity Core: $PROJECT"
    fi
}

init_runtime_paths() {
    TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t zera-sync)"
    BACKUP_DIR="$TMP_DIR/backups"
    ensure_dir "$HERMES_HOME"
    ensure_dir "$HERMES_HOME/state"
    ensure_dir "$HERMES_HOME/profiles/zera"
    ensure_dir "$GEMINI_HOME"
    ensure_dir "$HERMES_SKILLS_DIR"
}

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT

require_python_yaml() {
    python3 - <<'PY' >/dev/null 2>&1
import yaml
PY
}

read_env_value() {
    local file="$1"
    local key="$2"
    [ -f "$file" ] || return 0
    python3 - "$file" "$key" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
key = sys.argv[2]
for raw in path.read_text(encoding='utf-8').splitlines():
    line = raw.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    if k.strip() == key:
        v = v.strip()
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        print(v)
        break
PY
}

write_env_value() {
    local file="$1"
    local key="$2"
    local value="$3"

    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would set ${key} in ${file}"
        return 0
    fi

    ensure_dir "$(dirname "$file")"
    touch "$file"
    backup_file "$file"

    python3 - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
out = []
replaced = False
for raw in lines:
    line = raw.strip()
    if line.startswith(f"{key}="):
        out.append(f"{key}={value}")
        replaced = True
    else:
        out.append(raw)
if not replaced:
    out.append(f"{key}={value}")
path.write_text("\n".join(out).rstrip() + "\n", encoding='utf-8')
PY
}

copy_file() {
    local src="$1"
    local dest="$2"
    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would copy ${src} → ${dest}"
        return 0
    fi
    ensure_dir "$(dirname "$dest")"
    if [ -f "$dest" ]; then
        backup_file "$dest"
    fi
    cp "$src" "$dest"
}

remove_file() {
    local target="$1"
    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would remove stale file ${target}"
        return 0
    fi
    [ -f "$target" ] || return 0
    backup_file "$target"
    rm -f "$target"
}

sync_api_keys() {
    section "1. API key reference validation"

    local project_env="$PROJECT/.env"
    local keys
    keys=(
        OPENROUTER_API_KEY
        GEMINI_API_KEY
        GROQ_API_KEY
        CLOUDFLARE_API_TOKEN
        HF_TOKEN
        GITHUB_PERSONAL_ACCESS_TOKEN
        CONTEXT7_API_KEY
        PERPLEXITY_API_KEY
        SUPABASE_ACCESS_TOKEN
        STITCH_API_KEY
        QDRANT_API_KEY
        COMPOSIO_API_KEY
        MAGIC_API_KEY
        EXA_API_KEY
        TAVILY_API_KEY
        FIRECRAWL_API_KEY
        FAL_KEY
        MEMU_API_KEY
    )

    if [ ! -f "$project_env" ]; then
        warn "No project .env found at $project_env"
        warn "Secret values remain reference-only unless project .env is available"
        return 0
    fi

    local key value current
    for key in "${keys[@]}"; do
        value="$(read_env_value "$project_env" "$key")"
        if [ -n "$value" ]; then
            API_AVAILABLE=$((API_AVAILABLE + 1))
            if [ "$SYNC_SECRETS" = true ]; then
                current="$(read_env_value "$HERMES_ENV" "$key")"
                if [ "$current" != "$value" ]; then
                    write_env_value "$HERMES_ENV" "$key" "$value"
                    ok "Synced secret ref/value for $key"
                    API_SYNCED=$((API_SYNCED + 1))
                else
                    info "No change for $key"
                fi
            else
                ok "Reference available for $key"
            fi
        else
            info "Missing in project .env: $key"
        fi
    done

    if [ "$SYNC_SECRETS" = false ]; then
        ok "Secret copy disabled — reference validation only"
    fi
}

sync_skills() {
    section "2. Skill sync"

    ensure_dir "$HERMES_SKILLS_DIR"
    local manifest="$HERMES_HOME/state/zera-skills-manifest.txt"
    local tmp_manifest="$TMP_DIR/zera-skills-manifest.txt"
    : > "$tmp_manifest"

    shopt -s nullglob
    local skill_dir skill_name src dest copied_any=false

    # Antigravity Core logic: 3 primary search locations
    local search_paths=(
        "$PROJECT"/configs/skills/superpowers/*/
        "$PROJECT"/configs/skills/*/
        "$PROJECT"/.agents/skills/*/
    )

    for skill_dir in "${search_paths[@]}"; do
        skill_name="$(basename "$skill_dir")"
        src="$skill_dir/SKILL.md"
        dest="$HERMES_SKILLS_DIR/${skill_name}.md"
        
        # Determine kind for logging
        local kind="domain"
        [[ "$skill_dir" == *"/superpowers/"* ]] && kind="superpower"
        [[ "$skill_dir" == *".agents/skills"* ]] && kind="agent-native"

        if [ -f "$src" ]; then
            # Filter out packs and internal zera tools if needed
            [[ "$skill_name" =~ ^(packs|zera-internal) ]] && continue
            
            copy_file "$src" "$dest"
            echo "$dest" >> "$tmp_manifest"
            ok "${kind}: $skill_name"
            SKILLS_SYNCED=$((SKILLS_SYNCED + 1))
            copied_any=true
        fi
    done
    shopt -u nullglob

    if [ "$copied_any" = false ]; then
        warn "No skills found under $PROJECT/configs/skills"
    fi

    if [ "$CLEAN_SKILLS" = true ]; then
        shopt -s nullglob
        local file found
        for file in "$HERMES_SKILLS_DIR"/*.md; do
            found=false
            if [ -s "$tmp_manifest" ] && grep -Fqx "$file" "$tmp_manifest"; then
                found=true
            fi
            if [ "$found" = false ]; then
                remove_file "$file"
                ok "removed stale skill: $(basename "$file")"
                SKILLS_REMOVED=$((SKILLS_REMOVED + 1))
            fi
        done
        shopt -u nullglob
    fi

    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would refresh skill manifest: $manifest"
    else
        cp "$tmp_manifest" "$manifest"
    fi

    ok "$SKILLS_SYNCED skills synchronized"
}

sync_mcp_configs() {
    section "3. MCP surface inspection"

    local mcp_file="$PROJECT/configs/tooling/mcp_profiles.json"
    if [ ! -f "$mcp_file" ]; then
        warn "MCP profiles file not found: $mcp_file"
        return 0
    fi

    local output
    output="$(python3 - "$mcp_file" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding='utf-8'))
servers = data.get('servers', {})
print(len(servers))
for name, cfg in sorted(servers.items()):
    cmd = cfg.get('command', 'N/A')
    args = cfg.get('args', []) or []
    line = " ".join([cmd] + list(args)).strip()
    print(f"{name}\t{line}")
PY
)"

    MCP_COUNT="$(echo "$output" | head -1 | tr -d '[:space:]')"
    if [ -z "$MCP_COUNT" ] || [ "$MCP_COUNT" = "0" ]; then
        warn "No MCP servers declared in $mcp_file"
        return 0
    fi

    ok "Declared MCP servers: $MCP_COUNT"
    echo "$output" | tail -n +2 | while IFS=$'\t' read -r name line; do
        [ -n "$name" ] || continue
        echo "  - $name → $line"
    done
}

sync_adapter_contract_refs() {
    section "4. Adapter contract sync"

    require_python_yaml || {
        err "python3 module 'yaml' is required for YAML contract sync"
        [ "$STRICT" = true ] && exit 1
        return 0
    }

    local refs
    refs=(
        "$PROJECT/configs/tooling/zera_command_registry.yaml"
        "$PROJECT/configs/tooling/zera_client_profiles.yaml"
        "$PROJECT/configs/adapters/hermes/adapter.yaml"
        "$PROJECT/configs/adapters/hermes/agent-map.yaml"
        "$PROJECT/configs/tooling/zera_mode_router.json"
        "$PROJECT/configs/tooling/zera_growth_governance.json"
        "$PROJECT/configs/tooling/zera_branching_policy.yaml"
    )

    local ref missing_any=false
    for ref in "${refs[@]}"; do
        if [ -f "$ref" ]; then
            ok "contract ref exists: ${ref#$PROJECT/}"
            REFS_OK=$((REFS_OK + 1))
        else
            warn "missing contract ref: ${ref#$PROJECT/}"
            REFS_MISSING=$((REFS_MISSING + 1))
            missing_any=true
        fi
    done

    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would synchronize zera_adapter_contract in $HERMES_PROFILE"
        warn "[DRY RUN] Would synchronize zera_command_control in $GEMINI_CONFIG"
        return 0
    fi

    backup_file "$HERMES_PROFILE"
    backup_file "$GEMINI_CONFIG"

    python3 - "$HERMES_PROFILE" "$PROJECT" <<'PY'
import sys
from pathlib import Path
import yaml

profile = Path(sys.argv[1])
project = Path(sys.argv[2])
profile.parent.mkdir(parents=True, exist_ok=True)

data = {}
if profile.exists():
    loaded = yaml.safe_load(profile.read_text(encoding='utf-8'))
    if isinstance(loaded, dict):
        data = loaded

data['zera_adapter_contract'] = {
    'version': 2,
    'semantics_source': 'repo',
    'command_registry_ref': str(project / 'configs/tooling/zera_command_registry.yaml'),
    'client_profiles_ref': str(project / 'configs/tooling/zera_client_profiles.yaml'),
    'adapter_ref': str(project / 'configs/adapters/hermes/adapter.yaml'),
    'agent_map_ref': str(project / 'configs/adapters/hermes/agent-map.yaml'),
    'mode_router_ref': str(project / 'configs/tooling/zera_mode_router.json'),
    'growth_governance_ref': str(project / 'configs/tooling/zera_growth_governance.json'),
    'branch_policy_ref': str(project / 'configs/tooling/zera_branching_policy.yaml'),
    'default_namespace': 'zera:*',
    'parity_mode': 'strict_reference',
    'validation': {
        'on_boot': True,
        'on_sync': True,
        'fail_mode': 'warn_only',
    },
    'degrade_paths': {
        'unsupported_command': 'zera:plan',
        'unsupported_transport': 'repo_native_contract',
        'unsupported_tool_surface': 'propose_and_request_review',
        'missing_contract_ref': 'read_only_reference_mode',
    },
    'transport': {
        'mode': 'provider_routed_chat_runtime',
        'profile': 'zera',
    },
}
data['secret_policy'] = {
    'env_ref_only': True,
    'inline_secret_forbidden': True,
    'sync_secrets_opt_in': True,
}

profile.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
PY
    ok "Hermes profile contract block synchronized"

    python3 - "$GEMINI_CONFIG" "$PROJECT" <<'PY'
import json
import sys
from pathlib import Path

cfg_path = Path(sys.argv[1])
project = Path(sys.argv[2])
cfg_path.parent.mkdir(parents=True, exist_ok=True)

data = {}
if cfg_path.exists():
    raw = cfg_path.read_text(encoding='utf-8').strip()
    if raw:
        data = json.loads(raw)

control = data.setdefault('zera_command_control', {})
control['version'] = 2
control['command_registry'] = str(project / 'configs/tooling/zera_command_registry.yaml')
control['client_profiles'] = str(project / 'configs/tooling/zera_client_profiles.yaml')
control['branching_policy'] = str(project / 'configs/tooling/zera_branching_policy.yaml')
control['mode_router'] = str(project / 'configs/tooling/zera_mode_router.json')
control['growth_governance'] = str(project / 'configs/tooling/zera_growth_governance.json')
control['default_command_namespace'] = 'zera:*'
control['semantics_source'] = 'repo'
control['parity_mode'] = 'strict_reference'
control['validation'] = {
    'on_boot': True,
    'on_sync': True,
    'fail_mode': 'warn_only',
}
control['degrade_paths'] = {
    'unsupported_command': 'zera:plan',
    'unsupported_transport': 'repo_native_contract',
    'unsupported_tool_surface': 'propose_and_request_review',
    'missing_contract_ref': 'read_only_reference_mode',
}
control['transport'] = {
    'mode': 'mcp_orchestrated_chat_runtime',
    'client': 'gemini',
}

data['secret_policy'] = {
    'env_ref_only': True,
    'inline_secret_forbidden': True,
    'sync_secrets_opt_in': True,
}

cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
    ok "Gemini MCP config contract block synchronized"

    if [ "$missing_any" = true ] && [ "$STRICT" = true ]; then
        err "Strict mode: adapter contract refs are incomplete"
        exit 1
    fi
}

check_secret_hygiene() {
    section "5. Secret hygiene"

    local patterns='(AIza[0-9A-Za-z_-]{20,}|sbp_[0-9a-f]{20,}|sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|hf_[A-Za-z0-9]{20,})'
    local files
    files=(
        "$HERMES_PROFILE"
        "$GEMINI_CONFIG"
    )

    local file checker_found=false
    for file in "${files[@]}"; do
        [ -f "$file" ] || continue
        if optional_cmd rg; then
            if rg -n "$patterns" "$file" >/dev/null 2>&1; then
                warn "Potential inline secret pattern found in $file"
                SECRET_FLAGS=$((SECRET_FLAGS + 1))
                checker_found=true
            else
                ok "No obvious inline secret pattern in $file"
            fi
        else
            if grep -En "$patterns" "$file" >/dev/null 2>&1; then
                warn "Potential inline secret pattern found in $file"
                SECRET_FLAGS=$((SECRET_FLAGS + 1))
                checker_found=true
            else
                ok "No obvious inline secret pattern in $file"
            fi
        fi
    done

    if [ "$checker_found" = true ] && [ "$STRICT" = true ]; then
        err "Strict mode: secret hygiene validation failed"
        exit 1
    fi
}

read_workspace_cwd() {
    local file="$1"
    [ -f "$file" ] || return 0
    if require_python_yaml; then
        python3 - "$file" <<'PY'
import sys
from pathlib import Path
import yaml
path = Path(sys.argv[1])
loaded = yaml.safe_load(path.read_text(encoding='utf-8'))
if isinstance(loaded, dict):
    workspace = loaded.get('workspace', {}) or {}
    cwd = workspace.get('cwd', '')
    if cwd:
        print(cwd)
PY
    else
        grep "cwd:" "$file" 2>/dev/null | head -1 | awk '{print $2}'
    fi
}

patch_workspace_yaml() {
    local file="$1"
    local cwd="$2"
    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would patch workspace block in $file"
        return 0
    fi

    require_python_yaml || {
        err "python3 module 'yaml' is required to patch workspace config"
        [ "$STRICT" = true ] && exit 1
        return 0
    }

    ensure_dir "$(dirname "$file")"
    touch "$file"
    backup_file "$file"

    python3 - "$file" "$cwd" <<'PY'
import sys
from pathlib import Path
import yaml
path = Path(sys.argv[1])
cwd = sys.argv[2]
data = {}
if path.exists() and path.read_text(encoding='utf-8').strip():
    loaded = yaml.safe_load(path.read_text(encoding='utf-8'))
    if isinstance(loaded, dict):
        data = loaded
workspace = data.setdefault('workspace', {})
workspace['cwd'] = cwd
workspace['project_root'] = cwd
path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
PY
}

sync_workspace() {
    section "6. Workspace alignment"

    local hermes_cwd
    hermes_cwd="$(read_workspace_cwd "$HERMES_CONFIG")"
    if [ "$hermes_cwd" = "$PROJECT" ]; then
        ok "Hermes workspace already aligned to Antigravity Core"
        return 0
    fi

    warn "Hermes workspace current: ${hermes_cwd:-<unset>}"
    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would set workspace.cwd and workspace.project_root → $PROJECT"
        return 0
    fi

    if optional_cmd hermes; then
        if hermes config set workspace.cwd "$PROJECT" >/dev/null 2>&1 && hermes config set workspace.project_root "$PROJECT" >/dev/null 2>&1; then
            ok "Workspace updated through Hermes CLI"
            return 0
        fi
        warn "Hermes CLI update failed, falling back to direct YAML patch"
    else
        warn "Hermes CLI not found, falling back to direct YAML patch"
    fi

    patch_workspace_yaml "$HERMES_CONFIG" "$PROJECT"
    ok "Workspace patched directly in $HERMES_CONFIG"
}

show_model_mapping() {
    section "7. Runtime model mapping"
    echo ""
    echo "  Antigravity Role           →  Hermes Default"
    echo "  ────────────────────────────────────────────"
    echo "  BUILDER_A (qwen3.6-plus)   →  Primary model"
    echo "  BUILDER_B (qwen3.6-plus)   →  Fallback model"
    echo "  COUNCIL (qwen3.5-plus)     →  Deep reasoning"
    echo "  REVIEWER (qwen3.6-plus)    →  Code review"
    echo "  FALLBACK (gemini-2-flash)  →  Emergency"
    echo ""
}

write_report() {
    if [ "$DRY_RUN" = true ]; then
        warn "[DRY RUN] Would write JSON report → $REPORT_PATH"
        return 0
    fi

    ensure_dir "$(dirname "$REPORT_PATH")"
    python3 - "$REPORT_PATH" <<PY
import json
from pathlib import Path
from datetime import datetime, timezone
report = {
    "service": "antigravity-sync",
    "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
    "project": ${PROJECT@Q},
    "hermes_home": ${HERMES_HOME@Q},
    "dry_run": ${DRY_RUN},
    "sync_secrets": ${SYNC_SECRETS},
    "strict": ${STRICT},
    "clean_skills": ${CLEAN_SKILLS},
    "stats": {
        "api_available": ${API_AVAILABLE},
        "api_synced": ${API_SYNCED},
        "skills_synced": ${SKILLS_SYNCED},
        "skills_removed": ${SKILLS_REMOVED},
        "refs_ok": ${REFS_OK},
        "refs_missing": ${REFS_MISSING},
        "secret_flags": ${SECRET_FLAGS},
        "warnings": ${WARN_COUNT},
        "errors": ${ERROR_COUNT},
        "mcp_count": ${MCP_COUNT},
    }
}
Path(${REPORT_PATH@Q}).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
    ok "Report written: $REPORT_PATH"
}

print_summary() {
    section "Summary Metrics"
    printf "  %-22s : ${CYAN}%s${NC}\n" "API refs available" "$API_AVAILABLE"
    printf "  %-22s : ${GREEN}%s${NC}\n" "API refs synced" "$API_SYNCED"
    printf "  %-22s : ${GREEN}%s${NC}\n" "Skills synced" "$SKILLS_SYNCED"
    printf "  %-22s : ${YELLOW}%s${NC}\n" "Skills removed/stale" "$SKILLS_REMOVED"
    printf "  %-22s : ${GREEN}%s${NC}\n" "Contract refs OK" "$REFS_OK"
    printf "  %-22s : ${RED}%s${NC}\n" "Contract refs missing" "$REFS_MISSING"
    printf "  %-22s : %s\n" "MCP servers" "$MCP_COUNT"
    printf "  %-22s : ${YELLOW}%s${NC}\n" "Secret logic flags" "$SECRET_FLAGS"
    printf "  %-22s : ${YELLOW}%s${NC}\n" "Total Warnings" "$WARN_COUNT"
    printf "  %-22s : ${RED}%s${NC}\n" "Total Failures" "$ERROR_COUNT"
}

main() {
    need_cmd python3
    require_project
    init_runtime_paths

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ⚕  ZeRa ↔ Antigravity Core — Hardened Configuration Sync   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    [ "$DRY_RUN" = true ] && warn "DRY RUN — no files will be modified"
    [ "$SYNC_SECRETS" = true ] && warn "Secret sync enabled — values may be copied to Hermes .env"
    [ "$STRICT" = true ] && warn "Strict mode enabled — validation failures will stop execution"

    sync_api_keys
    sync_skills
    sync_mcp_configs
    sync_adapter_contract_refs
    check_secret_hygiene
    sync_workspace
    show_model_mapping
    write_report
    print_summary

    echo ""
    echo -e "${GREEN}✅ Sync complete${NC}"
    echo ""
    echo "Next steps:"
    echo "  hermes status       — check runtime status"
    echo "  hermes doctor       — run diagnostics"
    echo "  hermes chat         — start a session"
    echo "  hermes tools list   — inspect tools"
    echo "  cat $REPORT_PATH    — inspect sync report"
    echo ""
}

main "$@"