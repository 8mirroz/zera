# 🌌 Antigravity Core

> **Agent OS Platform** — multi-agent autonomous development system with model routing, MCP servers, workflow engine, semantic memory, and premium design infrastructure.

```
Version: 4.2  │  Status: Production  │  Tiers: C1–C5  │  Roles: 7  │  Workflows: 44  │  Skills: 29
CLI Tools: 8  │  ADRs: 6+8           │  Knowledge: 57+ items  │  Memory: BM25+LightRAG
```

---

## 🧠 What Is This

Antigravity Core is **not a framework**. It is a **running platform** — a coordinated multi-agent system that classifies tasks, routes them to optimal models, executes via workflows, learns from outcomes, and maintains semantic memory across sessions.

### Core Capabilities

| Capability | What It Does | Status |
|------------|--------------|--------|
| **Unified Router** | 5-tier task classification (C1–C5) with model selection, fallback chains, and workflow-first arbitration | ✅ v4.2 |
| **MCP Servers** | Model Context Protocol servers for filesystem, memory retrieval, search, and UI generation | ✅ Active |
| **Workflow Engine** | 44 workflow definitions for automated task execution — research, codegen, audit, swarm | ✅ Active |
| **Agent Memory** | BM25-indexed semantic retrieval + LightRAG integration with 4-layer TTL model | ✅ Active |
| **Design System** | Premium UI component library with dark mode, glassmorphism, micro-interactions | ✅ Active |
| **Role Contracts** | 7 YAML-defined agent roles with explicit responsibilities and handoff contracts | ✅ Active |
| **CLI Integration** | 8 AI CLI tools (qwen, codex, claude, kiro, kilo, cline, opencode, superclaude) with routing matrix | ✅ Active |
| **Strategic Layer** | `configs/global/` — connector registry, region profiles, quality gates, observability | ✅ v1 |

---

## 🚀 Quick Start

### 1-Minute Orientation

```bash
# Understand the workspace rules (mandatory)
cat configs/rules/WORKSPACE_STANDARD.md

# Check system health
python3 repos/packages/agent-os/scripts/swarmctl.py doctor

# See what skills are available
ls .agents/skills/
```

### 10-Minute Setup

```bash
# 1. Environment
cp .env.example .env

# 2. Dependencies
nvm install && npm install                         # Node.js (v22)
pip install -r repos/packages/agent-os/requirements.txt  # Python (3.12)

# 3. Publish active skills
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills

# 4. Run quality gates
bash scripts/run_quality_checks.sh
```

### Execute Your First Task

```bash
# Via Qwen (free, best quality, primary for all tiers)
qwen -y "Add a Python utility function to repos/packages/"

# Via Codex (premium, syntax-verified, C3+)
cd repos/packages && codex exec --full-auto "Write a test for utils.py"

# Via Kiro (full C1–C5 coverage, model pinning + MCP)
kiro-cli run "Analyze the router.yaml configuration"
```

---

## 🏗️ System Architecture

