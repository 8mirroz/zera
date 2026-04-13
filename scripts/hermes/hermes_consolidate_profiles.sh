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

HERMES_DIR="$HOME/.hermes/profiles"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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

# Update adapter.yaml — change profile_config_path from antigravity to zera
ADAPTER_YAML="$REPO_ROOT/configs/adapters/hermes/adapter.yaml"
if [ -f "$ADAPTER_YAML" ]; then
    sed -i '' 's|profiles/antigravity/config.yaml|profiles/zera/config.yaml|g' "$ADAPTER_YAML"
    echo "  ✓ adapter.yaml updated"
fi

# Update zera_client_profiles.yaml
CLIENT_PROFILES="$REPO_ROOT/configs/tooling/zera_client_profiles.yaml"
if [ -f "$CLIENT_PROFILES" ]; then
    sed -i '' 's|profiles/antigravity/config.yaml|profiles/zera/config.yaml|g' "$CLIENT_PROFILES"
    echo "  ✓ zera_client_profiles.yaml updated"
fi

# Update zera_command_runtime.py
ZERA_RUNTIME="$REPO_ROOT/scripts/zera_command_runtime.py"
if [ -f "$ZERA_RUNTIME" ]; then
    sed -i '' 's|-p antigravity|-p zera|g' "$ZERA_RUNTIME"
    echo "  ✓ zera_command_runtime.py updated"
fi

# Update scout_daemon.py
SCOUT_DAEMON="$REPO_ROOT/scripts/scout_daemon.py"
if [ -f "$SCOUT_DAEMON" ]; then
    sed -i '' 's|profiles/antigravity/|profiles/zera/|g' "$SCOUT_DAEMON"
    echo "  ✓ scout_daemon.py updated"
fi

# Update beta_manager.py if it references antigravity profile path
BETA_MANAGER="$REPO_ROOT/scripts/beta_manager.py"
if [ -f "$BETA_MANAGER" ]; then
    sed -i '' 's|profiles/antigravity|profiles/zera|g' "$BETA_MANAGER"
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

# 6. Summary
echo ""
echo "═══ Consolidation Summary ═══"
echo ""
echo "✅ Unified profile: ~/.hermes/profiles/zera/config.yaml"
echo "📦 Backups: ~/.hermes/profiles/.backups/$TIMESTAMP/"
echo ""
echo "📝 Updated repo files:"
echo "   • configs/adapters/hermes/adapter.yaml"
echo "   • configs/tooling/zera_client_profiles.yaml"
echo "   • scripts/zera_command_runtime.py"
echo "   • scripts/scout_daemon.py"
echo "   • scripts/beta_manager.py"
echo ""
echo "⚠️  Manual steps remaining:"
echo "   1. Review ~/.hermes/profiles/zera/config.yaml"
echo "   2. Test: hermes -p zera status"
echo "   3. If ok, remove: ~/.hermes/profiles/antigravity/"
echo "   4. Update docs/ki/ references"
echo ""
echo "🧪 Test commands:"
echo "   hermes -p zera status"
echo "   hermes -p zera chat -q 'hello'"
echo "   hermes -p zera --model"
echo ""
