#!/usr/bin/env bash
set -euo pipefail

# --- CONFIGURATION ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENT_OS="$ROOT/repos/packages/agent-os"
MODE="pre_commit"
JSON_REPORT=false
DEBUG=0

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { [[ "$JSON_REPORT" == "true" ]] || echo -e "${CYAN}[QUALITY]${NC} $1"; }
ok()   { [[ "$JSON_REPORT" == "true" ]] || echo -e "${GREEN}[OK]${NC}      $1"; }
warn() { [[ "$JSON_REPORT" == "true" ]] || echo -e "${YELLOW}[WARN]${NC}    $1"; }
err()  { [[ "$JSON_REPORT" == "true" ]] || echo -e "${RED}[ERROR]${NC}   $1" >&2; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json)    JSON_REPORT=true ;;
        --debug)   DEBUG=1 ;;
        --quick)   MODE="local_quick" ;;
        --profile) shift; MODE="$1" ;;
        --doctor)  MODE="doctor" ;;
        *)         MODE="$1" ;;
    esac
    shift
done

if [[ "$MODE" == "pre-commit" ]]; then MODE="pre_commit"; fi

# --- VALIDATION ---
if [[ ! -d "$ROOT" ]]; then err "Root not found: $ROOT"; exit 2; fi
if [[ ! -d "$AGENT_OS" ]]; then err "Agent-OS not found: $AGENT_OS"; exit 2; fi

# --- PREFLIGHT ---
if [[ "${AG_SKIP_PREFLIGHT:-0}" != "1" && "$MODE" != "doctor" ]]; then
    HEALTH_SCRIPT="$ROOT/scripts/system_health_check.sh"
    if [[ -x "$HEALTH_SCRIPT" ]]; then
        if [[ "$JSON_REPORT" == "true" ]]; then
            "$HEALTH_SCRIPT" --quick --json >/dev/null 2>&1 || { err "Preflight health check failed"; exit 1; }
        else
            "$HEALTH_SCRIPT" --quick || { err "Preflight health check failed"; exit 1; }
        fi
    fi
fi

# --- EXECUTION ---
case "$MODE" in
    doctor)
        log "Running Qualitly Doctor (Auto-fix mode)..."
        # Integration with ruff or other formatters could go here
        cd "$AGENT_OS"
        if command -v uv >/dev/null 2>&1; then
            uv run ruff format . 2>/dev/null || warn "Ruff format failed or not available"
            uv run ruff check --fix . 2>/dev/null || warn "Ruff fix failed or not available"
        fi
        ok "Doctor finished"
        exit 0
        ;;
    pre_commit|local_quick|ci_required|nightly|all_non_benchmark)
        log "Running quality profile: $MODE"
        if [[ "$JSON_REPORT" == "true" ]]; then
            # Execute with JSON capture
            cd "$AGENT_OS"
            exec bash -lc "uv run python ../../../scripts/reliability_orchestrator.py run --profile \"$MODE\" --json"
        else
            cd "$AGENT_OS"
            exec bash -lc "uv run python ../../../scripts/reliability_orchestrator.py run --profile \"$MODE\""
        fi
        ;;
    *)
        err "Unknown reliability profile: $MODE"
        echo "Allowed: pre-commit, quick, --doctor, ci_required, nightly"
        exit 2
        ;;
esac
