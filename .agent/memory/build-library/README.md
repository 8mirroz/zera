# Build Memory Library Standard
Version: 2.0
Role: L1-L3 Shared Memory Subsystem for Build Intelligence, Reuse, and Deterministic Retrieval

## 1. PURPOSE

Build Memory Library is the shared memory subsystem for storing, ranking, and retrieving
the most effective builds, settings combinations, algorithms, workflows, execution playbooks,
and validated operating patterns used by Antigravity agents.

This library exists to transform isolated successful runs into reusable system intelligence.

It is not a general note archive.
It is a structured, evidence-backed memory layer for planners, orchestrators, evaluators,
and execution agents.

---

## 2. PRIMARY OBJECTIVES

- Reuse proven solutions across agents, sessions, and projects
- Separate cross-project best practices from project-specific optimizations
- Preserve evidence for every retained pattern
- Support deterministic querying, filtering, and ranking
- Promote validated builds into reusable gold standards
- Reduce repeated experimentation cost
- Increase first-pass success rate for future tasks
- Provide traceable memory inputs to planning and orchestration layers

---

## 3. SYSTEM ROLE IN THE ARCHITECTURE

Build Memory Library functions as:

- a reusable pattern repository
- a retrieval layer for agent planning
- a validation history for what actually worked
- a ranking engine for best known combinations
- a bridge between traces, audits, KI, benchmarks, and future execution

This subsystem sits between:
- runtime traces
- benchmark/eval outputs
- audit findings
- planners/orchestrators
- project execution agents

---

## 4. CORE PRINCIPLES

### 4.1 Determinism First
Entries must be stored in a form that supports deterministic retrieval and comparison.

### 4.2 Evidence Over Opinion
Every retained pattern should be traceable to measurable execution evidence, known references,
or explicit expert rationale.

### 4.3 One Entry = One Coherent Pattern
Each entry must describe exactly one coherent build, combination, algorithm, workflow pattern,
or execution playbook.

### 4.4 Global vs Project Separation
Reusable cross-project intelligence belongs in `global/`.
Project-specific optimizations belong in `projects/<project-slug>/`.

### 4.5 Promotion by Proof
Status advances only through evidence-backed validation:
`candidate -> validated -> gold`

### 4.6 No Secrets
No secrets, API keys, credentials, raw tokens, private personal data, or unsafe payloads.

### 4.7 Low Noise Policy
Weak, vague, duplicate, or non-reproducible entries must be rejected or archived.

---

## 5. DIRECTORY STRUCTURE