### Execution Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          TASK INGESTION                              │
│  Incoming request → Classification (C1–C5) → Intent mapping (T1–T7) │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     STRATEGIC ARBITRATION                            │
│  configs/global/routing_policy.yaml — workflow-first decision       │
│  configs/global/region_profiles.yaml — provider/region selection    │
│  configs/global/platform_mode.yaml — consumer/pro/hybrid mode       │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ROUTING ENGINE                                │
│  configs/orchestrator/router.yaml (v4.2) — Source of Truth          │
│  ├─ Tier selection → model alias → fallback chain                   │
│  ├─ Role contract enforcement (7 roles)                             │
│  ├─ Handoff safeguards (no cycles, max depth 2)                     │
│  └─ Ralph Loop activation (C3+: auto-refine up to 7 iterations)     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   MCP SERVERS    │  │   WORKFLOWS      │  │   AGENT MEMORY   │
│  Filesystem      │  │  44 definitions  │  │  BM25 + LightRAG │
│  Memory/Retrieval│  │  Steps → Gates   │  │  4-layer TTL     │
│  Search/UI       │  │  Output schemas  │  │  Session→User    │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXECUTION + OBSERVABILITY                       │
│  configs/global/observability.yaml — 10-field trace tracking        │
│  configs/global/quality_gates.yaml — content-type gates             │
│  configs/orchestrator/completion_gates.yaml — tier DoD gates        │
└─────────────────────────────────────────────────────────────────────┘
```

### Tier Classification

| Tier | Name | Agents | Max Tools | Workflow Path | Human Audit |
|:----:|------|:------:|:---------:|---------------|:-----------:|
| **C1** | Trivial | 1 | 8 | `path-fast` | — |
| **C2** | Simple | 1 | 12 | `path-fast` | — |
| **C3** | Medium | 2 | 20 | `path-quality` | — |
| **C4** | Complex | 3 | 35 | `path-swarm` | ✅ |
| **C5** | Critical | 3 | 50 | `path-swarm` | ✅ + Council |

**Task Types:** T1 (Config) · T2 (Fix) · T3 (Implement) · T4 (Architect) · T5 (Research) · T6 (Design) · T7 (Telegram)

### Role Contracts

| Role | Responsibility | Contract |
|------|---------------|----------|
| **Orchestrator** | Task decomposition, routing, coordination | `configs/orchestrator/role_contracts/orchestrator.yaml` |
| **Architect** | C4–C5 system design, API contracts, data models | `configs/orchestrator/role_contracts/architect.yaml` |
| **Engineer** | C2–C3 implementation, testing, integration | `configs/orchestrator/role_contracts/engineer.yaml` |
| **Reviewer** | Code review, quality gates, security checks | `configs/orchestrator/role_contracts/reviewer.yaml` |
| **Design Lead** | UI/UX, design system, visual consistency | `configs/orchestrator/role_contracts/design_lead.yaml` |
| **Routine Worker** | C1 tasks, formatting, boilerplate | `configs/orchestrator/role_contracts/routine_worker.yaml` |
| **Council** | C5 final review, escalation, governance | `configs/orchestrator/role_contracts/council.yaml` |

---

## 📂 Directory Structure

```
antigravity-core/
│
├── 📋 configs/                    # Configuration & governance
│   ├── orchestrator/              # router.yaml, models.yaml, role_contracts/ (7), completion_gates.yaml
│   ├── global/                    # Strategic layer: connectors, regions, quality gates, observability
│   ├── rules/                     # WORKSPACE_STANDARD, AGENT_ONLY, TASK_ROUTING, SECURITY_RULES
│   ├── tooling/                   # 86 files: CLI tools, MCP profiles, providers, SLOs, memory policies
│   └── skills/                    # 20 skill packs (7 domain + 13 superpowers)
│
├── 🏭 repos/                      # Production-ready code
│   ├── packages/agent-os/         # Python runtime: contracts, routing, memory, observability
│   ├── packages/design-system/    # Premium UI component library
│   ├── mcp/servers/               # MCP server implementations (TypeScript)
│   ├── workflows/                 # Workflow definitions (runtime)
│   ├── data/                      # Data processing, scraping, parsing tools
│   └── telegram/                  # Telegram bots, mini apps, payments
│
├── 🤖 .agents/                     # Agent runtime
│   ├── config/                    # Agent runtime configurations
│   ├── memory/                    # BM25-indexed memory store (memory.jsonl)
│   ├── skills/                    # 29 published skills (from configs/skills/)
│   ├── templates/compressed/      # Prompt templates T1–T7
│   └── workflows/                 # 44 workflow files
│
├── 📚 docs/                       # Documentation & knowledge
│   ├── adr/                       # 6 Architecture Decision Records + 8 specs
│   ├── ki/                        # 57+ Knowledge Items (system docs, benchmarks, retrospectives)
│   ├── guides/                    # How-to guides
│   ├── patterns/                  # Reusable code patterns (Ralph's Loop)
│   ├── architecture/              # System architecture documents
│   ├── playbooks/                 # Operational playbooks
│   └── agent-system/              # Agent system deep docs
│
├── 🧪 sandbox/                    # Experimental prototyping (entry point for all new code)
├── 🛠️ scripts/                    # 44 scripts: CI, quality checks, CLI setup, daemons, sync
├── 📦 templates/                  # Starter kits & boilerplates
├── 🔍 audit/                      # Audit reports (folder-per-date structure)
├── 📊 ops/                        # Operational scripts and monitoring
└── 🧬 Zera/                       # Zera agent: self-evolution, command runtime, intelligence
```

### Placement Rules (enforced)

| Project Type | Location |
|--------------|----------|
| Web apps / sites | `repos/apps/<name>/` |
| Telegram bots / mini apps | `repos/telegram/<name>/` |
| Scraping / parsing | `repos/data/<name>/` |
| MCP servers | `repos/mcp/<name>/` |
| Shared libraries | `repos/packages/<name>/` |

**Sandbox First:** All new work starts in `sandbox/`, moves to `repos/` after validation.

---

## 🔌 CLI Tool Integration

### Tool Registry

| CLI | Version | Status | Best For | Tier Coverage |
|-----|---------|--------|----------|:-------------:|
| **qwen** | 0.14.1 | ✅ Ready | Best quality, primary for all tiers | C1–C4 |
| **kiro** | 1.29.5 | ✅ Ready | Full coverage, model pinning + MCP | C1–C5 |
| **codex** | 0.98.0 | ✅ Ready | Syntax verification, git integration | C3–C5 |
| **claude** | 2.1.79 | ✅ Local Templates | Plan/act modes, creative tasks | C2–C5 |
| **kilo** | 0.26.1 | ⚠️ Config Required | 6 modes: architect/code/ask/debug/orchestrator/review | C2–C5 |
| **cline** | 2.9.0 | ✅ Ready | Plan/act mode switching | C1–C3 |
| **opencode** | 1.3.3 | ✅ Ready | Free, fast, no config needed | C1–C3 |
| **superclaude** | 4.1.6 | ✅ Framework Installed | Framework-based agent modes | C2–C5 |

### Routing Matrix

| Tier | Primary | Fallback | Premium |
|:----:|---------|----------|---------|
| C1 | qwen | opencode | kiro (worker) |
| C2 | qwen | kiro | kilo (code) |
| C3 | qwen | kiro | codex |
| C4 | qwen | codex | kiro (supervisor) |
| C5 | qwen | codex | kiro (supervisor) + codex-review |

### Quick Commands

```bash
# Check all CLI tools
bash scripts/cli_tools_check.sh

