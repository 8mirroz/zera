#!/usr/bin/env bash
set -euo pipefail

MODE="full"
JSON=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)
      MODE="quick"
      ;;
    --json)
      JSON=1
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
else
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi

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
  py_path="$(python3 - "$cfg" <<'PY'
import json
import sys
from pathlib import Path
cfg=Path(sys.argv[1])
data=json.loads(cfg.read_text(encoding="utf-8"))
print(data.get("python_bin",""))
PY
)"
  if [[ -z "$py_path" || ! -x "$py_path" ]]; then
    add_fail "python_bin_missing_or_not_executable:$py_path"
    return
  fi
  local py_info
  py_info="$("$py_path" - <<'PY'
import platform, sys
print(platform.machine(), sys.version_info.major, sys.version_info.minor)
PY
)"
  local py_arch py_major py_minor
  py_arch="$(awk '{print $1}' <<<"$py_info")"
  py_major="$(awk '{print $2}' <<<"$py_info")"
  py_minor="$(awk '{print $3}' <<<"$py_info")"
  if [[ "$py_arch" != "arm64" ]]; then
    add_fail "python_arch_not_arm64:$py_arch:$py_path"
  elif [[ "$py_major" -lt 3 || ( "$py_major" -eq 3 && "$py_minor" -lt 11 ) ]]; then
    add_fail "python_version_lt_3_11:${py_major}.${py_minor}:$py_path"
  else
    add_check "python_ok:${py_major}.${py_minor}:$py_path"
  fi
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
  if [[ "${#CHECKS[@]}" -gt 0 ]]; then
    export AG_HEALTH_CHECKS="$(printf '%s\n' "${CHECKS[@]}")"
  else
    export AG_HEALTH_CHECKS=""
  fi
  if [[ "${#WARNS[@]}" -gt 0 ]]; then
    export AG_HEALTH_WARNS="$(printf '%s\n' "${WARNS[@]}")"
  else
    export AG_HEALTH_WARNS=""
  fi
  if [[ "${#FAILS[@]}" -gt 0 ]]; then
    export AG_HEALTH_FAILS="$(printf '%s\n' "${FAILS[@]}")"
  else
    export AG_HEALTH_FAILS=""
  fi
  python3 - "$MODE" "$ROOT" <<'PY'
import json
import os
import sys

mode = sys.argv[1]
root = sys.argv[2]
checks = [x for x in os.environ.get("AG_HEALTH_CHECKS", "").splitlines() if x]
warns = [x for x in os.environ.get("AG_HEALTH_WARNS", "").splitlines() if x]
fails = [x for x in os.environ.get("AG_HEALTH_FAILS", "").splitlines() if x]
print(
    json.dumps(
        {
            "mode": mode,
            "root": root,
            "checks": checks,
            "warnings": warns,
            "failures": fails,
            "status": "fail" if fails else "pass",
        },
        ensure_ascii=False,
    )
)
PY
  if [[ "${#FAILS[@]}" -gt 0 ]]; then
    exit 1
  fi
  exit 0
fi

echo "[health] mode=$MODE root=$ROOT"
for c in "${CHECKS[@]:-}"; do
  [[ -n "$c" ]] || continue
  echo "[OK]   $c"
done
for w in "${WARNS[@]:-}"; do
  [[ -n "$w" ]] || continue
  echo "[WARN] $w"
done
for f in "${FAILS[@]:-}"; do
  [[ -n "$f" ]] || continue
  echo "[FAIL] $f"
done

if [[ "${#FAILS[@]}" -gt 0 ]]; then
  exit 1
fi

exit 0