```text
build-memory-library/
  global/
    entries/
  projects/
    <project-slug>/
      entries/
  indexes/
    global_index.json
    project_indexes/
      <project-slug>.json
    tag_index.json
    capability_index.json
    evidence_index.json
    top_ranked_global.json
    top_ranked_by_task.json
  snapshots/
    gold/
    validated/
    planner_packs/
  templates/
    entry.template.json
    playbook.template.json
    build-combination.template.json
  schemas/
    entry.schema.json
    index.schema.json
    query.schema.json
  audit/
    dedupe_reports/
    stale_reports/
    validation_reports/
6. ENTRY TYPES

Allowed entry types:

build_combination
settings_stack
algorithm_pattern
execution_playbook
routing_policy
memory_strategy
benchmark_winner
integration_pattern
recovery_pattern
cost_optimization_pattern

Each entry must have exactly one primary type.

7. ENTRY CONTRACT

Each entry must conform to the following canonical schema.

{
  "id": "bml-global-telegram-free-first-001",
  "version": 1,
  "scope": "global",
  "project_slug": null,
  "status": "candidate",
  "entry_type": "build_combination",
  "title": "Telegram free-first extraction and processing stack",
  "summary": "Low-cost pipeline for Telegram export ingestion and downstream analysis.",
  "problem_class": ["telegram-ingestion", "free-first", "document-normalization"],
  "use_cases": ["chat export", "knowledge extraction", "agent analysis prep"],
  "components": [
    {
      "name": "telegram-desktop-export",
      "role": "data source",
      "version": "stable"
    },
    {
      "name": "normalizer-pipeline",
      "role": "preprocessing",
      "version": "v2"
    }
  ],
  "configuration": {
    "runtime": "local",
    "budget_mode": "free-first",
    "latency_profile": "balanced",
    "reliability_profile": "high"
  },
  "algorithm": {
    "inputs": ["telegram export json/html/txt"],
    "steps": [
      "export raw chat",
      "normalize message structure",
      "split attachments and text",
      "generate metadata manifest",
      "store queryable artifacts"
    ],
    "fallbacks": [
      "if json absent, parse html",
      "if attachment metadata incomplete, create unresolved manifest entries"
    ]
  },
  "evidence": {
    "trace_refs": ["trace:2026-04-10-run-17", "trace:2026-04-11-run-02"],
    "ki_refs": ["ki://telegram/export-guide", "ki://patterns/free-first-ingestion"],
    "benchmark_refs": ["bench:telegram-ingestion-pack-v1"],
    "audit_refs": ["audit:2026-04-10-ingestion-review"],
    "metrics": {
      "success_rate": 0.93,
      "first_pass_success": 0.81,
      "median_latency_sec": 42.1,
      "token_cost_estimate": 0.12,
      "failure_modes_observed": 3
    }
  },
  "scoring": {
    "confidence": 0.84,
    "evidence_strength": 0.78,
    "reusability": 0.88,
    "determinism": 0.91,
    "cost_efficiency": 0.86,
    "overall_score": 0.853
  },
  "constraints": [
    "requires desktop export access",
    "best for medium-size chat histories"
  ],
  "failure_modes": [
    "missing attachments",
    "corrupt export chunks",
    "non-standard timestamp locale"
  ],
  "when_to_use": [
    "budget-sensitive ingestion",
    "repeatable preprocessing required"
  ],
  "when_not_to_use": [
    "real-time streaming chat sync",
    "high-security encrypted-only flows"
  ],
  "supersedes": [],
  "related_entries": ["bml-global-chat-normalization-003"],
  "tags": ["telegram", "free-first", "ingestion", "playbook"],
  "owner_agent": "memory-curator",
  "created_at": "2026-04-14T00:00:00Z",
  "updated_at": "2026-04-14T00:00:00Z",
  "validation": {
    "validated_by": [],
    "validation_runs": 0,
    "gold_promoted_at": null
  }
}
8. REQUIRED FIELDS

Mandatory fields for every entry:

id
version
scope
status
entry_type
title
summary
problem_class
components
configuration
algorithm
evidence
scoring
constraints
failure_modes
when_to_use
when_not_to_use
tags
owner_agent
created_at
updated_at
9. STATUS LIFECYCLE
9.1 candidate

Used for promising but not yet sufficiently verified entries.

Requirements:

at least one concrete use case
at least one evidence source
coherent algorithm and configuration description
9.2 validated

Used for entries that have passed repeatable checks.

Requirements:

at least 2 independent evidence references
at least 2 successful runs or one benchmark-backed validation
no unresolved critical ambiguity
scoring fields populated
9.3 gold

Used for highest-confidence reusable standards.

Requirements:

repeated success across contexts or agents
clear superiority or stability advantage
evidence strength above threshold
approved by curator/governance agent
suitable for planner default recommendation
9.4 deprecated

Used for formerly valid entries that are no longer preferred.

9.5 archived

Used for historical retention without active recommendation.

10. SCORING MODEL

Each entry must expose normalized scoring dimensions in range [0.0 - 1.0].

Core dimensions:

confidence
evidence_strength
reusability
determinism
cost_efficiency
latency_efficiency
stability
maintainability

Default weighted score:

overall_score =
  0.20 * confidence +
  0.18 * evidence_strength +
  0.16 * determinism +
  0.14 * reusability +
  0.10 * stability +
  0.08 * cost_efficiency +
  0.07 * latency_efficiency +
  0.07 * maintainability

Projects may override weights, but global index must preserve the default score for comparability.

11. EVIDENCE MODEL

Accepted evidence sources:

runtime traces
benchmark outputs
eval reports
audits
KI/knowledge references
architecture decisions
regression results
human-reviewed implementation notes

Evidence quality tiers:

E1: anecdotal / single run
E2: repeated local success
E3: benchmark or multi-run validated
E4: cross-project validated
E5: gold-standard reusable pattern with long-term stability

Every entry must have an evidence tier.

12. INDEXING STRATEGY

Indexes are generated artifacts, never manually edited.

Required indexes:

global_index.json
project_indexes/<project-slug>.json
tag_index.json
capability_index.json
evidence_index.json
top_ranked_global.json
top_ranked_by_task.json

Each index must include:

normalized id
title
scope
status
tags
problem_class
score
evidence tier
freshness
linked project
supersession metadata
13. QUERY & RETRIEVAL CONTRACT

The system must support deterministic filters for planners and orchestrators.

Supported query dimensions:

full text
tags
problem class
entry type
scope
status
project slug
evidence tier
score threshold
freshness window
component name
budget mode
reliability profile

Example query object:

{
  "text": "telegram free-first",
  "filters": {
    "scope": ["global", "project"],
    "status": ["validated", "gold"],
    "entry_type": ["build_combination", "execution_playbook"],
    "score_min": 0.75,
    "tags_any": ["telegram", "free-first"]
  },
  "sort": ["overall_score:desc", "evidence_strength:desc", "updated_at:desc"],
  "limit": 10
}

Retrieval order:

exact project gold matches
project validated matches
global gold matches
global validated matches
candidate matches only if explicitly allowed
14. GLOBAL / PROJECT INHERITANCE RULES
Global entries

Store reusable patterns valid across multiple projects.

Project entries

Store local optimizations, tuned settings, project-specific workflows,
domain heuristics, and exceptions.

Inheritance rule

Project queries may inherit global entries unless:

project policy disables inheritance
project has an explicit override
global entry is deprecated for that project context
Override rule

Project-scoped gold entries outrank global validated entries for the same task class.

15. WRITE POLICY

Write access should be role-gated.

Allowed writer roles:

memory-curator
benchmark-agent
audit-agent
planner-agent (candidate only unless promoted)
project-maintainer-agent

Disallowed:

raw runtime agents writing gold entries directly
anonymous write paths
silent overwrite without version bump

All writes must:

validate against schema
run duplicate detection
recompute score
update indexes
write audit log
16. DUPLICATE CONTROL

Before saving a new entry, system must check:

same problem class
overlapping components
same budget/reliability profile
semantic similarity of title/summary
equivalent algorithm steps

Possible actions:

reject as duplicate
merge into existing entry version
save as variant with explicit differentiator
supersede older weaker entry
17. PROMOTION PIPELINE
candidate -> validated

Triggered when:

repeated success observed
benchmark or audit confirms utility
minimum evidence threshold satisfied
validated -> gold

Triggered when:

rank remains high across time
low failure volatility
superior or stable performance confirmed
governance approval succeeds

Promotion must produce:

promotion report
score delta
rationale
linked evidence bundle
18. QUALITY GATES

No entry may enter active indexes if it fails any blocking gate.

Blocking gates:

schema_valid
required_fields_present
no_secrets_detected
evidence_present
score_calculated
duplicate_resolution_complete

Warning gates:

low evidence diversity
stale metrics
ambiguous summary
insufficient failure mode description
19. AGENT ORCHESTRATION LAYER
Roles
memory-harvester: extracts candidate patterns from traces/audits/benchmarks
memory-normalizer: converts raw findings into schema-compliant entries
memory-curator: validates, deduplicates, scores, promotes
planner-reader: retrieves best matches for task planning
governance-agent: enforces lifecycle and policy compliance
Flow
discovery
extraction
normalization
evidence binding
scoring
validation
index rebuild
promotion or archive
planner consumption
20. MEMORY LEARNING LOOP

The library must improve itself over time.

Feedback sources:

benchmark deltas
execution outcomes
planner selection success
regression incidents
human review feedback

Learning actions:

raise or lower score
mark stale
promote or deprecate
suggest new variants
split over-broad entries into atomic units
21. SNAPSHOTS

Snapshots provide optimized retrieval packs for agents with limited context budget.

Required snapshot classes:

gold/global
gold/by-problem-class
validated/recent-winners
planner_packs/<task-family>.json

Planner packs should contain:

top 3-10 entries
concise rationale
failure alerts
cost/stability notes
recommended default path
22. STALENESS POLICY

Entries should be reviewed when:

no validation activity for 90+ days
components changed materially
benchmark performance regressed
dependency versions drifted
conflicting newer gold entry exists

Stale entries may remain searchable but must be marked.

23. SECURITY & SAFETY POLICY

Forbidden content in entries:

secrets
credentials
PII beyond approved operational metadata
exploit payloads
unsafe bypass instructions
unverifiable claims framed as gold standards

Sensitive references should be stored as redacted pointers, not raw payloads.

24. METRICS FOR SYSTEM SUCCESS

Library-level KPIs:

retrieval hit rate
planner adoption rate
first-pass success uplift
repeated experiment reduction
gold entry reuse count
candidate-to-validated conversion rate
validated-to-gold promotion rate
stale entry ratio
duplicate rejection rate
median query latency
25. TOOLING

Recommended commands:

python3 repos/packages/agent-os/scripts/build_memory_library.py rebuild-index
python3 repos/packages/agent-os/scripts/build_memory_library.py query --text "telegram free-first"
python3 repos/packages/agent-os/scripts/build_memory_library.py validate-entry --path <entry.json>
python3 repos/packages/agent-os/scripts/build_memory_library.py promote --id <entry-id> --to validated
python3 repos/packages/agent-os/scripts/build_memory_library.py snapshot --type planner_pack --task-family telegram_ingestion
python3 repos/packages/agent-os/scripts/build_memory_library.py stale-report
26. TEMPLATES

Templates must exist for:

build combination
playbook
settings stack
recovery pattern
benchmark winner

Templates should enforce:

atomicity
evidence binding
score placeholders
constraints/failure modes
use/not-use guidance
27. FAIL-SAFE RULES
Never auto-promote to gold from a single run
Never allow project noise to pollute global gold
Never write entries without evidence pointer
Never overwrite stronger entry with weaker variant
Never return candidate entries to planner defaults unless fallback mode is enabled
28. DEFAULT OPERATING POLICY

Default planner read policy:

include only validated and gold
prefer project over global where conflict exists
require score >= 0.75 unless fallback search requested
show failure modes with every recommendation
expose evidence references for top results

Default write policy:

new discoveries enter as candidate
validation is explicit
gold requires governance approval
29. EXAMPLE USE CASES
selecting the best free-first Telegram ingestion build
retrieving best memory strategy for Obsidian-based agent systems
ranking model-routing patterns for low-cost coding tasks
reusing validated benchmark-winning configs across projects
finding recovery playbooks for brittle desktop automation flows
30. FINAL DESIGN INTENT

Build Memory Library is the long-term operating memory of the Antigravity ecosystem.

Its mission is not just to remember.
Its mission is to turn successful execution into reusable system intelligence.


---

### 5. ULTRA PROMPT (MODE C)

```md
# ULTRA PROMPT — BUILD MEMORY LIBRARY ARCHITECT + IMPLEMENTATION AGENT

