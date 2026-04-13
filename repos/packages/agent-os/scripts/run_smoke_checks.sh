#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p logs
TRACE_FILE="$(mktemp "$ROOT_DIR/logs/smoke-trace.XXXXXX")"
export AGENT_OS_TRACE_FILE="$TRACE_FILE"

python3 repos/packages/agent-os/scripts/swarmctl.py smoke
python3 repos/packages/agent-os/scripts/swarmctl.py route "fix typo in README" --task-type T2 --complexity C1
python3 repos/packages/agent-os/scripts/swarmctl.py run "verify baseline route and memory"
python3 repos/packages/agent-os/scripts/trace_validator.py --json --allow-legacy --file "$TRACE_FILE"
python3 repos/packages/agent-os/scripts/trace_metrics_materializer.py --allow-legacy --file "$TRACE_FILE" --out logs/smoke-trace-metrics.json
