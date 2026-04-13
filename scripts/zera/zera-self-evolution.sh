#!/bin/bash
# ============================================
# Zera Self-Evolution Control Plane Bootstrap
# Prepares a governed dual-loop cycle without bypassing review surfaces.
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ ! -d "$DEFAULT_ROOT/configs" ]]; then
  DEFAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
REPO_ROOT="${ZERA_REPO_ROOT:-$DEFAULT_ROOT}"
VAULT="${VAULT_PATH:-$HOME/antigravity-vault}"
RESEARCH_DIR="$VAULT/research"
CONTROL_DIR="$RESEARCH_DIR/_control"
LOG_DIR="$RESEARCH_DIR/logs"
REPORT_DIR="$RESEARCH_DIR/reports"
MANIFEST_DIR="$RESEARCH_DIR/manifests"
PROMOTION_DIR="$RESEARCH_DIR/promotions"
REJECTION_DIR="$RESEARCH_DIR/rejections"
CANDIDATE_DIR="$RESEARCH_DIR/candidates"
DISCUSSION_DIR="$RESEARCH_DIR/discussions"
GOVERNOR_DIR="$RESEARCH_DIR/governor"
BRANCH_DIR="$RESEARCH_DIR/branches"
SOURCE_CARD_DIR="$RESEARCH_DIR/source-cards"

GOVERNANCE_CONFIG="$REPO_ROOT/configs/tooling/zera_growth_governance.json"
COMMAND_REGISTRY="$REPO_ROOT/configs/tooling/zera_command_registry.yaml"
CLIENT_PROFILES="$REPO_ROOT/configs/tooling/zera_client_profiles.yaml"
BRANCH_POLICY="$REPO_ROOT/configs/tooling/zera_branching_policy.yaml"
RESEARCH_REGISTRY="$REPO_ROOT/configs/tooling/zera_research_registry.yaml"
FOUNDRY_REGISTRY="$REPO_ROOT/configs/tooling/zera_skill_foundry.yaml"
EXTERNAL_IMPORTS="$REPO_ROOT/configs/tooling/zera_external_imports.yaml"
PROTOCOL_DOC="$REPO_ROOT/configs/personas/zera/SELF_EVOLUTION_PROTOCOL.md"
WORKFLOW_DOC="$REPO_ROOT/configs/personas/zera/ZERA_SELF_EVOLUTION_WORKFLOW.md"
EVAL_CASES="$REPO_ROOT/configs/personas/zera/eval_cases.json"
FREEZE_FILE="$CONTROL_DIR/freeze-state.json"
EVENT_LOG="$LOG_DIR/evolution-events.jsonl"

DRY_RUN=false
FORCE=false
LOOP_MODE="dual"
ALLOW_PERSONALITY_PROMOTION=false

RUN_ID="$(date +"%Y%m%dT%H%M%S")-$$"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

log()   { echo -e "${CYAN}[ZERA-EVO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}        $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}      $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}      $1"; }
title() { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }

usage() {
    cat <<'EOF'
Usage: bash scripts/zera-self-evolution.sh [--dry-run] [--force] [--loop capability|personality|dual] [--allow-personality-promotion]

This script prepares the governed Zera self-evolution control plane.
It does not auto-promote governance or personality changes.
EOF
}

event_log() {
    local event_type="$1"
    local decision="$2"
    local message="$3"
    python3 - "$EVENT_LOG" "$RUN_ID" "$TS" "$event_type" "$decision" "$LOOP_MODE" "$message" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "ts": sys.argv[3],
    "run_id": sys.argv[2],
    "event_type": sys.argv[4],
    "candidate_id": None,
    "candidate_class": None,
    "loop": sys.argv[6],
    "target_layer": "zera_self_evolution",
    "risk_level": "n/a",
    "governance_impact": "none",
    "decision": sys.argv[5],
    "eval_suite": [],
    "rollback_path": None,
    "source": "scripts/zera-self-evolution.sh",
    "command_id": None,
    "client_id": "repo_native",
    "branch_id": None,
    "branch_type": None,
    "import_lane": None,
    "source_license": None,
    "trust_score": None,
    "message": sys.argv[7],
}
with path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
PY
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                ;;
            --force)
                FORCE=true
                ;;
            --loop)
                shift
                LOOP_MODE="${1:-dual}"
                ;;
            --allow-personality-promotion)
                ALLOW_PERSONALITY_PROMOTION=true
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                fail "Unknown argument: $1"
                usage
                exit 2
                ;;
        esac
        shift
    done

    case "$LOOP_MODE" in
        capability|personality|dual) ;;
        *)
            fail "Invalid loop mode: $LOOP_MODE"
            exit 2
            ;;
    esac
}