You are a Senior AGI Systems Architect and Repository Intelligence Engineer.

Your task is to design, audit, implement, and harden the Build Memory Library subsystem
for the Antigravity agent ecosystem.

## Mission
Transform the existing Build Memory Library from a simple storage concept into a deterministic,
evidence-backed, reusable memory system for planners, orchestrators, benchmark agents,
audit agents, and execution agents.

## Primary Outcomes
You must produce:
1. a full audit of the current memory library design
2. a rebuilt specification if needed
3. implementation-ready schemas and templates
4. indexing and retrieval logic
5. lifecycle/promotion rules
6. validation and fail-safe mechanisms
7. a roadmap for future self-improvement

---

## Phase 1 — Structural Audit
Analyze the current memory library and identify:

- missing contracts
- missing required fields
- retrieval ambiguity
- governance gaps
- lifecycle weaknesses
- deduplication risks
- scale risks
- anti-drift risks
- planner integration gaps
- evidence quality weaknesses

Deliver:
- architectural problem list
- severity ranking
- upgrade priorities
- dependencies with other systems

---

## Phase 2 — System Role Definition
Define the memory library as part of a larger agent architecture.

You must explicitly map:
- who writes to memory
- who reads from memory
- who validates memory
- who promotes entries
- how project memory differs from global memory
- how planners consume retrieved entries deterministically

