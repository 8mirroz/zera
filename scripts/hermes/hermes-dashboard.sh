#!/bin/bash
# ============================================
# Hermes Agent — Antigravity Core Dashboard
# Usage: bash scripts/hermes-dashboard.sh
# ============================================

set -euo pipefail

# --- CONFIGURATION ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HERMES_BIN="${HERMES_BIN:-}"
PROFILE="${HERMES_PROFILE:-zera}" # Default to zera profile

# Auto-detect hermes binary if not provided
if [[ -z "$HERMES_BIN" ]]; then
    if command -v hermes &>/dev/null; then
        HERMES_BIN="hermes"
    elif [[ -x "$HOME/.local/bin/hermes" ]]; then
        HERMES_BIN="$HOME/.local/bin/hermes"
    else
        echo "Error: hermes binary not found. Please install it or set HERMES_BIN." >&2
        exit 1
    fi
fi

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'
NC='\033[0m'

# ============================================
# UI / ANIMATION (no deps)
# ============================================
# Config:
#   HERMES_DASH_STYLE: classic | orbit | wave | minimal (default: classic)
#   HERMES_DASH_ANIM:  1 | 0  (default: 1 on TTY)
#   HERMES_DASH_NO_UNICODE: 1 forces ASCII fallback
#
# Tips:
#   HERMES_DASH_STYLE=orbit bash scripts/hermes/hermes-dashboard.sh
#   HERMES_DASH_ANIM=0 bash scripts/hermes/hermes-dashboard.sh
#
ui_is_tty() { [[ -t 1 ]] && [[ -t 0 ]]; }

ui_is_utf8() {
    if [[ "${HERMES_DASH_NO_UNICODE:-0}" == "1" ]]; then
        return 1
    fi
    local charmap
    charmap="$(locale charmap 2>/dev/null || true)"
    [[ "$charmap" == UTF-8* || "$charmap" == utf8* ]]
}

ui_can_animate() {
    local anim="${HERMES_DASH_ANIM:-}"
    if [[ -n "$anim" ]]; then
        [[ "$anim" != "0" ]]
        return
    fi
    ui_is_tty
}

ui_sleep_ms() {
    local ms="${1:-80}"
    sleep "0.$(printf "%03d" "$ms")"
}

ui_clear_line() {
    if ui_is_tty; then
        printf '\r\033[2K'
    fi
}

