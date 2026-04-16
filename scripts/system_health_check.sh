#!/usr/bin/env bash
set -euo pipefail

# --- CONFIGURATION ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODE="full"
JSON=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick) MODE="quick" ;;
    --json)  JSON=1 ;;
    *)       echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

FAILS=()
WARNS=()
CHECKS=()

add_check() {
  CHECKS+=("$1")
}

add_fail() {
  FAILS+=("$1")
}

add_warn() {
  WARNS+=("$1")
}

check_repo_root() {
  if [[ ! -d "$ROOT" ]]; then
    add_fail "repo_root_missing:$ROOT"
    return
  fi
  add_check "repo_root_ok:$ROOT"
}

check_git_integrity() {
  if [[ -d "$ROOT/.git" ]]; then
    add_check "git_dir_ok"
  elif [[ -f "$ROOT/.git" ]]; then
    add_fail "git_is_link_file:$ROOT/.git"
  else
    add_fail "git_metadata_missing"
  fi
}

check_architecture() {
  local machine
  machine="$(uname -m)"
  if [[ "$machine" != "arm64" ]]; then
    add_fail "host_arch_not_arm64:$machine"
  else
    add_check "host_arch_ok:$machine"
  fi
}

check_uv() {
  if ! command -v uv >/dev/null 2>&1; then
    add_fail "uv_missing"
    return
  fi
  local uv_path uv_file
  uv_path="$(command -v uv)"
  uv_file="$(file "$uv_path" 2>/dev/null || true)"
  if [[ "$uv_file" != *"arm64"* ]]; then
    add_warn "uv_not_arm64:$uv_path"
  else
    add_check "uv_ok:$uv_path"
  fi
}

check_python_runtime() {
  local cfg py_path
  cfg="$ROOT/configs/tooling/notebooklm_integration.json"
  if [[ ! -f "$cfg" ]]; then
    add_fail "notebooklm_config_missing:$cfg"
    return
  fi
  
  py_path=$(python3 -c "
import json, sys, os
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text())
    print(data.get('python_bin',''))
except: pass
" "$cfg" 2>/dev/null)

  if [[ -z "$py_path" || ! -x "$py_path" ]]; then
    add_fail "python_bin_missing_or_not_executable:$py_path"
    return
  fi

  local py_info
  py_info=$("$py_path" -c "
import platform, sys, os
print(f'{platform.machine()} {sys.version_info.major} {sys.version_info.minor}')
" 2>/dev/null)

  # Robust parsing with python to avoid awk/tr issues
  python3 -c "
import sys
try:
    info = sys.argv[1].split()
    arch, major, minor = info[0], int(info[1]), int(info[2])
    if arch != 'arm64':
        print('FAIL:python_arch_not_arm64:' + arch)
    elif major < 3 or (major == 3 and minor < 11):
        print(f'FAIL:python_version_lt_3_11:{major}.{minor}')
    else:
        print(f'OK:python_ok:{major}.{minor}')
except:
    print('FAIL:python_info_parsing_failed')
" "$py_info" | while read -r line; do
    case "$line" in
        OK:*)   add_check "${line#OK:}:$py_path" ;;
        FAIL:*) add_fail "${line#FAIL:}:$py_path" ;;
    esac
  done
}

check_notebooklm() {
  if [[ "$MODE" == "quick" ]]; then
    return
  fi
  local report
  if ! report="$(python3 "$ROOT/repos/packages/agent-os/scripts/swarmctl.py" notebooklm-doctor --json 2>/dev/null)"; then
    add_fail "notebooklm_doctor_exec_failed"
    return
  fi
  if grep -q '"status": "pass"' <<<"$report"; then
    add_check "notebooklm_doctor_pass"
  else
    add_fail "notebooklm_doctor_not_pass"
  fi
}

check_qmd() {
  if command -v qmd >/dev/null 2>&1; then
    add_check "qmd_ok:$(command -v qmd)"
  else
    if [[ "$MODE" == "quick" ]]; then
      add_warn "qmd_missing"
    else
      add_fail "qmd_missing"
    fi
  fi
}

check_broken_symlinks() {
  local broken_count
  broken_count="$(find -L "$ROOT" -type l 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$broken_count" != "0" ]]; then
    add_fail "broken_symlinks:$broken_count"
  else
    add_check "broken_symlinks_ok"
  fi
}

check_env_consistency() {
  if [[ ! -f "$ROOT/.env" ]]; then
    add_warn "env_file_missing"
    return
  fi
  if ! grep -q '^[[:space:]]*\(export[[:space:]]\+\)\?OPENROUTER_API_KEY=' "$ROOT/.env"; then
    add_warn "openrouter_key_missing"
  else
    add_check "openrouter_key_present"
  fi
}

# --- TRAPS ---
cleanup() { :; }
trap cleanup EXIT
trap 'echo -e "\nInterrupted"; exit 130' INT TERM

# --- EXECUTION ---
if [[ "$JSON" -eq 0 ]]; then
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ⚕  Antigravity Core System Health Check                  ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo -e "${BLUE}[SYSTEM]${NC} Mode: $MODE | Root: $ROOT"
    echo ""
fi

# Run checks
check_repo_root
check_git_integrity
check_architecture
check_uv
check_python_runtime
check_qmd
check_broken_symlinks
check_env_consistency
check_notebooklm

if [[ "$JSON" -eq 1 ]]; then
  # Structured JSON output consistent with Hermes dashboard
  # Export lists for python helper
  export AG_CHECKS="$(printf '%s\n' "${CHECKS[@]:-}")"
  export AG_WARNS="$(printf '%s\n' "${WARNS[@]:-}")"
  export AG_FAILS="$(printf '%s\n' "${FAILS[@]:-}")"
  export AG_MODE="$MODE"
  export AG_ROOT="$ROOT"
  
  python3 - <<'PY'
import json, os, sys
from datetime import datetime
checks = os.environ.get("AG_CHECKS", "").splitlines()
warns = os.environ.get("AG_WARNS", "").splitlines()
fails = os.environ.get("AG_FAILS", "").splitlines()
print(json.dumps({
    "service": "antigravity-core",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "status": "healthy" if not fails else "critical",
    "mode": os.environ.get("AG_MODE", "full"),
    "repository_root": os.environ.get("AG_ROOT"),
    "checks": [c for c in checks if c],
    "warnings": [w for w in warns if w],
    "failures": [f for f in fails if f]
}, indent=2))
PY
  [[ ${#FAILS[@]} -eq 0 ]] || exit 1
  exit 0
fi

# Human readable output
for c in "${CHECKS[@]:-}"; do [[ -n "$c" ]] && echo -e "${GREEN}[OK]${NC}     $c"; done
for w in "${WARNS[@]:-}"; do [[ -n "$w" ]] && echo -e "${YELLOW}[WARN]${NC}   $w"; done
for f in "${FAILS[@]:-}"; do [[ -n "$f" ]] && echo -e "${RED}[FAIL]${NC}   $f"; done

echo ""
if [[ ${#FAILS[@]} -eq 0 ]]; then
  echo -e "${GREEN}✅ System healthy${NC}"
  exit 0
else
  echo -e "${RED}❌ System issues detected (${#FAILS[@]} failures)${NC}"
  exit 1
fi