# Setup tools that need configuration
bash scripts/setup_kilo.sh    # Provider selection
bash scripts/setup_cline.sh   # Authentication
kiro-cli setup                # Kiro components
```

---

## 🧬 Skills System

29 active skills published from `configs/skills/` to `.agents/skills/`.

### Domain Skills (7)

| Skill | Use When |
|-------|----------|
| `design-system-architect` | Creating or evolving UI component systems |
| `ui-premium` | Building any user-facing interface |
| `visual-intelligence` | Design critique, visual consistency |
| `telegram-bot` | Creating or modifying Telegram bots |
| `telegram-miniapp` | Building Telegram Web App integrations |
| `telegram-payments` | Payment flow implementation |
| `e-commerce` | Shopping, cart, checkout systems |

### Superpowers (22)

| Skill | Use When |
|-------|----------|
| `systematic-debugging` | Any bug, error, or unexpected behavior |
| `writing-plans` | Before implementing multi-step features |
| `executing-plans` | After a plan has been written and approved |
| `verification-before-completion` | Always — final check before claiming done |
| `test-driven-development` | Writing tests before or alongside code |
| `dispatching-parallel-agents` | Decompose and run tasks concurrently |
| `subagent-driven-development` | Delegated multi-agent workflows |
| `react-doctor-analyzer` | Debugging React component issues |
| `brainstorming` | Exploring solution spaces before committing |
| `write-a-prd` | Creating product requirements documents |
| `prd-to-plan` | Converting PRDs to technical implementation plans |
| `requesting-code-review` | Preparing code for review |
| `receiving-code-review` | Processing review feedback |
| `finishing-a-development-branch` | Before PR/merge completion |
| `using-git-worktrees` | Parallel work on multiple branches |
| `git-guardrails` | Safe git operations |
| `triage-issue` | Issue investigation and classification |
| `memfree-engine` | Memory-free retrieval workflows |
| `claude-code-patterns` | Claude-specific pattern matching |
| `grill-me` | Stress-testing ideas through rigorous questioning |
| `design-an-interface` | API/UI interface design |
| `ubiquitous-language` | Domain language alignment across team |

### Managing Skills

```bash
# Publish active skills
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills

