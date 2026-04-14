#!/usr/bin/env bash
# ============================================
# Antigravity Core CLI Tooling Audit
# Validates presence and versions of required system tools.
# Usage: bash scripts/cli_tools_check.sh [--json]
# ============================================

set -euo pipefail

# --- CONFIGURATION ---
JSON_REPORT=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --json) JSON_REPORT=true ;;
    esac
    shift
done

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

# Tools to check: name, command, hint
TOOLS=(
    "Python 3.11+|python3|brew install python@3.11"
    "UV (Package Manager)|uv|curl -LsSf https://astral.sh/uv/install.sh | sh"
    "Git|git|brew install git"
    "Ripgrep (rg)|rg|brew install ripgrep"
    "Ruff (Formatter)|ruff|uv tool install ruff"
    "Quarto (qmd)|qmd|brew install quarto"
    "Hermes CLI|hermes|Follow hermes installation guide"
    "Node.js (npx)|npx|brew install node"
)

# --- EXECUTION ---
RESULTS=()
MISSING_COUNT=0

if [[ "$JSON_REPORT" == "false" ]]; then
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ⚕  Antigravity CLI Tooling Audit                         ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
fi

for entry in "${TOOLS[@]}"; do
    IFS="|" read -r name cmd hint <<< "$entry"
    
    if command -v "$cmd" >/dev/null 2>&1; then
        version=$($cmd --version 2>/dev/null | head -n 1 || echo "unknown")
        path=$(command -v "$cmd")
        
        if [[ "$JSON_REPORT" == "false" ]]; then
            printf "${GREEN}[OK]${NC}   %-25s %s\n" "$name" "($version)"
        fi
        RESULTS+=("{\"tool\": \"$name\", \"status\": \"ok\", \"path\": \"$path\", \"version\": \"$version\"}")
    else
        if [[ "$JSON_REPORT" == "false" ]]; then
            printf "${RED}[FAIL]${NC} %-25s ${YELLOW}Hint: %s${NC}\n" "$name" "$hint"
        fi
        RESULTS+=("{\"tool\": \"$name\", \"status\": \"missing\", \"hint\": \"$hint\"}")
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done

if [[ "$JSON_REPORT" == "true" ]]; then
    echo "["
    for i in "${!RESULTS[@]}"; do
        echo "  ${RESULTS[$i]}$([[ $i -lt $((${#RESULTS[@]} - 1)) ]] && echo ",")"
    done
    echo "]"
else
    echo ""
    if [[ "$MISSING_COUNT" -eq 0 ]]; then
        echo -e "${GREEN}✅ All required CLI tools are present.${NC}"
        echo ""
    else
        echo -e "${RED}❌ Missing $MISSING_COUNT required tools.${NC}"
        echo ""
        exit 1
    fi
fi
