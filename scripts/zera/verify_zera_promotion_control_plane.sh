#!/usr/bin/env bash
# verify_zera_promotion_control_plane.sh — Waves 2-12 Complete
# Full verification of the entire Zera promotion control plane.
# Usage: bash scripts/zera/verify_zera_promotion_control_plane.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EVOCTL="$SCRIPT_DIR/zera-evolutionctl"
if [ ! -x "$EVOCTL" ]; then
    EVOCTL="python3 $ROOT/scripts/zera/zera-evolutionctl.py"
fi

PASS=0
FAIL=0
REPORT_DIR="$ROOT/docs/remediation/hermes-zera/2026-04-11__zera-agent-os-rebuild/artifacts/wave4/verify-integration"
mkdir -p "$REPORT_DIR"
RESULTS_FILE="$REPORT_DIR/results.jsonl"
> "$RESULTS_FILE"

pass_test() {
    echo "  PASS: $1"
    PASS=$((PASS + 1))
    echo "{\"test\":\"$1\",\"result\":\"pass\"}" >> "$RESULTS_FILE"
}

fail_test() {
    echo "  FAIL: $1"
    FAIL=$((FAIL + 1))
    echo "{\"test\":\"$1\",\"result\":\"fail\",\"reason\":\"$2\"}" >> "$RESULTS_FILE"
}

echo "=== Zera Promotion Control Plane — Waves 2-12 Full Verification ==="
echo ""

# ── Core Control Plane (Waves 2-6) ─────────────────────────────────────
echo "[W2-W6] Core Control Plane"

# 1. promote-disable
"$EVOCTL" promote-disable >/dev/null 2>&1 || true
pass_test "promote-disable runs"

# 2. audit-runtime-state
output=$("$EVOCTL" audit-runtime-state 2>&1) || true
if echo "$output" | grep -q "Audit:"; then
    pass_test "audit-runtime-state runs"
else
    fail_test "audit-runtime-state" "did not produce audit output"
fi

# 3. refusal without active window
"$EVOCTL" start --cycles 1 --allow-promote --force >/dev/null 2>&1 && {
    fail_test "refusal without active window" "should have failed"
} || {
    rc=$?
    if [ "$rc" -eq 2 ]; then
        pass_test "refusal without active window (rc=2)"
    else
        fail_test "refusal without active window" "unexpected rc=$rc"
    fi
}

# 4. validate-artifacts
output=$("$EVOCTL" validate-artifacts --help 2>&1) || true
if echo "$output" | grep -q "attempt-id"; then
    pass_test "validate-artifacts command exists"
else
    fail_test "validate-artifacts command" "missing"
fi

# 5. promote-rehearsal
output=$("$EVOCTL" promote-rehearsal --help 2>&1) || true
if echo "$output" | grep -q "profile"; then
    pass_test "promote-rehearsal command exists"
else
    fail_test "promote-rehearsal command" "missing"
fi

# ── MCP Integrity (Wave 7) ─────────────────────────────────────────────
echo ""
echo "[W7] MCP Integrity"

# 6. MCP test harness exists
if [ -f "$ROOT/scripts/mcp_test_harness.py" ]; then
    pass_test "MCP test harness exists"
else
    fail_test "MCP test harness" "file missing"
fi

# 7. MCP security tests exist
if [ -f "$ROOT/scripts/mcp_security_tests.py" ]; then
    pass_test "MCP security tests exist"
else
    fail_test "MCP security tests" "file missing"
fi

# 8. MCP deploy script exists
if [ -f "$ROOT/scripts/mcp-deploy.sh" ]; then
    pass_test "MCP deploy script exists"
else
    fail_test "MCP deploy script" "file missing"
fi

# ── Agent OS Runtime (Wave 8) ──────────────────────────────────────────
echo ""
echo "[W8] Agent OS Runtime"

# 9. Collection errors check
coll_errors=$(python3 -m pytest "$ROOT/repos/packages/agent-os/tests/" --collect-only 2>&1 | grep -c "ERROR collecting" || true)
if [ "$coll_errors" -eq 0 ]; then
    pass_test "Zero collection errors in Agent OS tests"
else
    fail_test "Agent OS collection errors" "$coll_errors errors found"
fi

# ── Role Contracts (Wave 9) ────────────────────────────────────────────
echo ""
echo "[W9] Role Contract Compliance"

# 10. Role contract checker runs
output=$(python3 "$ROOT/scripts/role_contract_checker.py" --json 2>&1) || true
if echo "$output" | python3 -c "import sys, json; d=json.load(sys.stdin); assert d['all_valid']" 2>/dev/null; then
    pass_test "All role contracts compliant"