# Browse skills
ls .agents/skills/
```

---

## 🌐 External Connectors

`configs/global/connectors_registry.yaml` manages 6 external system connectors:

| Connector | Type | Access | Business Value | Risk |
|-----------|------|--------|:--------------:|:----:|
| **Notion** | Knowledge | Read/Write | High | Medium |
| **Google Drive** | Files | Read/Write | High | Medium |
| **GitHub** | Code | Read/Write | High | High |
| **Gmail** | Communication | Read/Write | Medium | High |
| **Calendar** | Scheduling | Read/Write | Medium | Medium |
| **Telegram** | Messaging | Read/Write | High | Medium |

Each connector has phase-scoping (`allowed_phases`), risk classification, and preferred workflow assignments.

---

## 🌍 Region Profiles

3 geographic profiles for provider selection and fallback:

| Profile | Providers | Fallback Stack | Use Case |
|---------|-----------|----------------|----------|
| **global_west** | OpenAI, Anthropic, Google | Local LLM, cached retrieval | Full internet access |
| **russia_adapted** | DeepSeek, local LLM, hybrid API | Local RAG, offline docs | Sanctions variability |
| **privacy_first** | Local LLM, self-hosted | Local RAG, cached tools | Minimized external calls |

---

## 📊 Observability

10-field telemetry tracking with dashboard schemas:

- `workflow_name` · `duration_ms` · `token_cost` · `tool_calls`
- `success_rate` · `retry_count` · `quality_gate_failures`
- `user_acceptance` · `memory_hit_rate` · `region_profile_used`

Traces written to `logs/agent_traces.jsonl`. Dashboards: workflow efficiency, connector ROI, memory hit rate, artifact acceptance, region fallback rate.

---

## ✅ Definition of Done

A task is **DONE** only if all applicable gates pass:

```yaml
# Mandatory for ALL tiers:
- [ ] Error handling with meaningful messages
- [ ] Documentation updated (docs/ki/ or docs/adr/)
- [ ] Code passes lint/format checks
- [ ] Minimal happy-path test or verification script exists

# Tier-gated (C2+):
- [ ] Tests pass (C2+)
- [ ] Retrospective written (C3+)
- [ ] Code review evidence collected (C3+)
- [ ] Pattern extracted to docs/patterns/ (C4+)
- [ ] Human audit completed (C4+)
- [ ] ADR updated (C5)
- [ ] Council review passed (C5)
```

---

## 📖 Documentation Index

### Getting Started
- **[Agent Onboarding](docs/AGENT_ONBOARDING.md)** — Complete agent system overview
- **[Workspace Standards](configs/rules/WORKSPACE_STANDARD.md)** — Directory structure, placement rules
- **[Rules Entry Point](RULES.md)** — Rule hierarchy and swarmctl commands

### Architecture
- **[ADR-001](docs/adr/ADR-001_routing_consolidation.md)** — Routing architecture decision
- **[ADR-002](docs/adr/ADR-002_bm25_over_hnsw.md)** — Memory system decision
- **[ADR-003](docs/adr/ADR-003_yaml_role_contracts.md)** — YAML role contracts
- **[ADR-004](docs/adr/ADR-004_prompt_compression.md)** — Prompt compression
- **[ADR-005](docs/adr/ADR-005_mcp_security.md)** — MCP security standards
- **[ADR-006](docs/adr/ADR-006_claw_code_integration.md)** — CLAW code integration

### Knowledge Base
- **[Agent OS v2 (RU)](docs/ki/AGENT_OS_V2_RU.md)** — Full platform documentation
- **[CLI Tools Audit](docs/ki/CLI_TOOLS_AUDIT_2026-03-11.md)** — CLI integration audit
- **[Hermes Profile](docs/ki/HERMES_PROFILE_CONSOLIDATION_2026-04-09.md)** — Profile consolidation
- **[Transformation Metrics](docs/adr/TRANSFORMATION_METRICS.md)** — 10-phase transformation metrics
- **[57+ Knowledge Items](docs/ki/)** — Benchmarks, retrospectives, system analyses

### Guides
- **[Browser Use Workflow](.agents/workflows/browser-use.md)** — Web automation guide
- **[Multi-Agent Routing](.agents/workflows/multi-agent-routing.md)** — Swarm coordination (v3.1)
- **[Ralph Loop](.agents/workflows/ralph-loop.md)** — Iterative refinement loop

---

## 🛠️ Operational Commands

### Health & Quality

```bash
# Full quality check
bash scripts/run_quality_checks.sh