Deliver:
- architecture map
- role responsibility matrix
- read/write policy table

---

## Phase 3 — Entry Contract Design
Design a strict schema for memory entries.

Each entry must include:
- identity and versioning
- scope and project binding
- status lifecycle
- entry type
- problem class
- component list
- configuration
- algorithm steps
- evidence references
- scoring
- failure modes
- when-to-use / when-not-to-use
- tags and timestamps
- supersession and related-entry links

Rules:
- one entry = one coherent pattern
- no secrets
- no vague summaries
- no unscored validated entries
- no gold entries without repeated proof

Deliver:
- canonical schema
- example entries
- template files
- validation rules

---

## Phase 4 — Retrieval & Ranking Layer
Design deterministic retrieval.

You must define:
- query fields
- filters
- sort order
- inheritance rules between project and global scope
- fallback behavior
- ranking formula
- evidence-aware retrieval behavior

Deliver:
- query contract
- ranking formula
- index structures
- planner-facing retrieval policy

---

## Phase 5 — Governance & Promotion
Implement lifecycle governance:
- candidate
- validated
- gold
- deprecated
- archived

Define:
- promotion conditions
- demotion conditions
- stale rules
- dedupe/merge logic
- versioning behavior
- approval path for gold

Deliver:
- lifecycle state machine
- promotion pipeline
- governance policy
- audit log requirements