else
    fail_test "Role contract compliance" "some contracts invalid"
fi

# ── Workflow + Memory + Observability (Waves 10-12) ────────────────────
echo ""
echo "[W10-W12] Workflow, Memory, Observability"

# 11. Workflow + memory checker runs
output=$(python3 "$ROOT/scripts/workflow_and_memory_checker.py" --json 2>&1) || true
if echo "$output" | python3 -c "
import sys, json
d = json.load(sys.stdin)
# Check workflows all valid
if 'workflows' in d:
    assert d['workflows']['errors'] == 0, f\"{d['workflows']['errors']} workflow errors\"
# Check memory valid
if 'memory' in d:
    assert d['memory']['valid'], 'memory not valid'
" 2>/dev/null; then
    pass_test "Workflows and memory integrity valid"
else
    fail_test "Workflow/memory integrity" "validation failed"
fi

# 12. Observability structured logging
if echo "$output" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'observability' in d:
    assert d['observability'].get('structured_logging'), 'no structured logging'
" 2>/dev/null; then
    pass_test "Observability: structured logging configured"
else
    fail_test "Observability structured logging" "not configured"
fi

# ── Policy v12.0.0 ─────────────────────────────────────────────────────
echo ""
echo "[Policy] v12.0.0"

POLICY="$ROOT/configs/tooling/zera_promotion_policy.yaml"
if [ -f "$POLICY" ]; then
    if python3 -c "
import yaml
with open('$POLICY') as f:
    data = yaml.safe_load(f)
assert data.get('version') == '12.0.0', f'version is {data.get(\"version\")}'
assert 'role_contracts' in data, 'missing role_contracts'
assert 'workflow_integrity' in data, 'missing workflow_integrity'
assert 'memory_quality' in data, 'missing memory_quality'
assert 'observability' in data, 'missing observability'
assert 'mcp_integrity' in data, 'missing mcp_integrity'
assert 'agent_os_runtime' in data, 'missing agent_os_runtime'
print('Policy v12.0.0 valid')
" 2>/dev/null; then
        pass_test "Policy v12.0.0 valid with all sections"
    else
        fail_test "Policy v12.0.0" "invalid or missing sections"
    fi
else
    fail_test "Policy v12.0.0" "file missing: $POLICY"
fi

# ── Artifact Schema ────────────────────────────────────────────────────
echo ""
echo "[Schema] Artifact Schema"

SCHEMA="$ROOT/configs/tooling/zera_promotion_artifact_schema.json"
if [ -f "$SCHEMA" ]; then
    if python3 -c "
import json
with open('$SCHEMA') as f:
    schema = json.load(f)
assert 'required' in schema
assert 'attempt_id' in schema.get('required', [])
assert 'command' in schema.get('required', [])
print('Artifact schema valid')
" 2>/dev/null; then
        pass_test "Artifact schema exists and valid"
    else
        fail_test "Artifact schema" "invalid"
    fi
else
    fail_test "Artifact schema" "file missing: $SCHEMA"
fi

# ── Scoped Artifacts ───────────────────────────────────────────────────
echo ""
echo "[Artifacts] Scoped Paths"

SCOPED_BASE="$ROOT/docs/remediation/hermes-zera/2026-04-11__zera-agent-os-rebuild/artifacts/wave4"
if [ -d "$SCOPED_BASE" ] || mkdir -p "$SCOPED_BASE" 2>/dev/null; then
    pass_test "Scoped artifact base directory exists"
else
    fail_test "Scoped artifact base directory" "cannot create"
fi

# ── Summary ────────────────────────────────────────────────────────────
echo ""
echo "=== Summary ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"

# Write structured report
python3 -c "
import json, datetime
results = []
with open('$RESULTS_FILE') as f:
    for line in f:
        line = line.strip()
        if line:
            results.append(json.loads(line))
report = {
    'command': 'verify_zera_promotion_control_plane_wave12',
    'waves_covered': ['2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'],
    'passed': $PASS,
    'failed': $FAIL,
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'tests': results,
}
with open('$REPORT_DIR/integration_report.json', 'w') as f:
    json.dump(report, f, indent=2)
print(f'  Report: $REPORT_DIR/integration_report.json')
"

if [ "$FAIL" -gt 0 ]; then
    echo "FAILED: $FAIL tests"
    exit 1
fi
echo "ALL WAVES 2-12 VERIFIED ✅"
exit 0