# System health
python3 repos/packages/agent-os/scripts/swarmctl.py doctor

# CLI tools check
bash scripts/cli_tools_check.sh

# System health (extended)
bash scripts/system_health_check.sh
```

### Memory & Skills

```bash
# Publish skills
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills

# Generate experience graph
python3 scripts/generate_experience_graph.py

# Query experience
python3 scripts/query_experience.py
```

### Zera Agent

```bash
# Command runtime
python3 scripts/zera_command_runtime.py

# Agent intelligence
bash scripts/zera-agent-intelligence.sh

# Self-evolution
bash scripts/zera-self-evolution.sh
```

### Sync & Integration

```bash
# Environment bootstrap
bash scripts/bootstrap_env.sh

# Hermes sync
bash scripts/hermes-sync-config.sh

# Obsidian integration
bash scripts/zera-obsidian-integration.sh
```

---

## 🧠 Model Stack

### Tiers (free-first strategy)

| Tier | Alias | Model | Purpose |
|------|-------|-------|---------|
| Builder A | `AGENT_MODEL_BUILDER_A` | deepseek/deepseek-v3:free | Primary construction |
| Builder B | `AGENT_MODEL_BUILDER_B` | google/gemini-2.0-flash-exp:free | Fast iteration |
| Builder C | `AGENT_MODEL_BUILDER_C` | qwen/qwen3-next-80b-a3b-instruct:free | Design + quality |
| Reviewer | — | mistralai/mistral-small-24b-instruct-2501:free | Code review |
| Orchestrator | — | deepseek/deepseek-v3:free | Task orchestration |
| Council | — | deepseek/deepseek-r1:free | C5 governance |

### Provider Topology

40+ models across 4 tiers: `free` · `light` · `quality` · `reasoning`

Providers: OpenRouter gateway · Direct API · Ollama local · MLX local

Full catalog: `configs/tooling/model_providers.json`

---

## 🔒 Security

- **MCP Security:** Path validation per ADR-005, rate limiting, audit logging
- **Role Contracts:** 7 YAML contracts enforce responsibility boundaries
- **Handoff Safeguards:** Max chain depth 2, cycle prevention, contract required
- **Completion Gates:** Tier-gated quality with human audit for C4+
- **Connector Risk:** Each external connector classified by risk level and phase scope

---

## 🔄 Development Workflow

```
1. Research     →  Read docs/ki/, check existing patterns
2. Prototype    →  Build in sandbox/<project-slug>/
3. Validate     →  Quality checks, happy-path test
4. Promote      →  Move to repos/, add documentation
5. Learn        →  Retro → patterns → memory capture
```

### Sandbox Rules

- ALL new work starts in `sandbox/`
- Experimental, broken, incomplete code is allowed here
- Once validated → move to `repos/`
- Never commit unvalidated code to `repos/`

---

## 📜 Language Policy

| Context | Language |
|---------|----------|
| Technical output (code, logs, CLI) | English |
| System reports, plans, retrospectives | Russian |
| Agent → owner communication | Russian |
| Technical terms/commands | English (as required by tools) |

---

## 🧭 Navigation Shortcuts

| Need | Go To |
|------|-------|
| "Where does my code go?" | `configs/rules/WORKSPACE_STANDARD.md` §Placement Matrix |
| "Which tier is my task?" | `configs/orchestrator/router.yaml` |
| "What skills exist?" | `.agents/skills/` |
| "How to run quality checks?" | `bash scripts/run_quality_checks.sh` |
| "What decided architecturally?" | `docs/adr/` |
| "How does routing work?" | `.agents/workflows/multi-agent-routing.md` |
| "System health?" | `swarmctl.py doctor` |
| "Folder audit knowledge?" | `audit/090426/` |

---

## 🌌 Philosophy

> We are not writing code to make it work.
> We are building systems that **scale**, **read cleanly**, and **feel inevitable**.

Antigravity is not a sandbox.
Antigravity is a **platform**.

Every contribution either **strengthens the platform** or **accumulates debt**.
There is no middle ground.

---

*Antigravity Core v4.2 · Agent OS Platform · 2026*
