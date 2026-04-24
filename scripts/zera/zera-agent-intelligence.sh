#!/bin/bash
# ============================================
# Zera Agent Intelligence Intake
# Indexes external agent intelligence into reviewable artifacts.
# Direct persona-memory promotion is opt-in and never default.
# ============================================

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [[ ! -d "$DEFAULT_ROOT/configs" ]]; then
  DEFAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi
REPO_ROOT="${ZERA_REPO_ROOT:-$DEFAULT_ROOT}"
VAULT="${VAULT_PATH:-$HOME/antigravity-vault}"
INTEL_DIR="$VAULT/intelligence"
RESEARCH_DIR="$VAULT/research"
DISCUSSION_DIR="$RESEARCH_DIR/discussions"
LOG_DIR="$RESEARCH_DIR/logs"
REPORT_DIR="$RESEARCH_DIR/reports"
FREEZE_FILE="$RESEARCH_DIR/_control/freeze-state.json"
GOVERNANCE_CONFIG="$REPO_ROOT/configs/tooling/zera_growth_governance.json"
RESEARCH_REGISTRY="$REPO_ROOT/configs/tooling/zera_research_registry.yaml"
FOUNDRY_REGISTRY="$REPO_ROOT/configs/tooling/zera_skill_foundry.yaml"
EXTERNAL_IMPORTS="$REPO_ROOT/configs/tooling/zera_external_imports.yaml"
COMMAND_BRIDGE="$REPO_ROOT/scripts/zera-command.sh"
SOURCE_CARD_DIR="$RESEARCH_DIR/source-cards"
CANDIDATE_DIR="$RESEARCH_DIR/candidates"

PROMOTE_MEMORY=false
DRY_RUN=false
PROJECT_LIMIT=50
RUN_ID="$(date +"%Y%m%dT%H%M%S")-$$"
TODAY="$(date +"%Y-%m-%d")"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

log()   { echo -e "${CYAN}[INTEL]${NC}     $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}        $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}      $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}      $1"; }
title() { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }

usage() {
    cat <<'EOF'
Usage: bash scripts/zera-agent-intelligence.sh [--dry-run] [--promote-memory] [--project-limit N]

Indexes agent-system intelligence into reviewable artifacts.
Stable persona-memory promotion is disabled by default.
EOF
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                ;;
            --promote-memory)
                PROMOTE_MEMORY=true
                ;;
            --project-limit)
                shift
                PROJECT_LIMIT="${1:-50}"
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
}

event_log() {
    local event_type="$1"
    local decision="$2"
    local message="$3"
    python3 - "$LOG_DIR/evolution-events.jsonl" "$RUN_ID" "$TS" "$event_type" "$decision" "$message" <<'PY'
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
    "candidate_class": "research_target",
    "loop": "capability",
    "target_layer": "intelligence_intake",
    "risk_level": "medium",
    "governance_impact": "none",
    "decision": sys.argv[5],
    "eval_suite": [
        "source_provenance",
        "curation_required"
    ],
    "rollback_path": "delete or archive generated intelligence note",
    "source": "scripts/zera-agent-intelligence.sh",
    "command_id": "zera:foundry-ingest",
    "client_id": "repo_native",
    "branch_id": None,
    "branch_type": None,
    "import_lane": None,
    "source_license": None,
    "trust_score": None,
    "message": sys.argv[6],
}
with path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
PY
}

require_files() {
    if [ ! -f "$GOVERNANCE_CONFIG" ]; then
        fail "Missing governance config: $GOVERNANCE_CONFIG"
        exit 2
    fi
    for path in "$RESEARCH_REGISTRY" "$FOUNDRY_REGISTRY" "$EXTERNAL_IMPORTS" "$COMMAND_BRIDGE"; do
        if [ ! -f "$path" ]; then
            fail "Missing required file: $path"
            exit 2
        fi
    done
    if [ ! -f "$FREEZE_FILE" ]; then
        fail "Missing freeze-state file. Run scripts/zera-self-evolution.sh first."
        exit 2
    fi
}

