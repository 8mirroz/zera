#!/bin/bash
# ============================================
# zera evolve — bounded single-cycle execution
# Executes one governed evolution prompt. No infinite loop, no silent governance mutation.
# ============================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ ! -d "$DEFAULT_ROOT/configs" ]]; then
  DEFAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
REPO_ROOT="${ZERA_REPO_ROOT:-$DEFAULT_ROOT}"
VAULT="${VAULT_PATH:-$REPO_ROOT/vault}"
CONTROL_DIR="$VAULT/research/_control"
REPORT_DIR="$VAULT/research/reports"
BRANCH_DIR="$VAULT/research/branches"

GOVERNANCE_CONFIG="$REPO_ROOT/configs/tooling/zera_growth_governance.json"
COMMAND_REGISTRY="$REPO_ROOT/configs/tooling/zera_command_registry.yaml"
CLIENT_PROFILES="$REPO_ROOT/configs/tooling/zera_client_profiles.yaml"
BRANCH_POLICY="$REPO_ROOT/configs/tooling/zera_branching_policy.yaml"
PROTOCOL_DOC="$REPO_ROOT/configs/personas/zera/SELF_EVOLUTION_PROTOCOL.md"
WORKFLOW_DOC="$REPO_ROOT/configs/personas/zera/ZERA_SELF_EVOLUTION_WORKFLOW.md"
EVAL_CASES="$REPO_ROOT/configs/personas/zera/eval_cases.json"
FREEZE_FILE="$CONTROL_DIR/freeze-state.json"
COMMAND_BRIDGE="$REPO_ROOT/scripts/zera-command.sh"

DRY_RUN=false
FORCE=false
PROMPT_ONLY=false
LOOP_MODE="capability"
ALLOW_PERSONALITY_PROMOTION=false

LOOPS_DIR="$VAULT/loops"
RUN_ID="$(date +"%Y%m%dT%H%M%S")-$$"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

usage() {
    cat <<'EOF'
Usage: bash scripts/zera-evolve.sh [--dry-run] [--prompt-only] [--force] [--loop capability|personality|dual] [--allow-personality-promotion]

Runs exactly one governed evolution cycle prompt.
EOF
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                ;;
            --prompt-only)
                PROMPT_ONLY=true
                ;;
            --force)
                FORCE=true
                ;;
            --loop)
                shift
                LOOP_MODE="${1:-capability}"
                ;;
            --allow-personality-promotion)
                ALLOW_PERSONALITY_PROMOTION=true
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown argument: $1" >&2
                usage
                exit 2
                ;;
        esac
        shift
    done

    case "$LOOP_MODE" in
        capability|personality|dual) ;;
        *)
            echo "Invalid loop mode: $LOOP_MODE" >&2
            exit 2
            ;;
    esac
}

require_files() {
    local missing=0
    for path in "$GOVERNANCE_CONFIG" "$COMMAND_REGISTRY" "$CLIENT_PROFILES" "$BRANCH_POLICY" "$PROTOCOL_DOC" "$WORKFLOW_DOC" "$EVAL_CASES" "$COMMAND_BRIDGE"; do
        if [ ! -f "$path" ]; then
            echo "Missing required file: $path" >&2
            missing=1
        fi
    done
    if [ "$missing" -ne 0 ]; then
        exit 2
    fi
}

check_freeze() {
    if [ ! -f "$FREEZE_FILE" ]; then
        echo "Missing freeze-state file. Run scripts/zera-self-evolution.sh first." >&2
        exit 2
    fi

    if python3 - "$FREEZE_FILE" <<'PY'
import json
import sys
from pathlib import Path

state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
raise SystemExit(0 if state.get("state") == "frozen" else 1)
PY
    then
        if [ "$FORCE" != true ]; then
            echo "Evolution is frozen. Review $FREEZE_FILE or rerun with --force after operator approval." >&2
            exit 3
        fi
    fi
}

