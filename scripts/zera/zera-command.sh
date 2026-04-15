#!/usr/bin/env bash
set -euo pipefail
# 4. Background pinger to ensure the title sticks in VS Code (overcoming zsh hooks)
(
  # Give the shell and hermes a moment to initialize
  sleep 0.5
  for i in {1..5}; do
    # Standard xterm sequences
    printf "\033]0;ZeRa\007"
    printf "\033]1;ZeRa\007"
    printf "\033]2;ZeRa\007"
    
    # VS Code specific shell integration sequences
    printf "\033]633;P;Icon=heart\007"
    printf "\033]633;P;TerminalIcon=heart\007"
    printf "\033]633;P;Color=terminal.ansiRed\007"
    printf "\033]633;P;TerminalColor=terminal.ansiRed\007"
    
    sleep 0.5
  done
) & disown

ROOT="${ZERA_REPO_ROOT:-$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}" 2>/dev/null || echo "${BASH_SOURCE[0]}")")" && if [[ $(basename "$(pwd)") == "zera" ]]; then cd ../..; else cd ..; fi && pwd)}"

AGENT_OS="$ROOT/repos/packages/agent-os"

if [[ "${AG_SKIP_PREFLIGHT:-0}" != "1" ]]; then
  if [[ -x "$ROOT/scripts/system_health_check.sh" ]]; then
    "$ROOT/scripts/system_health_check.sh" --quick >/dev/null
  elif [[ -f "$ROOT/scripts/system_health_check.sh" ]]; then
    bash "$ROOT/scripts/system_health_check.sh" --quick >/dev/null
  fi
fi

if [ $# -eq 0 ]; then
  # Default to interactive chat if no arguments
  exec /Users/user/.local/bin/hermes -p zera chat
else
  cd "$AGENT_OS"
  exec uv run python "../../../scripts/zera_command_runtime.py" "$@"
fi
