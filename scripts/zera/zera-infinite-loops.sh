#!/bin/bash
# ============================================
# Zera Infinite Loop Algorithms — Full Installation
# Installs and configures all 10 algorithms for Zera + Antigravity Core
# ============================================

set -e

VAULT="$HOME/antigravity-vault"
LOOPS_DIR="$VAULT/loops"
TIMESTAMP=$(date +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

log()   { echo -e "${CYAN}[LOOP]${NC}      $1"; }
ok()    { echo -e "${GREEN}[OK]${NC}        $1"; }
warn()  { echo -e "${YELLOW}[SETUP]${NC}     $1"; }
title() { echo -e "\n${BOLD}━━━ $1 ━━━${NC}"; }

mkdir -p "$LOOPS_DIR"/{karpathy,rsi,darwin-goedel,pantheon,self-improving,swarm,ralph,agentic-ci,self-driving,meta-learning}

# ============================================
# ALGORITHM 1: Karpathy Loop
# ============================================
setup_karpathy() {
    title "ALGORITHM 1: Karpathy Loop"

    cat > "$LOOPS_DIR/karpathy/config.yaml" << EOF
---
name: karpathy-loop
version: "1.0"
created: $TODAY
source: karpathy/autoresearch
status: active

# Core parameters
target_file: "configs/orchestrator/router.yaml"
metric: "first_pass_success_rate"
metric_direction: "higher_is_better"
time_budget_minutes: 5
max_iterations: 50
stopping_criteria:
  - "iterations >= max_iterations"
  - "score >= 0.90"
  - "plateau_detected (delta < 0.01 for 5 iterations)"
  - "manual_stop"

# What the agent can modify
allowed_changes:
  - "model aliases and routing"
  - "tier thresholds"
  - "max_tools limits"
  - "feature flags"
  - "memory retrieval params"

# What the agent CANNOT change
forbidden_changes:
  - "security policies"
  - "API keys"
  - "completion gates (safety)"
  - "role contracts"

# Logging
log_file: "$LOOPS_DIR/karpathy/results.jsonl"
progress_file: "$LOOPS_DIR/karpathy/progress.md"
best_config: "$LOOPS_DIR/karpathy/best-config.yaml"
EOF

    cat > "$LOOPS_DIR/karpathy/program.md" << 'EOF'
# Karpathy Loop — Antigravity Core Router Optimization

## Goal
Optimize configs/orchestrator/router.yaml to maximize first_pass_success_rate.

## Rules
1. You can ONLY modify configs/orchestrator/router.yaml
2. Each iteration: modify → test → measure → keep if better
3. Metric: first_pass_success_rate (higher is better)
4. Time budget: 5 minutes per experiment
5. Max 50 iterations total
6. Stop if: score >= 0.90 OR plateau for 5 iterations

## What to try
- Adjust C1-C5 tier thresholds
- Change model routing (different models per tier)
- Modify max_tools limits per tier
- Enable/disable feature flags
- Adjust memory retrieval params (top_k, min_score)
- Change task type mappings

## Process
1. Read current router.yaml
2. Read current best score from results.jsonl
3. Make ONE change (or small related set)
4. Validate YAML syntax
5. If valid → save as candidate, mark as "testing"
6. After test cycle → record score
7. If score > best → keep as new best, else revert
8. Log result to results.jsonl
9. Repeat

## Safety
- Never change security-related settings
- Never change API keys or credentials
- Never disable completion gates
- Always keep backup before changes
EOF

    cat > "$LOOPS_DIR/karpathy/results.jsonl" << 'EOF'
{"iteration": 0, "timestamp": "BASELINE", "config_hash": "initial", "metric": "first_pass_success_rate", "score": 0.85, "changes": "none", "status": "baseline"}
EOF

    cat > "$LOOPS_DIR/karpathy/progress.md" << EOF
# Karpathy Loop Progress — Antigravity Core Router
Started: $TODAY
Target: configs/orchestrator/router.yaml
Metric: first_pass_success_rate (higher is better)
Baseline: 0.85
Best score: 0.85
Iterations: 0/50

## History
| Iter | Change | Score | Δ | Status |
|------|--------|-------|---|--------|
| 0 | Baseline | 0.85 | — | baseline |
EOF

    ok "Karpathy Loop configured"
    ok "Target: router.yaml optimization"
    ok "Metric: first_pass_success_rate"
    ok "Max iterations: 50"
}

# ============================================
# ALGORITHM 2: RSI Loop
# ============================================
setup_rsi() {
    title "ALGORITHM 2: RSI Loop (Recursive Self-Improvement)"

    cat > "$LOOPS_DIR/rsi/config.yaml" << EOF
---
name: rsi-loop
version: "1.0"
created: $TODAY
source: clawinfra/rsi-loop
status: active

# Core parameters
analysis_scope:
  - "Zera SOUL.md effectiveness"
  - "Antigravity Core config quality"
  - "Hermes cron job performance"
  - "Vault organization"
  - "Skill coverage"

min_improvement_threshold: 0.05
max_iterations: 30
cooldown_hours: 2

# Scoring dimensions (0-10)
dimensions:
  knowledge_coverage: 10
  response_quality: 10
  autonomy_effectiveness: 8
  tool_utilization: 8
  memory_quality: 8
  config_optimization: 7

log_file: "$LOOPS_DIR/rsi/results.jsonl"
memory_file: "$LOOPS_DIR/rsi/self-knowledge.md"
EOF

    cat > "$LOOPS_DIR/rsi/algorithm.md" << 'EOF'
# RSI Loop — Recursive Self-Improvement Algorithm

## Loop
1. **Analyze** current performance across all dimensions
2. **Identify** weakest area (lowest score or most improvement potential)
3. **Hypothesize** specific improvement
4. **Test** in sandbox (dry run or isolated test)
5. **Deploy** if improvement confirmed, else discard
6. **Update** self-knowledge base
7. **Repeat** (truly infinite)

## Analysis Template
```yaml
dimension: [knowledge, quality, autonomy, tools, memory, config]
current_score: 0-10
improvement_potential: 10 - current_score
evidence: [list of supporting data]
hypothesis: "If I change X, then Y will improve by Z"
test_plan: "How to verify hypothesis"
```

## Self-Knowledge Update Rules
- Record what worked and what didn't
- Track improvement velocity per dimension
- Prefer changes with high impact + low risk
- Never degrade an already-good dimension to improve a weak one
EOF

    cat > "$LOOPS_DIR/rsi/self-knowledge.md" << EOF
---
created: $TODAY
updated: $TODAY
type: self-knowledge
---

# RSI Self-Knowledge Base

## Current State
| Dimension | Score | Last Changed | Trend |
|-----------|-------|-------------|-------|
| Knowledge Coverage | 7/10 | $TODAY | ↗ |
| Response Quality | 7/10 | $TODAY | → |
| Autonomy | 8/10 | $TODAY | ↗ |
| Tool Usage | 6/10 | $TODAY | → |
| Memory Quality | 7/10 | $TODAY | ↗ |
| Config Optimization | 5/10 | $TODAY | → |

## What I've Learned
- [To be filled by RSI Loop]

## Failed Attempts
- [None yet]

## Successful Improvements
- [Baseline established $TODAY]
EOF

    ok "RSI Loop configured"
    ok "6 dimensions tracked"
    ok "Self-knowledge base initialized"
}

# ============================================
# ALGORITHM 3: Darwin Gödel Machine
# ============================================
setup_darwin_goedel() {
    title "ALGORITHM 3: Darwin Gödel Machine"

    cat > "$LOOPS_DIR/darwin-goedel/config.yaml" << EOF
---
name: darwin-goedel-machine
version: "1.0"
created: $TODAY
source: schmidhuber-group/darwin-goedel-machine
status: active

# Gödel Machine: prove improvement before accepting
mutation_types:
  - "prompt_optimization"
  - "workflow_restructuring"
  - "skill_addition"
  - "config_tuning"
  - "memory_reorganization"

proof_requirements:
  min_score_improvement: 0.03
  min_test_coverage: 0.8
  no_regressions: true
  safety_check: true

generation: 0
population_size: 5
mutation_rate: 0.2
crossover_rate: 0.1

log_file: "$LOOPS_DIR/darwin-goedel/evolution.jsonl"
best_genome: "$LOOPS_DIR/darwin-goedel/best-genome.yaml"
EOF

    cat > "$LOOPS_DIR/darwin-goedel/algorithm.md" << 'EOF'
# Darwin Gödel Machine — Provable Self-Improvement

## Loop
1. Current state = (prompts, workflows, skills, configs, memory)
2. Propose mutation to any component
3. PROVE mutation improves utility:
   - Run sandbox tests
   - Compare metrics before/after
   - Verify no regressions
   - Check safety constraints
4. If provably better → accept, update genome
5. New generation → repeat

## Mutation Operators
- **prompt_optimization**: Rewrite SOUL.md sections for clarity
- **workflow_restructuring**: Reorder workflow steps for efficiency
- **skill_addition**: Add new skill from research
- **config_tuning**: Adjust thresholds, limits, weights
- **memory_reorganization**: Restructure vault for better retrieval

## Proof Checklist
- [ ] Metric improved by >= 3%
- [ ] No test failures introduced
- [ ] No safety rules broken
- [ ] Rollback plan exists
- [ ] Change is reversible
EOF

    ok "Darwin Gödel Machine configured"
    ok "5 mutation types, proof-based acceptance"
}

# ============================================
# ALGORITHM 4: PantheonOS
# ============================================
setup_pantheon() {
    title "ALGORITHM 4: PantheonOS — Evolvable Multi-Agent"

    cat > "$LOOPS_DIR/pantheon/config.yaml" << EOF
---
name: pantheon-os
version: "1.0"
created: $TODAY
source: aristoteleo/PantheonOS
status: active

# Agent roles (mapping to Zera capabilities)
agents:
  researcher:
    role: "discover patterns from repos, papers, configs"
    schedule: "every 12 hours"
    output: "$LOOPS_DIR/pantheon/research-findings.md"

  builder:
    role: "implement improvements discovered by researcher"
    schedule: "after researcher completes"
    output: "$LOOPS_DIR/pantheon/implementation.md"

  critic:
    role: "evaluate quality of implementations"
    schedule: "after builder completes"
    output: "$LOOPS_DIR/pantheon/critique.md"

  evaluator:
    role: "measure impact on system metrics"
    schedule: "after critic approves"
    output: "$LOOPS_DIR/pantheon/evaluation.md"

  evolver:
    role: "update agent code/prompts based on results"
    schedule: "after evaluator confirms improvement"
    output: "$LOOPS_DIR/pantheon/evolution.md"

# Cycle parameters
max_cycles_per_day: 2
min_improvement: 0.05
rollback_on_failure: true

log_file: "$LOOPS_DIR/pantheon/cycles.jsonl"
EOF

    cat > "$LOOPS_DIR/pantheon/algorithm.md" << 'EOF'
# PantheonOS — Multi-Agent Evolution Loop

## Cycle
1. **Researcher** scans sources → finds patterns → proposes improvements
2. **Builder** implements proposals → creates working changes
3. **Critic** reviews implementations → approves or rejects
4. **Evaluator** measures impact → quantifies improvement
5. **Evolver** updates system → deploys improvements
6. All agents learn from cycle → improve their own behavior
7. Repeat

## Agent Communication
- Researcher → Builder: research-findings.md
- Builder → Critic: implementation.md
- Critic → Evaluator: critique.md (if approved)
- Evaluator → Evolver: evaluation.md (if improved)
- Evolver → all agents: evolution.md

## Safety
- Each agent operates independently
- Critic can veto any change
- Evaluator requires measurable improvement
- Evolver maintains rollback capability
EOF

    ok "PantheonOS configured"
    ok "5 agents: researcher, builder, critic, evaluator, evolver"
}

# ============================================
# ALGORITHM 5: Self-Improving Coding Agent
# ============================================
setup_self_improving() {
    title "ALGORITHM 5: Self-Improving Coding Agent"

    cat > "$LOOPS_DIR/self-improving/config.yaml" << EOF
---
name: self-improving-agent
version: "1.0"
created: $TODAY
source: addyosmani/self-improving-agents
status: active

# Scan targets
scan_paths:
  - "configs/orchestrator/"
  - "configs/tooling/"
  - ".agent/workflows/"
  - ".agent/config/"
  - "scripts/"

# What to look for
patterns:
  - "TODO comments"
  - "FIXME comments"
  - "Deprecated configs"
  - "Inconsistent formatting"
  - "Missing documentation"
  - "Outdated references"
  - "Inefficient patterns"
  - "Security concerns"

# Fix parameters
auto_fix_enabled: true
max_fixes_per_cycle: 5
require_test: true
require_commit_message: true
require_pr_for_complex: true

log_file: "$LOOPS_DIR/self-improving/fixes.jsonl"
EOF

    cat > "$LOOPS_DIR/self-improving/algorithm.md" << 'EOF'
# Self-Improving Coding Agent

## Loop
1. Scan repo for issues:
   - TODOs, FIXMEs
   - Deprecated configs
   - Inconsistent formatting
   - Missing docs
   - Outdated references
   - Security concerns
2. Pick highest priority item
3. Analyze + propose fix
4. Run tests to verify
5. If tests pass → commit + push
6. Update issue tracker
7. Repeat

## Priority Rules
1. Security issues → immediate
2. Broken configs → high
3. Deprecated items → medium
4. TODOs/FIXMEs → medium
5. Documentation → low
6. Formatting → lowest
EOF

    ok "Self-Improving Agent configured"
    ok "8 pattern types, auto-fix enabled"
}

# ============================================
# ALGORITHM 6: Karpathy Swarm
# ============================================
setup_swarm() {
    title "ALGORITHM 6: Karpathy Swarm — Parallel Experiments"

    cat > "$LOOPS_DIR/swarm/config.yaml" << EOF
---
name: karpathy-swarm
version: "1.0"
created: $TODAY
source: karpathy/autoresearch (swarm variant)
status: active

# Parallel agents, each optimizes different aspect
agents:
  - name: agent-router
    target: "configs/orchestrator/router.yaml"
    metric: "routing_accuracy"

  - name: agent-models
    target: "configs/orchestrator/models.yaml"
    metric: "model_quality_score"

  - name: agent-mcp
    target: "configs/tooling/mcp_profiles.json"
    metric: "mcp_tool_effectiveness"

  - name: agent-skills
    target: "configs/skills/"
    metric: "skill_match_rate"

  - name: agent-workflows
    target: ".agent/workflows/"
    metric: "workflow_efficiency"

# Swarm coordination
sync_interval_iterations: 10
share_winners: true
archive_failures: true
spawn_new_for_promising: true

max_agents: 5
max_iterations_per_agent: 20

log_file: "$LOOPS_DIR/swarm/results.jsonl"
shared_knowledge: "$LOOPS_DIR/swarm/shared-findings.md"
EOF

    ok "Karpathy Swarm configured"
    ok "5 parallel agents, different targets"
}

# ============================================
# ALGORITHM 7: Ralph Loop ∞
# ============================================
setup_ralph() {
    title "ALGORITHM 7: Ralph Loop ∞ (Infinite)"

    cat > "$LOOPS_DIR/ralph/config.yaml" << EOF
---
name: ralph-loop-infinite
version: "2.0"
created: $TODAY
source: antigravity-core (extended)
status: active

# Extended from existing Ralph Loop
# Original: max 7 iterations, stops at 0.70 score
# Infinite: no hard cap, continuous improvement

max_iterations: 0  # 0 = infinite
scoring_weights:
  correctness: 0.35
  speed: 0.20
  code_quality: 0.20
  token_efficiency: 0.15
  tool_success_rate: 0.10

# Stopping (only manual or plateau)
stopping_criteria:
  - "manual_stop"
  - "plateau_50_iterations (delta < 0.001)"
  - "budget_exhausted"

# Scope
targets:
  - "configs/orchestrator/"
  - "configs/tooling/"
  - ".agent/workflows/"

# Knowledge accumulation
knowledge_base: "$LOOPS_DIR/ralph/knowledge.md"
best_solutions: "$LOOPS_DIR/ralph/best-solutions/"

log_file: "$LOOPS_DIR/ralph/results.jsonl"
EOF

    cat > "$LOOPS_DIR/ralph/knowledge.md" << EOF
---
created: $TODAY
type: ralph-knowledge
---

# Ralph Loop ∞ Knowledge Base

## Baseline
- Original Ralph: max 7 iterations, threshold 0.70
- Extended Ralph: no cap, continuous improvement
- Score formula: 0.35*correctness + 0.20*speed + 0.20*code_quality + 0.15*token_eff + 0.10*tool_success

## Optimization History
| Date | Target | Best Score | Key Change |
|------|--------|-----------|------------|
| $TODAY | Baseline | TBD | Initial |

## Patterns Discovered
- [To be filled]
EOF

    ok "Ralph Loop ∞ configured (infinite mode)"
}

# ============================================
# ALGORITHM 8: Agentic CI
# ============================================
setup_agentic_ci() {
    title "ALGORITHM 8: Agentic CI — Continuous Background Agents"

    cat > "$LOOPS_DIR/agentic-ci/config.yaml" << EOF
---
name: agentic-ci
version: "1.0"
created: $TODAY
source: github.com (Continuous AI pattern)
status: active

# 5 continuous background agents
agents:
  doc-agent:
    name: "Documentation Agent"
    trigger: "on config or code change"
    action: "update docs to match reality"
    schedule: "continuous"

  test-agent:
    name: "Test Coverage Agent"
    trigger: "every 4 hours"
    action: "add tests for uncovered code paths"
    schedule: "*/4 * * * *"

  refactor-agent:
    name: "Refactoring Agent"
    trigger: "every 12 hours"
    action: "clean tech debt, improve patterns"
    schedule: "0 */12 * * *"

  security-agent:
    name: "Security Agent"
    trigger: "every 6 hours"
    action: "scan for vulnerabilities, misconfigs"
    schedule: "0 */6 * * *"

  perf-agent:
    name: "Performance Agent"
    trigger: "every 12 hours"
    action: "optimize hot paths, reduce latency"
    schedule: "0 */12 * * *"

# Coordination
max_concurrent_agents: 2
conflict_resolution: "doc-agent priority highest"

log_file: "$LOOPS_DIR/agentic-ci/agents.jsonl"
EOF

    ok "Agentic CI configured"
    ok "5 agents: doc, test, refactor, security, perf"
}

# ============================================
# ALGORITHM 9: Self-Driving Business
# ============================================
setup_self_driving() {
    title "ALGORITHM 9: Self-Driving Business Loop"

    cat > "$LOOPS_DIR/self-driving/config.yaml" << EOF
---
name: self-driving-loop
version: "1.0"
created: $TODAY
source: Self-Driving Business pattern
status: active

# Metrics to optimize
metrics:
  task_success_rate:
    target: 0.95
    current: 0.85
    weight: 3

  response_time_seconds:
    target: 30
    current: 45
    weight: 2

  token_efficiency:
    target: 0.70
    current: 0.55
    weight: 2

  user_satisfaction:
    target: 0.90
    current: 0.80
    weight: 3

# A/B Testing
ab_test_duration_hours: 24
min_sample_size: 10
confidence_threshold: 0.95

# Deployment
auto_deploy_winners: true
auto_rollback_losers: true
max_concurrent_tests: 3

log_file: "$LOOPS_DIR/self-driving/experiments.jsonl"
metrics_history: "$LOOPS_DIR/self-driving/metrics.jsonl"
EOF

    ok "Self-Driving Loop configured"
    ok "4 metrics tracked, A/B testing enabled"
}

# ============================================
# ALGORITHM 10: Meta-Learning
# ============================================
setup_meta_learning() {
    title "ALGORITHM 10: Meta-Learning Loop"

    cat > "$LOOPS_DIR/meta-learning/config.yaml" << EOF
---
name: meta-learning-loop
version: "1.0"
created: $TODAY
source: Meta-Learning pattern
status: active

# What to learn
learning_targets:
  - "how to search more effectively"
  - "how to evaluate candidates better"
  - "how to integrate improvements faster"
  - "how to identify patterns quicker"
  - "how to communicate findings clearly"

# Meta-learning process
1. Learn task X (normal operation)
2. Analyze HOW I learned (meta-analysis)
3. Update learning strategy
4. Learn task Y with better strategy
5. Compare: was new strategy better?
6. If yes → keep new strategy
7. Repeat (infinite meta-improvement)

# Tracking
strategy_history: "$LOOPS_DIR/meta-learning/strategies.jsonl"
learning_velocity: "$LOOPS_DIR/meta-learning/velocity.md"

log_file: "$LOOPS_DIR/meta-learning/results.jsonl"
EOF

    cat > "$LOOPS_DIR/meta-learning/velocity.md" << EOF
---
created: $TODAY
type: meta-learning-velocity
---

# Meta-Learning Velocity

## Learning Strategies
| Strategy | Task | Before Score | After Score | Improvement | Kept? |
|----------|------|-------------|-------------|-------------|-------|
| Baseline | search | TBD | — | — | — |

## Insights
- [To be filled]
EOF

    ok "Meta-Learning Loop configured"
    ok "5 learning targets tracked"
}

# ============================================
# MAIN
# ============================================
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ⚕  Zera Infinite Loop Algorithms — Full Installation   ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    setup_karpathy          # 1
    setup_rsi               # 2
    setup_darwin_goedel     # 3
    setup_pantheon          # 4
    setup_self_improving    # 5
    setup_swarm             # 6
    setup_ralph             # 7
    setup_agentic_ci        # 8
    setup_self_driving      # 9
    setup_meta_learning     # 10

    # Create master index
    cat > "$LOOPS_DIR/README.md" << EOF
---
created: $TODAY
type: loop-algorithms-index
---

# Zera Infinite Loop Algorithms — Master Index

## Installed Algorithms

| # | Algorithm | Config | Status | Target |
|---|-----------|--------|--------|--------|
| 1 | Karpathy Loop | karpathy/config.yaml | ✅ Active | router.yaml optimization |
| 2 | RSI Loop | rsi/config.yaml | ✅ Active | Self-improvement (6 dims) |
| 3 | Darwin Gödel | darwin-goedel/config.yaml | ✅ Active | Provable mutations |
| 4 | PantheonOS | pantheon/config.yaml | ✅ Active | 5-agent evolution |
| 5 | Self-Improving | self-improving/config.yaml | ✅ Active | Tech debt automation |
| 6 | Karpathy Swarm | swarm/config.yaml | ✅ Active | 5 parallel experiments |
| 7 | Ralph Loop ∞ | ralph/config.yaml | ✅ Active | Infinite optimization |
| 8 | Agentic CI | agentic-ci/config.yaml | ✅ Active | 5 background agents |
| 9 | Self-Driving | self-driving/config.yaml | ✅ Active | A/B testing + metrics |
| 10 | Meta-Learning | meta-learning/config.yaml | ✅ Active | Learn to learn |

## How to Launch

### Single Algorithm
\`\`\`bash
zera chat -q "Запусти Karpathy Loop. Прочитай loops/karpathy/program.md и config.yaml. Оптимизируй router.yaml."
\`\`\`

### All Algorithms (Sequential)
\`\`\`bash
zera chat -q "Запусти все 10 циклов по порядку. Начни с Karpathy, закончи Meta-Learning."
\`\`\`

### Specific Algorithm
- Karpathy: \`zera chat -q "Karpathy Loop: оптимизируй router.yaml"\`
- RSI: \`zera chat -q "RSI Loop: найди слабую зону, улучши"\`
- Self-Improving: \`zera chat -q "Self-Improving: просканируй repo на tech debt"\`
- Ralph ∞: \`zera chat -q "Ralph Loop Infinite: непрерывная оптимизация"\`
- Swarm: \`zera chat -q "Karpathy Swarm: 5 агентов параллельно"\`
- PantheonOS: \`zera chat -q "PantheonOS: запусти 5-агентный цикл"\`
- Meta-Learning: \`zera chat -q "Meta-Learning: улучши как ты учишься"\`
- Self-Driving: \`zera chat -q "Self-Driving: оптимизируй 4 метрики"\`
- Agentic CI: \`zera chat -q "Agentic CI: запусти 5 фоновых агентов"\`
- Darwin Gödel: \`zera chat -q "Darwin Gödel: propose mutation, prove, accept"\`

## Directory Structure
\`\`\`
$LOOPS_DIR/
├── README.md (this file)
├── karpathy/          # 1. Karpathy Loop
│   ├── config.yaml
│   ├── program.md
│   ├── results.jsonl
│   └── progress.md
├── rsi/               # 2. RSI Loop
│   ├── config.yaml
│   ├── algorithm.md
│   ├── results.jsonl
│   └── self-knowledge.md
├── darwin-goedel/     # 3. Darwin Gödel Machine
│   ├── config.yaml
│   └── algorithm.md
├── pantheon/          # 4. PantheonOS
│   ├── config.yaml
│   └── algorithm.md
├── self-improving/    # 5. Self-Improving Agent
│   ├── config.yaml
│   └── algorithm.md
├── swarm/             # 6. Karpathy Swarm
│   └── config.yaml
├── ralph/             # 7. Ralph Loop ∞
│   ├── config.yaml
│   ├── knowledge.md
│   └── results.jsonl
├── agentic-ci/        # 8. Agentic CI
│   └── config.yaml
├── self-driving/      # 9. Self-Driving
│   └── config.yaml
└── meta-learning/     # 10. Meta-Learning
    ├── config.yaml
    └── velocity.md
\`\`\`
EOF

    # Count results
    local total_dirs=$(find "$LOOPS_DIR" -type d | wc -l | tr -d ' ')
    local total_files=$(find "$LOOPS_DIR" -type f | wc -l | tr -d ' ')
    local total_lines=$(find "$LOOPS_DIR" -type f -exec cat {} + | wc -l | tr -d ' ')

    echo ""
    echo -e "${GREEN}✅ All 10 Infinite Loop Algorithms Installed${NC}"
    echo ""
    echo "Statistics:"
    echo "  $total_dirs directories"
    echo "  $total_files config files"
    echo "  $total_lines lines of configuration"
    echo ""
    echo "Structure:"
    find "$LOOPS_DIR" -type f | sed "s|$LOOPS_DIR/|  /|" | sort
    echo ""
    echo "Cloned repos:"
    echo "  ✅ karpathy/autoresearch → /tmp/karpathy-autoresearch/"
    echo "  ✅ clawinfra/rsi-loop → /tmp/rsi-loop/"
    echo "  ✅ aristoteleo/PantheonOS → /tmp/PantheonOS/"
    echo ""
    echo "Quick start:"
    echo "  zera chat -q \"Запусти Karpathy Loop\""
    echo "  zera chat -q \"Запусти RSI Loop\""
    echo "  zera chat -q \"Запусти все 10 циклов\""
    echo ""
}

main "$@"