ui_spinner_run() {
    # Usage: ui_spinner_run "Label" command ...
    local label="$1"; shift
    if ! ui_can_animate; then
        "$@"
        return
    fi

    local frames='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    if ! ui_is_utf8; then
        frames='|/-\\'
    fi

    local tmp_out
    tmp_out="$(mktemp)"
    # Use a trap to ensure tmp file is removed if script is killed
    # (Global trap will handle it, but we also handle it here for safety)
    
    set +e
    ("$@" >"$tmp_out" 2>&1) &
    local cmd_pid=$!
    set -e

    local i=0
    while kill -0 "$cmd_pid" 2>/dev/null; do
        local frame_idx=$(( i % ${#frames} ))
        local frame="${frames:frame_idx:1}"
        printf "\r${CYAN}%s${NC} %s" "$frame" "$label"
        ui_sleep_ms 80
        i=$(( i + 1 ))
    done

    wait "$cmd_pid"
    local exit_code=$?
    ui_clear_line
    cat "$tmp_out"
    rm -f "$tmp_out"
    return "$exit_code"
}

ui_progress_bar() {
    # Usage: ui_progress_bar current total "Label"
    local current="${1:-0}"
    local total="${2:-1}"
    local label="${3:-}"
    local width=24
    if ! ui_is_tty; then
        # Minimal progress for non-TTY
        printf "[%d/%d] %s\n" "$current" "$total" "$label"
        return 0
    fi
    if [[ "$total" -le 0 ]]; then
        total=1
    fi
    local filled=$(( (current * width) / total ))
    if [[ "$filled" -gt "$width" ]]; then
        filled="$width"
    fi
    local empty=$(( width - filled ))
    local bar
    if ui_is_utf8; then
        # Generate bars safely without seq if possible, but seq is common
        bar="$(printf "%0.s█" $(seq 1 "$filled") 2>/dev/null || true)$(printf "%0.s░" $(seq 1 "$empty") 2>/dev/null || true)"
    else
        bar="$(printf "%0.s#" $(seq 1 "$filled") 2>/dev/null || true)$(printf "%0.s." $(seq 1 "$empty") 2>/dev/null || true)"
    fi
    printf "\r${BLUE}[${NC}%s${BLUE}]${NC} %s %d/%d" "$bar" "$label" "$current" "$total"
}

ui_header_style() {
    echo "${HERMES_DASH_STYLE:-classic}"
}

ui_print_logo() {
    # Logo is intentionally compact (works in narrow terminals)
    local style
    style="$(ui_header_style)"

    if ! ui_is_utf8; then
        echo -e "${CYAN}+----------------------------------------------+${NC}"
        echo -e "${CYAN}|${BOLD}   Hermes / ZeRa — Antigravity Dashboard     ${NC}${CYAN}|${NC}"
        echo -e "${CYAN}+----------------------------------------------+${NC}"
        return 0
    fi

    case "$style" in
        orbit)
            echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
            echo -e "${CYAN}║${BOLD}    ⚕  ZeRa Agent  ·  Hermes Console  ·  ⟲        ${NC}${CYAN}║${NC}"
            echo -e "${CYAN}║${NC}        ⠐⠒⠤⠤⠤⠤⠤⠤⠤⠤⠤⠤⠤⠤⠤⠒⠂            ${CYAN}║${NC}"
            echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
            ;;
        wave)
            echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
            echo -e "${CYAN}║${BOLD}   ⚕  ZeRa Agent — Antigravity Core Dashboard   ${NC}${CYAN}║${NC}"
            echo -e "${CYAN}║${NC}     ⢀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⡀        ${CYAN}║${NC}"
            echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
            ;;
        minimal)
            echo -e "${CYAN}ZeRa Agent${NC} ${BOLD}·${NC} Hermes ${BOLD}·${NC} Antigravity"
            ;;
        classic|*)
            echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
            echo -e "${CYAN}║${BOLD}   ⚕  ZeRa Agent — Antigravity Core Dashboard   ${NC}${CYAN}║${NC}"
            echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
            ;;
    esac
}

ui_animate_header() {
    if ! ui_can_animate || ! ui_is_tty || ! ui_is_utf8; then
        ui_print_logo
        echo ""
        return 0
    fi

    local style
    style="$(ui_header_style)"

    case "$style" in
        orbit)
            # A tiny "orbital" spinner next to the title for ~500ms
            local frames=( "⟲" "⟳" "⟲" "⟳" "⟲" )
            ui_print_logo
            echo ""
            for f in "${frames[@]}"; do
                printf "\r${CYAN}%s${NC} Initializing…" "$f"
                ui_sleep_ms 110
            done
            ui_clear_line
            ;;
        wave)
            # Subtle wave shimmer line
            ui_print_logo
            echo ""
            local wave=( "⣀⣀⣀⣀⣀⣀" "⣤⣤⣤⣤⣤⣤" "⣿⣿⣿⣿⣿⣿" "⣤⣤⣤⣤⣤⣤" )
            for w in "${wave[@]}"; do
                printf "\r${CYAN}%s${NC} Loading…" "$w"
                ui_sleep_ms 120
            done
            ui_clear_line
            ;;
        minimal|classic|*)
            ui_print_logo
            echo ""
            ;;
    esac
}

print_header() {
    echo ""
    ui_animate_header
}

print_section() {
    echo -e "\n${BLUE}━━━ $1 ━━━${NC}"
}

