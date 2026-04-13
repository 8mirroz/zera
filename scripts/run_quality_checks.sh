#!/usr/bin/env bash
# Thin entrypoint for the reliability platform pre-commit profile.
set -euo pipefail

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT="$(git rev-parse --show-toplevel)"
else
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fi
MODE="${1:-pre_commit}"
AGENT_OS="$ROOT/repos/packages/agent-os"

if [[ -z "${ROOT:-}" ]]; then
  echo "ERROR: failed to resolve repository root" >&2
  exit 2
fi

if [[ ! -d "$ROOT" ]]; then
  echo "ERROR: resolved root does not exist: $ROOT" >&2
  exit 2
fi

if [[ ! -d "$AGENT_OS" ]]; then
  echo "ERROR: agent-os directory not found: $AGENT_OS" >&2
  exit 2
fi

if [[ "${AG_SKIP_PREFLIGHT:-0}" != "1" ]]; then
  if [[ -x "$ROOT/scripts/system_health_check.sh" ]]; then
    "$ROOT/scripts/system_health_check.sh" --quick
  elif [[ -f "$ROOT/scripts/system_health_check.sh" ]]; then
    bash "$ROOT/scripts/system_health_check.sh" --quick
  else
    echo "WARN: preflight health check script missing: $ROOT/scripts/system_health_check.sh" >&2
  fi
fi

cd "$ROOT"

if [[ "${QUALITY_DEBUG:-0}" == "1" ]]; then
  echo "[quality] root=$ROOT mode=$MODE" >&2
fi

if [[ "$MODE" == "--quick" || "$MODE" == "quick" ]]; then
  MODE="local_quick"
fi

if [[ "$MODE" == "pre-commit" ]]; then
  MODE="pre_commit"
fi

case "$MODE" in
  pre_commit|local_quick|ci_required|nightly|all_non_benchmark)
    ;;
  *)
    echo "Unknown reliability profile: $MODE" >&2
    echo "Allowed: pre-commit, local_quick, ci_required, nightly, all_non_benchmark" >&2
    exit 2
    ;;
esac

exec bash -lc "cd \"$AGENT_OS\" && uv run python ../../../scripts/reliability_orchestrator.py run --profile \"$MODE\""
