#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

run_id="$(date +%Y%m%d_%H%M%S)"
out_dir="reports/integrations/21st/benchmarks"
mkdir -p "$out_dir"

csv_file="$out_dir/benchmark_${run_id}.csv"
json_file="$out_dir/benchmark_${run_id}.json"

cat > "$csv_file" <<'CSV'
scenario,mode,latency_ms,implementation_time_min,cost_units,ui_quality_score,defect_rate,rework_rate,determinism_score,portability_score,infra_burden_score,onboarding_speed_score,repeated_run_success_rate
ui-landing-premium,internal-only,0,0,0,0,0,0,0,0,0,0,0
ui-landing-premium,21st-assisted,0,0,0,0,0,0,0,0,0,0,0
dashboard-analytics,internal-only,0,0,0,0,0,0,0,0,0,0,0
dashboard-analytics,21st-assisted,0,0,0,0,0,0,0,0,0,0,0
support-agent-faq,hermes-runtime,0,0,0,0,0,0,0,0,0,0,0
support-agent-faq,21st-runtime,0,0,0,0,0,0,0,0,0,0,0
CSV

python3 - <<PY
import json
from datetime import datetime
report = {
  "run_id": "${run_id}",
  "timestamp": datetime.utcnow().isoformat() + "Z",
  "purpose": "21st integration benchmark scaffold",
  "inputs": {
    "csv": "${csv_file}",
    "scenarios": [
      "ui-landing-premium",
      "dashboard-analytics",
      "support-agent-faq",
      "docs-agent-ingest",
      "research-agent-brief"
    ]
  },
  "thresholds": {
    "speed_uplift_min_pct": 20,
    "ui_quality_uplift_min_pct": 15,
    "determinism_drift_max_pct": 5,
    "fallback_success_min_pct": 99
  },
  "status": "scaffold_generated"
}
with open("${json_file}", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("benchmark csv:", "${csv_file}")
print("benchmark json:", "${json_file}")
PY

echo "[21st-benchmark] scaffold created"