require_files() {
    local missing=0
    for path in "$GOVERNANCE_CONFIG" "$COMMAND_REGISTRY" "$CLIENT_PROFILES" "$BRANCH_POLICY" "$RESEARCH_REGISTRY" "$FOUNDRY_REGISTRY" "$EXTERNAL_IMPORTS" "$PROTOCOL_DOC" "$WORKFLOW_DOC" "$EVAL_CASES"; do
        if [ ! -f "$path" ]; then
            fail "Missing required file: $path"
            missing=1
        fi
    done
    if [ "$missing" -ne 0 ]; then
        exit 2
    fi
}

ensure_dirs() {
    mkdir -p \
        "$CONTROL_DIR" \
        "$LOG_DIR" \
        "$REPORT_DIR" \
        "$MANIFEST_DIR" \
        "$PROMOTION_DIR" \
        "$REJECTION_DIR" \
        "$CANDIDATE_DIR" \
        "$DISCUSSION_DIR" \
        "$GOVERNOR_DIR" \
        "$BRANCH_DIR" \
        "$SOURCE_CARD_DIR" \
        "$VAULT/memory/zera"
}

ensure_freeze_state() {
    if [ ! -f "$FREEZE_FILE" ]; then
        python3 - "$FREEZE_FILE" "$TS" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "state": "active",
    "updated_at": sys.argv[2],
    "reason": None,
    "resume_conditions": [],
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
        ok "Initialized freeze-state control file"
    fi

    if python3 - "$FREEZE_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
state = json.loads(path.read_text(encoding="utf-8"))
raise SystemExit(0 if state.get("state") == "frozen" else 1)
PY
    then
        if [ "$FORCE" != true ]; then
            fail "Evolution is frozen. Review $FREEZE_FILE or rerun with --force after operator decision."
            event_log "cycle_blocked" "blocked" "freeze-state active"
            exit 3
        fi
        warn "Freeze-state is active, but --force was supplied"
    fi
}

write_manifest_snapshot() {
    local out="$MANIFEST_DIR/zera-growth-governance.${RUN_ID}.json"
    python3 - "$GOVERNANCE_CONFIG" "$out" "$RUN_ID" "$TS" "$LOOP_MODE" "$ALLOW_PERSONALITY_PROMOTION" <<'PY'
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dest = Path(sys.argv[2])
payload = json.loads(src.read_text(encoding="utf-8"))
snapshot = {
    "run_id": sys.argv[3],
    "created_at": sys.argv[4],
    "loop_mode": sys.argv[5],
    "allow_personality_promotion": sys.argv[6].lower() == "true",
    "governance": payload,
}
dest.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
    ok "Governance snapshot written: $out"
}

write_candidate_template() {
    local out="$CANDIDATE_DIR/candidate-template.json"
    python3 - "$GOVERNANCE_CONFIG" "$FOUNDRY_REGISTRY" "$out" <<'PY'
import json
import sys
from pathlib import Path

governance = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
foundry = Path(sys.argv[2]).read_text(encoding="utf-8")
template = {
    "candidate_id": "candidate-YYYYMMDD-N",
    "source": "repo|research|operator|drift",
    "candidate_class": "skill_refinement",
    "candidate_type": "skill_refinement",
    "lane_owner": "zera-core",
    "loop": "capability",
    "target_layer": "skill|workflow|memory|persona|policy|tooling",
    "governance_impact": "none|adjacent|direct",
    "risk_level": "low|medium|high|critical",
    "reversibility": "easy|moderate|hard",
    "required_evidence": [
        "source provenance",
        "reason for change",
        "expected effect"
    ],
    "eval_suite": governance["candidate_classes"]["skill_refinement"]["eval_suite"],
    "promotion_gate": "auto_after_eval|review_required|operator_only",
    "rollback_path": "path or procedure",
    "overlap_result": "extend_existing|new_skill|reject_duplicate",
    "provenance": "internal|external",
    "import_lane": "none|direct_vendor_adapt|isolated_optional_component_only|concept_reference_quarantine|discovery_index_only",
    "quarantine_status": "none|review|required",
    "status": "observed",
    "notes": ""
}
Path(sys.argv[3]).write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
    ok "Candidate template refreshed: $out"
}