# ============================================
# STATUS
# ============================================
show_status() {
    local json_output="${1:-0}"
    
    if [[ "$json_output" == "1" ]]; then
        # Future: implement real JSON mapping if hermes supports it natively
        # For now, wrap basic info in JSON
        cat <<EOF
{
  "project": "$PROJECT_ROOT",
  "profile": "$PROFILE",
  "hermes_bin": "$HERMES_BIN",
  "version": "$($HERMES_BIN version 2>/dev/null | head -n 1 || echo "unknown")"
}
EOF
        return 0
    fi

    print_header
    print_section "System Status"
    $HERMES_BIN version 2>&1 || echo "Hermes binary failed"
    echo ""
    print_section "Configuration"
    # Safe pipe for head
    $HERMES_BIN config show 2>&1 | (head -n 20 || true)
    echo ""
    print_section "Toolsets"
    $HERMES_BIN tools list 2>&1
    echo ""
    print_section "MCP Servers"
    $HERMES_BIN mcp list 2>&1
    echo ""
    print_section "Profiles"
    $HERMES_BIN profile list 2>&1
    echo ""
    print_section "Sessions"
    $HERMES_BIN sessions stats 2>&1
    echo ""
    print_section "Platform Health"
    local health_script="$PROJECT_ROOT/scripts/system_health_check.sh"
    if [[ -x "$health_script" ]]; then
        "$health_script" --quick
    else
        echo -e "  ${RED}✗ Health check script missing${NC}"
    fi

    print_section "CLI Tooling Audit"
    local tool_script="$PROJECT_ROOT/scripts/cli_tools_check.sh"
    if [[ -x "$tool_script" ]]; then
        "$tool_script"
    else
        echo -e "  ${RED}✗ Tool check script missing${NC}"
    fi

    print_section "Skills (Antigravity Core synced)"
    local sync_dir="$HOME/.hermes/skills/antigravity"
    if [[ -d "$sync_dir" ]]; then
        local skill_count
        skill_count="$(find "$sync_dir" -name "*.md" | wc -l | tr -d ' ')"
        echo "  $skill_count Antigravity skills synced"
        find "$sync_dir" -name "*.md" -maxdepth 1 -exec basename {} \; | sed 's/\.md$//' | while read -r s; do echo "    • $s"; done
    else
        echo "  No skills synced yet (run sync command)"
    fi
}

# ============================================
# QUICK ACTIONS
# ============================================
quick_chat() {
    print_header
    echo -e "${YELLOW}Quick question mode (Ctrl+C to exit)${NC}"
    echo -e "${CYAN}Example: 'analyze the router config'${NC}"
    read -r -p "> " question
    $HERMES_BIN chat -q "$question" 2>&1
}

full_session() {
    print_header
    echo -e "${GREEN}Starting full interactive session (Antigravity profile)${NC}"
    echo -e "${CYAN}Type /help for commands, /exit to quit${NC}"
    $HERMES_BIN -p "$PROFILE" 2>&1
}