pick_loop() {
    local loops=(
        "karpathy"
        "rsi"
        "darwin-goedel"
        "pantheon"
        "self-improving"
        "swarm"
        "ralph"
        "agentic-ci"
        "self-driving"
        "meta-learning"
    )

    mkdir -p "$LOOPS_DIR"
    local state_file="$LOOPS_DIR/.evolve-state"
    local current_index=0
    if [ -f "$state_file" ]; then
        current_index="$(cat "$state_file" 2>/dev/null || echo "0")"
    fi

    local next_index=$(( (current_index + 1) % ${#loops[@]} ))
    CURRENT_LOOP="${loops[$current_index]}"
    NEXT_LOOP="${loops[$next_index]}"
    echo "$next_index" > "$state_file"
}

build_prompt() {
    local personality_line
    if [ "$ALLOW_PERSONALITY_PROMOTION" = true ]; then
        personality_line="Personality loop is allowed, but you may promote at most one significant personality delta and only after eval review."
    else
        personality_line="Do not promote personality deltas. If personality calibration opportunities appear, write them as review-required candidates only."
    fi

    cat <<EOF
EVOLUTION RUN ID: ${RUN_ID}
Time: ${TS}
Loop mode: ${LOOP_MODE}
Research algorithm context: ${CURRENT_LOOP}

Read these first:
1. ${PROTOCOL_DOC}
2. ${WORKFLOW_DOC}
3. ${GOVERNANCE_CONFIG}
4. ${EVAL_CASES}

Run exactly one bounded self-evolution cycle.

Non-negotiable rules:
- Treat capability growth and personality calibration as different candidate classes.
- Governance surfaces are read-only unless explicitly escalated for operator review.
- No infinite iteration.
- No hidden tool expansion.
- No silent permission change.
- No direct governance mutation.
- No stable-memory write for ambiguous intelligence.
- ${personality_line}

Your task:
1. Inspect current local signals first.
2. Classify every candidate into one of:
   - skill_refinement
   - tool_usage_refinement
   - workflow_improvement
   - orchestration_pattern_update
   - memory_policy_refinement
   - tone_calibration
   - boundary_tightening
   - proactivity_adjustment
   - refusal_behavior_adjustment
   - autonomy_behavior_adjustment
   - governance_affecting_candidate
   - mixed_ambiguous_candidate
3. Separate candidates by loop:
   - capability
   - personality
   - mixed
   - governance
4. Promote only candidates allowed by the governance config.
5. If a candidate touches governance, classify it, write the review payload, and stop short of promotion.
6. If a candidate is ambiguous, freeze promotion and escalate it as mixed_ambiguous_candidate.
7. Use eval cases before any proposed personality promotion.
8. Produce a report with:
   - signals
   - candidates
   - promotion decisions
   - review-required items
   - rollback paths
   - drift risks
   - next cycle focus

Special constraint for this run:
- The research loop '${CURRENT_LOOP}' is advisory context only. It does not authorize unbounded iteration or direct mutation.
- After one cycle, stop and report.
EOF
}

resolve_command_id() {
    case "$LOOP_MODE" in
        personality) COMMAND_ID="zera:evolve-personality" ;;
        capability|dual) COMMAND_ID="zera:evolve-capability" ;;
        *)
            echo "Unsupported loop mode: $LOOP_MODE" >&2
            exit 2
            ;;
    esac
}

resolve_branch_type() {
    case "$LOOP_MODE" in
        personality) BRANCH_TYPE="persona_sensitivity_branch" ;;
        capability) BRANCH_TYPE="research_branch" ;;
        dual) BRANCH_TYPE="strategy_branch" ;;
        *)
            echo "Unsupported loop mode: $LOOP_MODE" >&2
            exit 2
            ;;
    esac
}

main() {
    parse_args "$@"
    require_files
    check_freeze
    mkdir -p "$REPORT_DIR"
    mkdir -p "$BRANCH_DIR"
    pick_loop
    resolve_command_id
    resolve_branch_type

    local prompt
    prompt="$(build_prompt)"
    local prompt_path="$REPORT_DIR/evolution-prompt-${RUN_ID}.txt"
    printf "%s\n" "$prompt" > "$prompt_path"

    local branch_manifest_path="$BRANCH_DIR/branch-${RUN_ID}.json"
    bash "$COMMAND_BRIDGE" branch-manifest \
        --client repo_native \
        --command "$COMMAND_ID" \
        --branch-type "$BRANCH_TYPE" \
        --run-id "$RUN_ID" \
        --objective-file "$prompt_path" \
        --output "$branch_manifest_path" >/dev/null

    local rendered_prompt
    rendered_prompt="$(bash "$COMMAND_BRIDGE" render \
        --client repo_native \
        --command "$COMMAND_ID" \
        --objective-file "$prompt_path" \
        --branch-manifest-path "$branch_manifest_path")"

    echo "Run ID      : $RUN_ID"
    echo "Command ID  : $COMMAND_ID"
    echo "Loop mode   : $LOOP_MODE"
    echo "Branch type : $BRANCH_TYPE"
    echo "Current loop: $CURRENT_LOOP"
    echo "Next loop   : $NEXT_LOOP"
    echo "Prompt file : $prompt_path"
    echo "Branch file : $branch_manifest_path"

    if [ "$DRY_RUN" = true ] || [ "$PROMPT_ONLY" = true ]; then
        echo ""
        printf "%s\n" "$rendered_prompt"
        exit 0
    fi

    zera chat -q "$rendered_prompt"
}

main "$@"
