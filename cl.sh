#!/bin/bash

# OmniRoute Launcher for Claude Code — Zera Edition
# Usage: ./cl.sh [combo_name] [additional_args...]

# 1. Configuration
export CLAUDE_BASE_URL="http://localhost:20128/v1"
export ANTHROPIC_API_KEY="00000" # OmniRoute handles actual keys

# 2. Determine Model (Combo)
# If first arg matches a known combo, use it as model, shift args.
# Otherwise default to 'engineer'.
COMBO="engineer"
if [[ "$1" =~ ^(orchestrator|routine_worker|engineer|design_lead|reviewer|architect|council|quick_task|heavy_analysis)$ ]]; then
    COMBO="$1"
    shift
fi

echo "🚀 Starting Claude Code via OmniRoute [Combo: $COMBO]..."

# 3. Execution
# Using the found binary path
CLAUDE_BIN="/Users/user/.local/bin/claude"

if [ ! -f "$CLAUDE_BIN" ]; then
    echo "✗ Error: Claude CLI not found at $CLAUDE_BIN"
    exit 1
fi

exec "$CLAUDE_BIN" --model "$COMBO" "$@"