# ============================================
# SYNC
# ============================================
sync_skills() {
    print_header
    print_section "Syncing Antigravity Core Skills → Hermes"
    
    local sync_dir="$HOME/.hermes/skills/antigravity"
    mkdir -p "$sync_dir"
    
    local count=0
    local total=0
    local skill_paths=()

    shopt -s nullglob
    # Search in .agents/skills and configs/skills
    for d in "$PROJECT_ROOT/.agents/skills"/*/ "$PROJECT_ROOT/configs/skills"/*/ "$PROJECT_ROOT/configs/skills/superpowers"/*/; do
        if [[ -f "$d/SKILL.md" ]]; then
            skill_paths+=("$d/SKILL.md")
        fi
    done
    total=${#skill_paths[@]}

    for skill_file in "${skill_paths[@]}"; do
        local skill_dir
        skill_dir="$(dirname "$skill_file")"
        local skill_name
        skill_name="$(basename "$skill_dir")"
        
        # Skip certain patterns if needed (like zera- internal tools)
        if [[ "$skill_name" =~ ^(packs|zera-internal) ]]; then
            total=$(( total - 1 ))
            continue
        fi

        cp "$skill_file" "$sync_dir/${skill_name}.md" 2>/dev/null
        count=$(( count + 1 ))
        
        if ui_can_animate && ui_is_tty; then
            ui_progress_bar "$count" "$total" "Syncing: $skill_name"
        else
            echo -e "  ${GREEN}✓${NC} $skill_name"
        fi
    done
    shopt -u nullglob

    if ui_can_animate && ui_is_tty; then
        ui_clear_line
        echo -e "  ${GREEN}✓${NC} Skills written to ${BOLD}$sync_dir${NC}"
    fi
    
    echo -e "\n${GREEN}✅ Synced $count skills${NC}"
}

# ============================================
# DIAGNOSTICS
# ============================================
run_diagnostics() {
    print_header
    print_section "Full Diagnostics"
    ui_spinner_run "Running hermes doctor" "$HERMES_BIN" doctor
}

show_insights() {
    print_header
    print_section "Usage Insights (last 30 days)"
    ui_spinner_run "Collecting insights" "$HERMES_BIN" insights --days 30
}

test_mcp() {
    print_header
    print_section "Testing MCP Servers"
    "$HERMES_BIN" mcp list 2>&1
    echo ""
    # Only test a few core ones to keep it fast
    for server in filesystem context7 sequential-thinking; do
        echo -e "${YELLOW}Testing: $server${NC}"
        if ui_can_animate && ui_is_tty; then
            ui_spinner_run "mcp test $server" "$HERMES_BIN" mcp test "$server" || echo -e "  ${RED}✗ $server failed or not configured${NC}"
        else
            "$HERMES_BIN" mcp test "$server" 2>&1 || echo -e "  ${RED}✗ $server failed or not configured${NC}"
        fi
        echo ""
    done
}

# ============================================
# MAIN MENU
# ============================================
# --- TRAPS ---
cleanup() {
    ui_clear_line
    # Add any temp file cleanup here if needed
}
trap cleanup EXIT
trap 'echo -e "\nInterrupted"; exit 130' INT TERM

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
    echo -e "${CYAN}Style:${NC} ${BOLD}$(ui_header_style)${NC}  ${CYAN}Anim:${NC} ${BOLD}${HERMES_DASH_ANIM:-auto}${NC}  ${CYAN}Unicode:${NC} ${BOLD}$([ "${HERMES_DASH_NO_UNICODE:-0}" = "1" ] && echo off || echo auto)${NC}"
    echo ""
}

# --- DISPATCHER ---
handle_command() {
    local cmd="${1:-menu}"
    case "$cmd" in
        status)     show_status "${2:-0}" ;;
        chat)       quick_chat ;;
        session)    full_session ;;
        sync)       sync_skills ;;
        doctor)     run_diagnostics ;;
        insights)   show_insights ;;
        mcp-test)   test_mcp ;;
        config-edit) "$HERMES_BIN" config edit 2>&1 ;;
        logs)       "$HERMES_BIN" logs 2>&1 ;;
        menu)       return 0 ;;
        *)          echo -e "${RED}Unknown command: $cmd${NC}" >&2; exit 1 ;;
    esac
    exit 0
}

# --- MAIN ---
main() {
    # If arguments provided, use dispatcher
    if [[ $# -gt 0 ]]; then
        handle_command "$@"
    fi

    # Interactive Menu Loop
    while true; do
        print_menu
        read -r -p "Select [0-9]: " choice
        
        case $choice in
            1) show_status ;;
            2) quick_chat ;;
            3) full_session ;;
            4) sync_skills ;;
            5) run_diagnostics ;;
            6) show_insights ;;
            7) test_mcp ;;
            8) "$HERMES_BIN" config edit 2>&1 ;;
            9) "$HERMES_BIN" logs 2>&1 ;;
            0) echo -e "${GREEN}Goodbye!${NC}"; exit 0 ;;
            *) echo -e "${RED}Invalid choice${NC}" ;;
        esac
        
        echo -e "\n${YELLOW}Press Enter to return to menu...${NC}"
        read -r
    done
}

main "$@"
