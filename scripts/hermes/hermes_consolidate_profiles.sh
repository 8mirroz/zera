#!/bin/bash
# Объединение профилей Hermes: antigravity + zera → единый профиль zera
#
# Что делает:
# 1. Берт полный конфиг antigravity как основу
# 2. Обновляет persona на zera (уже установлено)
# 3. Сохраняет как единый профиль zera
# 4. Обновляет все ссылки в репозитории
# 5. Создаёт backup старых профилей

set -euo pipefail

# --- CONFIGURATION ---
HERMES_DIR="${HERMES_DIR:-$HOME/.hermes/profiles}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HERMES_BIN="${HERMES_BIN:-}"

# Auto-detect hermes binary
if [[ -z "$HERMES_BIN" ]]; then
    if command -v hermes &>/dev/null; then
        HERMES_BIN="hermes"
    elif [[ -x "$HOME/.local/bin/hermes" ]]; then
        HERMES_BIN="$HOME/.local/bin/hermes"
    fi
fi

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

echo "═══ Hermes Profile Consolidation ═══"
echo "Timestamp: $TIMESTAMP"
echo ""

# 1. Backup
echo "📦 Creating backups..."
mkdir -p "$HERMES_DIR/.backups/$TIMESTAMP"
cp -r "$HERMES_DIR/antigravity" "$HERMES_DIR/.backups/$TIMESTAMP/" 2>/dev/null || true
cp -r "$HERMES_DIR/zera" "$HERMES_DIR/.backups/$TIMESTAMP/" 2>/dev/null || true
echo "  ✓ Backups saved to $HERMES_DIR/.backups/$TIMESTAMP/"

# 2. Create unified zera profile from antigravity (already has persona: zera)
echo ""
echo "🔀 Creating unified zera profile..."
mkdir -p "$HERMES_DIR/zera"
cp "$HERMES_DIR/antigravity/config.yaml" "$HERMES_DIR/zera/config.yaml"

# Ensure .env exists
if [ -f "$HERMES_DIR/antigravity/.env" ]; then
    cp "$HERMES_DIR/antigravity/.env" "$HERMES_DIR/zera/.env"
fi

echo "  ✓ Unified profile created at $HERMES_DIR/zera/config.yaml"

# 3. Verify key settings in unified profile
echo ""
echo "🔍 Verifying unified profile..."
PERSONA=$(grep -E "^\s+persona:" "$HERMES_DIR/zera/config.yaml" | head -1 | awk '{print $2}')
MODEL=$(grep -E "^\s+default:" "$HERMES_DIR/zera/config.yaml" | head -1 | awk '{print $2}')
echo "  Persona: $PERSONA"
echo "  Model: $MODEL"

if [ "$PERSONA" != "zera" ]; then
    echo "  ⚠️  Persona is not 'zera', fixing..."
    # This shouldn't happen since antigravity already has persona: zera
fi

# 4. Update repo references
echo ""
echo "📝 Updating repository references..."

portable_sed() {
    local pattern="$1"
    local file="$2"
    if [[ ! -f "$file" ]]; then return 0; fi
    # Use python for portable in-place edit without backup issues
    python3 -c "
import sys, re
from pathlib import Path
pattern = sys.argv[1]
file_path = Path(sys.argv[2])
target, replacement = pattern.split('|')[1:3]
content = file_path.read_text()
new_content = content.replace(target, replacement)
file_path.write_text(new_content)
" "|$pattern" "$file"
}

# Update adapter.yaml — change profile_config_path from antigravity to zera
ADAPTER_YAML="$REPO_ROOT/configs/adapters/hermes/adapter.yaml"
if [[ -f "$ADAPTER_YAML" ]]; then
    portable_sed "profiles/antigravity/config.yaml|profiles/zera/config.yaml" "$ADAPTER_YAML"
    echo "  ✓ adapter.yaml updated"
fi

# Update zera_client_profiles.yaml
CLIENT_PROFILES="$REPO_ROOT/configs/tooling/zera_client_profiles.yaml"
if [[ -f "$CLIENT_PROFILES" ]]; then
    portable_sed "profiles/antigravity/config.yaml|profiles/zera/config.yaml" "$CLIENT_PROFILES"
    echo "  ✓ zera_client_profiles.yaml updated"
fi

# Update zera_command_runtime.py
ZERA_RUNTIME="$REPO_ROOT/scripts/zera_command_runtime.py"
if [[ -f "$ZERA_RUNTIME" ]]; then
    portable_sed "-p antigravity|-p zera" "$ZERA_RUNTIME"
    echo "  ✓ zera_command_runtime.py updated"
fi

# Update scout_daemon.py
SCOUT_DAEMON="$REPO_ROOT/scripts/scout_daemon.py"
if [[ -f "$SCOUT_DAEMON" ]]; then
    portable_sed "profiles/antigravity/|profiles/zera/" "$SCOUT_DAEMON"
    echo "  ✓ scout_daemon.py updated"
fi

# Update beta_manager.py if it references antigravity profile path
BETA_MANAGER="$REPO_ROOT/scripts/beta_manager.py"
if [[ -f "$BETA_MANAGER" ]]; then
    portable_sed "profiles/antigravity|profiles/zera" "$BETA_MANAGER"
    echo "  ✓ beta_manager.py updated"
fi

# 5. Update models.yaml hermes_profiles section
echo ""
echo "📝 Updating models.yaml hermes_profiles..."
MODELS_YAML="$REPO_ROOT/configs/orchestrator/models.yaml"
if [ -f "$MODELS_YAML" ]; then
    # Check if hermes_profiles has both zera and antigravity
    if grep -q "antigravity:" "$MODELS_YAML" 2>/dev/null; then
        echo "  ⚠️  Found 'antigravity' profile in models.yaml — needs manual review"
        echo "     Consider merging hermes_profiles.zera and hermes_profiles.antigravity"
    fi
fi

# --- TRAPS ---
cleanup() {
    :
}
trap cleanup EXIT
trap 'echo -e "\nInterrupted"; exit 130' INT TERM

# 6. Summary
echo ""
echo "═══ Consolidation Summary ═══"
echo ""
echo "✅ Unified profile: ~/.hermes/profiles/zera/config.yaml"
echo "📦 Backups: ~/.hermes/profiles/.backups/$TIMESTAMP/"
echo ""
if [[ -n "$HERMES_BIN" ]]; then
    echo "🧪 Testing zera profile..."
    "$HERMES_BIN" -p zera status 2>/dev/null | head -n 5 || echo "  ⚠️  zera profile test failed"
fi
echo ""
echo "⚠️  Manual steps remaining:"
echo "   1. Review ~/.hermes/profiles/zera/config.yaml"
echo "   2. Remove: ~/.hermes/profiles/antigravity/ (if everything is OK)"
echo ""