write_governor_ledger_template() {
    local out="$GOVERNOR_DIR/governor-state.json"
    python3 - "$GOVERNANCE_CONFIG" "$out" "$TS" <<'PY'
import json
import sys
from pathlib import Path

governance = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
axes = governance.get("personality_governor", {}).get("axes", {})
payload = {
    "updated_at": sys.argv[3],
    "axes": axes,
    "last_promoted_delta": None,
    "consecutive_personality_regressions": 0,
}
Path(sys.argv[2]).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
    ok "Governor ledger template refreshed: $out"
}

write_branch_template() {
    local out="$BRANCH_DIR/branch-template.json"
    python3 - "$BRANCH_POLICY" "$out" <<'PY'
import json
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    raise SystemExit("PyYAML required for branch template generation")

data = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
template = {
    "branch_id": "branch-YYYYMMDD-N",
    "branch_type": "strategy_branch",
    "parent_run_id": "run-YYYYMMDD-N",
    "source_command": "zera:branch",
    "origin_prompt": "objective",
    "allowed_tools": ["research"],
    "max_turns": 6,
    "ttl_minutes": data.get("defaults", {}).get("ttl_minutes", 90),
    "merge_policy": "summary_with_candidate_cards",
    "candidate_emission_allowed": True,
    "stable_memory_write_allowed": False,
    "personality_promotion_allowed": False,
}
Path(sys.argv[2]).write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
    ok "Branch template refreshed: $out"
}

write_ledgers() {
    local promo="$PROMOTION_DIR/promotions.jsonl"
    local reject="$REJECTION_DIR/rejections.jsonl"
    local report="$REPORT_DIR/evolution-cycle-${RUN_ID}.md"

    touch "$promo" "$reject" "$EVENT_LOG"
    touch "$GOVERNOR_DIR/personality-delta-ledger.jsonl" "$GOVERNOR_DIR/governor-rollbacks.jsonl"

    cat > "$report" <<EOF
# Zera Evolution Cycle Bootstrap — ${RUN_ID}

## Control State
- loop_mode: \`${LOOP_MODE}\`
- dry_run: \`${DRY_RUN}\`
- allow_personality_promotion: \`${ALLOW_PERSONALITY_PROMOTION}\`
- governance_config: \`${GOVERNANCE_CONFIG}\`
- freeze_file: \`${FREEZE_FILE}\`

## What This Run Did
- verified governance sources exist
- checked freeze state before any evolution work
- snapshotted machine-readable governance rules
- refreshed candidate template, branch template, and governor ledgers
- prepared event logging and report directories

## What This Run Did Not Do
- no external search
- no candidate promotion
- no governance mutation
- no personality promotion without review
- no stable-memory write from unreviewed intelligence

## Required Next Step
- run a bounded evolution execution through \`scripts/zera-evolve.sh\`
- or use the generated control artifacts for an operator-reviewed cycle
EOF

    ok "Cycle report created: $report"
}

main() {
    parse_args "$@"
    title "Zera Self-Evolution Control Plane"
    log "run_id=$RUN_ID loop_mode=$LOOP_MODE dry_run=$DRY_RUN"

    require_files
    ensure_dirs
    ensure_freeze_state

    if [ "$DRY_RUN" = true ]; then
        warn "Dry run enabled: control-plane bootstrap will still refresh local scaffolding only"
    fi

    write_manifest_snapshot
    write_candidate_template
    write_governor_ledger_template
    write_branch_template
    write_ledgers
    event_log "cycle_initialized" "initialized" "governed self-evolution control plane ready"

    echo ""
    ok "Zera self-evolution control plane is ready"
    echo "Control directory : $CONTROL_DIR"
    echo "Event log         : $EVENT_LOG"
    echo "Reports           : $REPORT_DIR"
    echo "Candidates        : $CANDIDATE_DIR"
    echo "Branches          : $BRANCH_DIR"
    echo "Governor          : $GOVERNOR_DIR"
}

main "$@"