---

## Phase 6 — Quality Gates & Fail-Safe
Add hard quality gates.

Blocking gates:
- schema validity
- evidence presence
- no secrets
- duplicate resolution
- score calculation

Warning gates:
- staleness
- low evidence diversity
- vague summary
- insufficient failure modes

Deliver:
- gate list
- gate thresholds
- failure handling logic
- rollback logic for bad promotions

---

## Phase 7 — Implementation Plan
Produce concrete implementation outputs.

Required deliverables:
- final markdown spec
- JSON schema files
- entry templates
- index template
- query examples
- CLI design notes
- integration notes for planners/orchestrators
- migration plan from old structure to new one

Prefer:
- modular code
- deterministic outputs
- composable scripts
- low-maintenance architecture

---

## Phase 8 — Validation
Run a design-level validation on the rebuilt system.

Test for:
- duplicate prevention
- project/global override behavior
- score-based sorting
- stale-entry handling
- promotion logic
- query determinism
- planner-read safety

Deliver:
- test matrix
- expected outcomes
- unresolved risks
- recommended next hardening steps

---

## Output Format
Use this exact structure:

### 1. Executive Summary
### 2. Problems Found
### 3. Architecture Decisions
### 4. Rebuilt Specification
### 5. Schemas and Templates
### 6. Retrieval and Ranking Logic
### 7. Governance and Promotion Rules
### 8. Validation and Quality Gates
### 9. Migration Plan
### 10. Risks and Fail-Safes
### 11. Phase Roadmap

---

## Design Rules
- Do not simplify the system
- Think in subsystems, not isolated files
- Favor evidence-backed determinism
- Design for long-term scale
- Reduce noise and ambiguity
- Add anti-fragility wherever possible
- Ensure planners can consume outputs with minimal ambiguity
- Prefer reusable abstractions over local hacks

---

## Success Criteria
The result is successful only if:
- the memory library becomes queryable and deterministic
- entries become comparable and rankable
- evidence is mandatory and structured
- lifecycle governance is explicit
- global/project separation is robust
- planners can safely reuse top-ranked patterns
- the system can scale without becoming a document dump