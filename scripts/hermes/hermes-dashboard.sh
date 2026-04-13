#!/bin/bash
# ============================================
# Hermes Agent — Antigravity Core Dashboard
# Usage: bash scripts/hermes-dashboard.sh
# ============================================

set -euo pipefail

HERMES="hermes"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$HOME/.hermes/config.yaml"
PROFILE="antigravity"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "\n${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${BOLD}   ⚕  ZeRa Agent — Antigravity Core Dashboard   ${NC}${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}\n"
}

print_section() {
    echo -e "\n${BLUE}━━━ $1 ━━━${NC}"
}

# ============================================
# STATUS
# ============================================
show_status() {
    print_header
    print_section "System Status"
    $HERMES version 2>&1
    echo ""
    print_section "Configuration"
    $HERMES config show 2>&1 | head -20
    echo ""
    print_section "Toolsets"
    $HERMES tools list 2>&1
    echo ""
    print_section "MCP Servers"
    $HERMES mcp list 2>&1
    echo ""
    print_section "Profiles"
    $HERMES profile list 2>&1
    echo ""
    print_section "Sessions"
    $HERMES sessions stats 2>&1
    echo ""
    print_section "Skills (Antigravity Core synced)"
    ls ~/.hermes/skills/antigravity/*.md 2>/dev/null | wc -l | xargs -I{} echo "  {} Antigravity skills synced"
    ls ~/.hermes/skills/antigravity/*.md 2>/dev/null | xargs -n1 basename | sed 's/\.md$//' | while read s; do echo "    • $s"; done
}

# ============================================
# QUICK ACTIONS
# ============================================
quick_chat() {
    print_header
    echo -e "${YELLOW}Quick question mode (Ctrl+C to exit)${NC}"
    echo -e "${CYAN}Example: 'analyze the router config'${NC}"
    read -p "> " question
    $HERMES chat -q "$question" 2>&1
}

full_session() {
    print_header
    echo -e "${GREEN}Starting full interactive session (Antigravity profile)${NC}"
    echo -e "${CYAN}Type /help for commands, /exit to quit${NC}"
    $HERMES -p "$PROFILE" 2>&1
}

# ============================================
# SYNC
# ============================================
sync_skills() {
    print_header
    print_section "Syncing Antigravity Core Skills → Hermes"
    
    mkdir -p ~/.hermes/skills/antigravity
    local count=0
    
    for skill_dir in "$PROJECT"/configs/skills/superpowers/*/; do
        skill_name=$(basename "$skill_dir")
        if [ -f "$skill_dir/SKILL.md" ]; then
            cp "$skill_dir/SKILL.md" "$HOME/.hermes/skills/antigravity/${skill_name}.md" 2>/dev/null
            echo -e "  ${GREEN}✓${NC} $skill_name"
            ((count++))
        fi
    done
    
    for skill_dir in "$PROJECT"/configs/skills/*/; do
        skill_name=$(basename "$skill_dir")
        if [ -f "$skill_dir/SKILL.md" ] && [[ ! "$skill_name" =~ ^(superpowers|packs|zera-) ]]; then
            cp "$skill_dir/SKILL.md" "$HOME/.hermes/skills/antigravity/${skill_name}.md" 2>/dev/null
            echo -e "  ${GREEN}✓${NC} $skill_name (domain)"
            ((count++))
        fi
    done
    
    echo -e "\n${GREEN}✅ Synced $count skills${NC}"
}

# ============================================
# DIAGNOSTICS
# ============================================
run_diagnostics() {
    print_header
    print_section "Full Diagnostics"
    $HERMES doctor 2>&1
}

# ============================================
# INSIGHTS
# ============================================
show_insights() {
    print_header
    print_section "Usage Insights (last 30 days)"
    $HERMES insights --days 30 2>&1
}

# ============================================
# MCP TEST
# ============================================
test_mcp() {
    print_header
    print_section "Testing MCP Servers"
    $HERMES mcp list 2>&1
    echo ""
    for server in filesystem context7 sequential-thinking; do
        echo -e "${YELLOW}Testing: $server${NC}"
        $HERMES mcp test "$server" 2>&1 || echo -e "  ${RED}✗ $server failed or not configured${NC}"
        echo ""
    done
}

# ============================================
# MAIN MENU
# ============================================
print_menu() {
    echo -e "\n${BOLD}┌──── ZeRa Agent Dashboard ────┐${NC}"
    echo -e "${BOLD}│${NC}                               ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}1)${NC} Full Status              ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}2)${NC} Quick Chat (one question) ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}3)${NC} Full Session (interactive)${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}4)${NC} Sync Skills              ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}5)${NC} Run Diagnostics          ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}6)${NC} Usage Insights           ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}7)${NC} Test MCP Servers         ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}8)${NC} Edit Config              ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}9)${NC} View Logs                ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}  ${GREEN}0)${NC} Exit                     ${BOLD}│${NC}"
    echo -e "${BOLD}│${NC}                               ${BOLD}│${NC}"
    echo -e "${BOLD}└───────────────────────────────┘${NC}"
    echo ""
}

main() {
    print_menu
    read -p "Select [0-9]: " choice
    
    case $choice in
        1) show_status ;;
        2) quick_chat ;;
        3) full_session ;;
        4) sync_skills ;;
        5) run_diagnostics ;;
        6) show_insights ;;
        7) test_mcp ;;
        8) $HERMES config edit 2>&1 ;;
        9) $HERMES logs 2>&1 ;;
        0) echo -e "${GREEN}Goodbye!${NC}"; exit 0 ;;
        *) echo -e "${RED}Invalid choice${NC}"; exit 1 ;;
    esac
    
    echo -e "\n${YELLOW}Press Enter to return to menu...${NC}"
    read
    main
}

main