check_freeze() {
    local freeze_exit=0
    python3 - "$FREEZE_FILE" <<'PY' || freeze_exit=$?
import json
import sys
from pathlib import Path

try:
    state = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (json.JSONDecodeError, OSError) as exc:
    print(f"ERROR: corrupted or unreadable freeze-state file: {exc}", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(0 if state.get("state") == "frozen" else 1)
PY
    if [ "$freeze_exit" -eq 0 ]; then
        fail "Evolution is frozen. Intelligence intake is paused until operator review."
        event_log "intelligence_intake_blocked" "blocked" "freeze-state active"
        exit 3
    elif [ "$freeze_exit" -eq 2 ]; then
        fail "Freeze-state file is corrupted. Treating as frozen for safety."
        event_log "intelligence_intake_blocked" "blocked" "freeze-state corrupted"
        exit 3
    fi
}

ensure_dirs() {
    mkdir -p \
        "$INTEL_DIR"/{agents,projects,patterns,skills,swarm,roles} \
        "$DISCUSSION_DIR" \
        "$REPORT_DIR" \
        "$SOURCE_CARD_DIR" \
        "$CANDIDATE_DIR"
}

phase_stage_external_sources() {
    title "Phase 0: Stage External Source Cards"
    local sources=(
        "source-superclaude:SuperClaude_Framework:command_taxonomy,workflow_shells,mode_decomposition"
        "source-claude-code-open:claude-code-open:provider_bridge,routing_helpers,multi_model_transport"
        "source-claurst:claurst:branching_mechanics,memory_consolidation,provider_multiplexing"
        "source-open-claude-code:open-claude-code:workflow_oracle,ux_reference"
        "source-awesome-claude-code:awesome-claude-code:ecosystem_index,tool_discovery"
    )
    local source
    for source in "${sources[@]}"; do
        IFS=":" read -r source_id source_name components <<<"$source"
        bash "$COMMAND_BRIDGE" source-card \
            --source-id "$source_id" \
            --source-name "$source_name" \
            --components "$components" \
            --output "$SOURCE_CARD_DIR/${source_id}.json" >/dev/null
        ok "Source card created: $source_name"
    done
}

phase_index_repos() {
    title "Phase 1: Index Agent Repositories"

    if [ -d "$HOME/NanoClaw/nanoclaw" ]; then
        cat > "$INTEL_DIR/agents/nanoclaw.md" <<EOF
---
created: ${TODAY}
source: ~/NanoClaw/nanoclaw
type: agent-system
status: observed_unpromoted
candidate_class: research_target
promotion_gate: discussion_first
tags: [agent, nanoclaw, observed]
---

# NanoClaw — Observed Agent System

This note is indexed intelligence, not stable persona memory.

## Why it matters
- useful for capability growth
- may generate skill or workflow candidates
- must not silently mutate governance or persona
EOF
        ok "NanoClaw indexed as observed intelligence"
    else
        warn "NanoClaw repo not found; skipping"
    fi

    local proj_count=0
    for proj_dir in "$HOME"/projects/*/; do
        [ "$proj_count" -ge "$PROJECT_LIMIT" ] && break
        local proj_name
        proj_name="$(basename "$proj_dir")"

        if [ -f "$proj_dir/.agents/config.yaml" ] || [ -f "$proj_dir/.claude/settings.local.json" ] || \
           [ -f "$proj_dir/CLAUDE.md" ] || [ -f "$proj_dir/AGENTS.md" ] || [ -f "$proj_dir/QWEN.md" ]; then
            cat > "$INTEL_DIR/projects/${proj_name}.md" <<EOF
---
created: ${TODAY}
source: ${proj_dir}
type: project-config
status: observed_unpromoted
candidate_class: research_target
promotion_gate: discussion_first
tags: [project, agent-config, ${proj_name}]
---

# Project: ${proj_name}

## Agent Configs Found
EOF

            find "$proj_dir" -maxdepth 3 \( -name "CLAUDE.md" -o -name "AGENTS.md" -o -name "QWEN.md" -o -name "*.agent" -o -name "settings*.json" -o -name "*.yaml" -o -name "PROJECT_SUMMARY.md" \) 2>/dev/null \
                | grep -v node_modules | grep -v ".next" | grep -v ".git" \
                | while read -r cfg; do
                    local rel_path="${cfg#$proj_dir/}"
                    local lines
                    lines="$(wc -l < "$cfg" 2>/dev/null || echo "?")"
                    echo "- \`${rel_path}\` (${lines} lines)" >> "$INTEL_DIR/projects/${proj_name}.md"
                done
            ((proj_count+=1))
        fi
    done
    ok "${proj_count} projects indexed as observed intelligence"
}

phase_extract_patterns() {
    title "Phase 2: Extract Patterns"

    cat > "$INTEL_DIR/roles/unified-role-registry.md" <<EOF
---
created: ${TODAY}
source: multi-agent-scan
type: role-registry
status: observed_unpromoted
candidate_class: orchestration_pattern_update
promotion_gate: review_required
tags: [roles, agents, patterns]
---

# Unified Agent Role Registry

This registry is a reviewable pattern source.
It is not an auto-promoted runtime contract.
EOF

    cat > "$INTEL_DIR/swarm/swarm-patterns.md" <<EOF
---
created: ${TODAY}
source: multi-agent-scan
type: swarm-patterns
status: observed_unpromoted
candidate_class: orchestration_pattern_update
promotion_gate: review_required
tags: [swarm, orchestration, patterns]
---

# Swarm Patterns — Observed Candidates

- model tier routing
- container isolation
- channel self-registration
- free-first with local fallback
- group-based memory
- scheduled tasks

Each item requires separate classification before promotion.
EOF

    cat > "$INTEL_DIR/skills/discovered-skills.md" <<EOF
---
created: ${TODAY}
source: multi-agent-scan
type: skill-discovery
status: observed_unpromoted
candidate_class: skill_refinement
promotion_gate: review_required
tags: [skills, discovery, patterns]
---

# Discovered Skills — Review Queue

These findings may inform future \`skill_refinement\` candidates.
They are not stable memory and not active skills by default.
EOF

    ok "Pattern registry refreshed"
}

phase_stage_review() {
    title "Phase 3: Stage Review Payload"

    local review_path="$DISCUSSION_DIR/agent-intelligence-review-${RUN_ID}.md"
    cat > "$review_path" <<EOF
# Agent Intelligence Review Payload — ${RUN_ID}

## Classification
- intake_type: observed intelligence
- default_candidate_class: research_target
- promotion_gate: discussion_first
- stable_memory_write: ${PROMOTE_MEMORY}

## What was indexed
- agent systems
- project configs
- role patterns
- swarm patterns
- discovered skills

## Required next step
For each useful pattern, create a separately classified candidate in:
\`${RESEARCH_DIR}/candidates/\`

Do not promote directly into governance or persona without review.
EOF
    ok "Review payload created: $review_path"

    cat > "$CANDIDATE_DIR/foundry-intake-${RUN_ID}.json" <<EOF
{
  "candidate_id": "foundry-intake-${RUN_ID}",
  "candidate_type": "research_heuristic",
  "lane_owner": "zera-researcher",
  "overlap_result": "extend_existing",
  "provenance": "external",
  "import_lane": "discovery_index_only",
  "eval_suite": ["source_provenance", "non_overlap", "rollback_path"],
  "reversibility": "easy",
  "promotion_gate": "review_required",
  "quarantine_status": "review",
  "notes": "External source cards were staged for foundry review before any runtime promotion."
}
EOF
    ok "Foundry intake candidate created: $CANDIDATE_DIR/foundry-intake-${RUN_ID}.json"

    if [ "$PROMOTE_MEMORY" = true ]; then
        local memory_path="$VAULT/memory/zera/agent-intelligence.md"
        cat > "$memory_path" <<EOF
---
created: ${TODAY}
updated: ${TODAY}
source: curated_summary
type: intelligence-memory
promotion_gate: operator_requested
tags: [intelligence, agents, curated]
---

# Zera Agent Intelligence

This file was written only because \`--promote-memory\` was explicitly requested.

## Summary
- external agent patterns were indexed into \`${INTEL_DIR}\`
- promotion into stable memory remains manual and curated
- future candidates must keep governance and personality surfaces gated
EOF
        ok "Curated memory promotion written: $memory_path"
        event_log "intelligence_memory_promoted" "reviewed" "operator requested stable memory promotion"
    else
        warn "Stable persona-memory promotion skipped by default"
        event_log "intelligence_indexed" "staged_for_review" "observed intelligence staged without memory promotion"
    fi
}

phase_report() {
    title "Phase 4: Report"
    local report="$REPORT_DIR/agent-intelligence-${RUN_ID}.md"
    cat > "$report" <<EOF
# Zera Agent Intelligence Intake — ${RUN_ID}

## Runtime Policy
- direct persona-memory promotion disabled by default
- observed intelligence is staged for review
- governance and persona promotion remain gated

## Artifacts
- \`${SOURCE_CARD_DIR}/\`
- \`${INTEL_DIR}/agents/\`
- \`${INTEL_DIR}/projects/\`
- \`${INTEL_DIR}/roles/\`
- \`${INTEL_DIR}/swarm/\`
- \`${INTEL_DIR}/skills/\`
- \`${DISCUSSION_DIR}/agent-intelligence-review-${RUN_ID}.md\`

## Next Step
Convert worthwhile findings into explicitly classified candidates before any promotion.
EOF
    ok "Intelligence report created: $report"
}

main() {
    parse_args "$@"
    require_files
    check_freeze
    ensure_dirs

    if [ "$DRY_RUN" = true ]; then
        warn "Dry run enabled: only local artifact generation will occur"
    fi

    phase_stage_external_sources
    phase_index_repos
    phase_extract_patterns
    phase_stage_review
    phase_report

    echo ""
    ok "Agent intelligence intake completed"
    echo "Stable memory promotion: $PROMOTE_MEMORY"
    echo "Review queue           : $DISCUSSION_DIR"
}

main "$@"
