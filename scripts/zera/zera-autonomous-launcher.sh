#!/bin/bash
# ============================================
# Zera Autonomous Background Jobs Launcher
# Starts all autonomous cron tasks for Zera
# Usage: bash scripts/zera-autonomous-launcher.sh [--dry-run]
# ============================================

set -euo pipefail

ZERA_CRON="$HOME/.hermes/profiles/zera/cron"
VAULT="$HOME/antigravity-vault"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ ! -d "$DEFAULT_ROOT/configs" ]]; then
  DEFAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
REPO_ROOT="${ZERA_REPO_ROOT:-$DEFAULT_ROOT}"
COMMAND_BRIDGE="$REPO_ROOT/scripts/zera-command.sh"
COMMAND_REGISTRY="$REPO_ROOT/configs/tooling/zera_command_registry.yaml"
CLIENT_PROFILES="$REPO_ROOT/configs/tooling/zera_client_profiles.yaml"
DRY_RUN=false

if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
    echo "🔍 DRY RUN — no jobs will be started"
fi

log()   { echo -e "\033[0;34m[ZERA-AUTO]\033[0m    $1"; }
ok()    { echo -e "\033[0;32m[OK]\033[0m          $1"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m        $1"; }
title() { echo -e "\n\033[0;36m━━━ $1 ━━━\033[0m"; }

main() {
    echo ""
    echo -e "\033[0;36m╔══════════════════════════════════════════════════════════╗\033[0m"
    echo -e "\033[0;36m║  ⚕  Zera Autonomous Background Jobs — Launcher         ║\033[0m"
    echo -e "\033[0;36m╚══════════════════════════════════════════════════════════╝\033[0m"
    echo ""

    # Verify cron directory
    if [ ! -d "$ZERA_CRON" ]; then
        warn "Cron directory not found at $ZERA_CRON"
        warn "Run the setup script first."
        exit 1
    fi

    title "Registered Autonomous Jobs"

    local count=0
    for job_file in "$ZERA_CRON"/*.json; do
        if [ -f "$job_file" ]; then
            name=$(python3 -c "import json; d=json.load(open('$job_file')); print(d.get('name','unknown'))")
            schedule=$(python3 -c "import json; d=json.load(open('$job_file')); print(d.get('schedule','unknown'))")
            desc=$(python3 -c "import json; d=json.load(open('$job_file')); print(d.get('description',''))")

            ok "$name"
            echo "    Schedule:  $schedule"
            echo "    Purpose:   $desc"
            ((count++))
        fi
    done

    echo ""
    title "Job Schedule Overview"
    echo ""
    echo "  Time     │ Job"
    echo "  ─────────┼──────────────────────────────────────────"
    echo "  04:00    │ Vault Guardian (daily maintenance)"
    echo "  08:00    │ Morning Briefing (daily for Artem)"
    echo "  */6h     │ Memory Consolidation (4x per day)"
    echo "  */12h    │ Self-Reflection (2x per day)"
    echo "  */12h    │ Goal Review (2x per day)"
    echo "  Mon 09:00│ Weekly Knowledge Digest"
    echo ""

    title "Autonomy Capabilities"
    echo ""
    echo "  ✅ Vault read (observe)"
    echo "  ✅ Vault write (execute_low_risk)"
    echo "  ✅ Vault reorganize & linking (execute_low_risk)"
    echo "  ✅ Vault synthesis (execute_low_risk)"
    echo "  ✅ Knowledge extraction (execute_low_risk)"
    echo "  ✅ Pattern detection (execute_low_risk)"
    echo "  ✅ Self-reflection (execute_low_risk)"
    echo "  ✅ Memory consolidation (execute_low_risk)"
    echo "  ✅ Goal review (execute_low_risk)"
    echo "  ⚠️  Internet search (execute_gated — needs approval)"
    echo "  ⚠️  Browser observation (execute_gated — needs approval)"
    echo "  ⚠️  Browser action (execute_gated — needs approval)"
    echo "  ❌  External messages (never_autonomous)"
    echo "  ❌  System changes (never_autonomous)"
    echo "  ❌  Destructive changes (never_autonomous)"
    echo ""

    title "Command OS"
    echo ""
    if [ -f "$COMMAND_BRIDGE" ]; then
        bash "$COMMAND_BRIDGE" catalog
    else
        warn "Command bridge not found: $COMMAND_BRIDGE"
    fi
    echo ""

    title "Quick Commands"
    echo ""
    echo "  # Resolve a canonical Zera command:"
    echo "  bash scripts/zera-command.sh resolve --client repo_native --command zera:plan --objective \"Собери мне приоритеты\" --json"
    echo ""
    echo "  # Render a governed research prompt:"
    echo "  bash scripts/zera-command.sh render --client repo_native --command zera:research --objective \"Собери evidence-backed сравнение\""
    echo ""
    echo "  # Run bounded self-evolution:"
    echo "  bash scripts/zera-evolve.sh --loop capability --dry-run"
    echo ""
    echo "  # Check cron jobs:"
    echo "  hermes cron list"
    echo ""
    echo "  # Full Zera session:"
    echo "  zera chat"
    echo ""

    echo "  Registry: $COMMAND_REGISTRY"
    echo "  Clients : $CLIENT_PROFILES"
    echo ""

    echo -e "\033[0;32m✅ Zera Autonomous System Ready ($count jobs registered)\033[0m"
    echo ""
}

main "$@"
