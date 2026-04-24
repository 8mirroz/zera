# 🌌 Zera — Qwen Context File

> **Project:** Antigravity Core v4.2 — Agent OS Platform
> **Working Directory:** `/Users/user/zera`
> **Generated:** 2026-04-13

---

## Project Overview

**Antigravity Core** is a multi-agent autonomous development platform — not a framework, but a running system that classifies tasks, routes them to optimal AI models, executes via workflows, learns from outcomes, and maintains semantic memory across sessions.

The project operates as a **platform**, not a sandbox. Every contribution must be production-grade.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **Unified Router** | 5-tier task classification (C1–C5) with model selection and fallback chains |
| **MCP Servers** | Model Context Protocol servers for filesystem, memory retrieval, search, UI generation |
| **Workflow Engine** | 44 workflow definitions for automated task execution |
| **Agent Memory** | BM25-indexed semantic retrieval + LightRAG with 4-layer TTL model |
| **Design System** | Premium UI component library with dark mode, glassmorphism, micro-interactions |
| **Role Contracts** | 7 YAML-defined agent roles with explicit responsibilities |
| **CLI Integration** | 8 AI CLI tools (qwen, codex, claude, kiro, kilo, cline, opencode, superclaude) |
| **Zera Agent** | Self-evolution, command runtime, intelligence subsystem |

### Technologies

- **Node.js:** v22 (via `.nvmrc`)
- **Python:** 3.12 (via `.python-version`)
- **Package managers:** npm (Node), uv (Python)
- **Build/Task runner:** Make (see `Makefile`)
- **Model providers:** OpenRouter gateway, Direct API, Ollama local, MLX local (40+ models)

---

## Directory Structure

```
zera/  (antigravity-core)
│
├── configs/              # Configuration & governance
│   ├── orchestrator/     # router.yaml, models.yaml, role_contracts/, completion_gates.yaml
│   ├── global/           # Strategic layer: connectors, regions, quality gates, observability
│   ├── rules/            # WORKSPACE_STANDARD, AGENT_ONLY, TASK_ROUTING, SECURITY_RULES
│   ├── tooling/          # CLI tools, MCP profiles, providers, SLOs, memory policies
│   └── skills/           # 20 skill packs (7 domain + 13 superpowers)
│
├── repos/                # Production-ready code
│   ├── apps/             # Web applications
│   ├── mcp/              # MCP server implementations (incl. LightRAG)
│   └── packages/         # Shared libraries (agent-os, design-system, mcp-profile-manager, mcp_context)
│
├── .agents/               # Agent runtime
│   ├── config/           # Agent runtime configurations
│   ├── evolution/        # Zera evolution state & logs
│   ├── memory/           # BM25-indexed memory store
│   ├── skills/           # 29 published skills
│   ├── templates/        # Prompt templates T1–T7
│   └── workflows/        # 44 workflow files
│
├── docs/                 # Documentation & knowledge base
│   ├── adr/              # Architecture Decision Records
│   ├── ki/               # 57+ Knowledge Items
│   ├── guides/           # How-to guides
│   ├── patterns/         # Reusable code patterns
│   └── remediation/      # Remediation reports & artifacts
│
├── scripts/              # Operational scripts (44+)
│   ├── zera/             # Zera-specific scripts (evolutionctl, command runtime, self-evolution)
│   ├── benchmarks/       # Benchmark suites
│   ├── hermes/           # Hermes sync scripts
│   ├── internal/         # Internal platform scripts
│   ├── obsidian/         # Obsidian vault integration
│   ├── ops/              # Operational monitoring
│   └── validation/       # Validation scripts
│
├── vault/                # Obsidian vault (knowledge graph, semantic embeddings)
│   ├── loops/            # Evolution loop state
│   ├── knowledge/        # Knowledge base
│   └── 00-overview.md    # Vault entry point
│
├── sandbox/              # Experimental prototyping (entry point for all new code)
├── scratch/              # Scratch space
├── logs/                 # Agent traces, logs, telemetry
└── outputs/              # Generated outputs
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

## Building and Running

### Quick Start

```bash
# 1. Environment setup
cp .env.example .env

# 2. Install dependencies
nvm install && npm install
cd repos/packages/agent-os && uv sync
cd repos/packages/design-system && uv sync  # or pip install -r requirements.txt

# 3. Publish active skills
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills

# 4. Run quality checks
bash scripts/run_quality_checks.sh

# 5. System health check
python3 repos/packages/agent-os/scripts/swarmctl.py doctor
```

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Install all dependencies (Node.js + Python) |
| `make test` | Run smoke tests |
| `make test-all` | Run all test suites (via reliability orchestrator) |
| `make quality` | Run full quality check suite |
| `make doctor` | Run system health check |
| `make clean` | Clean Python cache files |
| `make lightrag-install` | Install LightRAG dependencies |
| `make lightrag-build` | Build LightRAG |
| `make lightrag-test` | Run LightRAG tests |
| `make lightrag-query Q="question"` | Query LightRAG knowledge base |

### Zera Evolution Commands

```bash
# Status
./scripts/zera-evolutionctl status

# Start evolution loop
./scripts/zera-evolutionctl start --cycles 3

# Stop evolution loop
./scripts/zera-evolutionctl stop

# Dry run
./scripts/zera-evolutionctl dry-run --cycles 1

# Tail logs
./scripts/zera-evolutionctl tail

# Self-evolution loop
make self-improve    # update + test-smoke
```

### Environment Variables

Key variables from `.env.example`:

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | OpenRouter gateway access |
| `GEMINI_API_KEY` | Google Gemini API |
| `QDRANT_API_KEY` | Vector database access |
| `HF_TOKEN` | Hugging Face access |
| `NOTEBOOKLM_AUTH_JSON` | NotebookLM integration |
| `VAULT_PATH` | Obsidian vault path (default: `./vault`) |

---

## Key Architectural Concepts

### Task Classification (C1–C5)

| Tier | Name | Agents | Max Tools | Human Audit |
|:----:|------|:------:|:---------:|:-----------:|
| **C1** | Trivial | 1 | 8 | — |
| **C2** | Simple | 1 | 12 | — |
| **C3** | Medium | 2 | 20 | — |
| **C4** | Complex | 3 | 35 | ✅ |
| **C5** | Critical | 3 | 50 | ✅ + Council |

### CLI Tool Routing Matrix

| Tier | Primary | Fallback | Premium |
|:----:|---------|----------|---------|
| C1 | qwen | opencode | kiro (worker) |
| C2 | qwen | kiro | kilo (code) |
| C3 | qwen | kiro | codex |
| C4 | qwen | codex | kiro (supervisor) |
| C5 | qwen | codex | kiro (supervisor) + codex-review |

### Skills System

29 active skills published. Key categories:
- **Domain (7):** design-system-architect, ui-premium, visual-intelligence, telegram-bot, telegram-miniapp, telegram-payments, e-commerce
- **Superpowers (22):** systematic-debugging, writing-plans, executing-plans, verification-before-completion, test-driven-development, dispatching-parallel-agents, and more

Manage skills:
```bash
ls .agents/skills/                                    # List skills
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills  # Publish
```

### Zera Evolution System

The `zera-evolutionctl` script manages Zera's self-evolution lifecycle:
- **Shadow upgrade:** Clone Hermes profile into shadow profile for testing
- **Promotion:** Controlled promotion with attempt binding, rollback capability
- **Algorithms:** karpathy, rsi, darwin-goedel, pantheon, self-improving, karpathy-swarm, ralph, agentic-ci, self-driving, meta-learning
- **State:** `.agents/evolution/` (primary), `vault/loops/.evolve-state.json` (legacy)

---

## Development Conventions

### Definition of Done

**Mandatory for ALL tiers:**
- [ ] Error handling with meaningful messages
- [ ] Documentation updated (`docs/ki/` or `docs/adr/`)
- [ ] Code passes lint/format checks
- [ ] Minimal happy-path test or verification script exists

**Tier-gated (C2+):**
- [ ] Tests pass (C2+)
- [ ] Retrospective written (C3+)
- [ ] Code review evidence collected (C3+)
- [ ] Pattern extracted to `docs/patterns/` (C4+)
- [ ] Human audit completed (C4+)
- [ ] ADR updated (C5)
- [ ] Council review passed (C5)

### Language Policy

| Context | Language |
|---------|----------|
| Technical output (code, logs, CLI) | English |
| System reports, plans, retrospectives | Russian |
| Agent ↔ owner communication | Russian |
| Technical terms/commands | English (as required) |

### Design Principles

- Premium by default — no generic UIs, no placeholder visuals
- Dark mode by default with glassmorphism, depth, layered gradients
- Smooth micro-interactions (hover, focus, transitions)
- Typography: Inter, Outfit, Roboto preferred
- If it looks like a tutorial template, it's wrong

### Absolute Prohibitions

- NO assumptions about architecture or placement
- NO silent refactors (state intent before changing structure)
- NO undocumented behavior
- NO "temporary" hacks in `repos/` (sandbox is for experiments)
- NO creating root-level directories without explicit approval
- NO modifying `configs/rules/*` unless explicitly requested
- NO skipping skills when a relevant skill exists
- NO claiming DONE without passing all applicable gates

---

## Critical Reference Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | Agent operating contract (Layer 1) |
| `RULES.md` | Rule hierarchy entry point (Layer 2) |
| `configs/rules/WORKSPACE_STANDARD.md` | Directory placement, naming conventions |
| `configs/orchestrator/router.yaml` | Task routing source of truth |
| `.agents/workflows/multi-agent-routing.md` | Swarm coordination protocol |
| `Makefile` | Build, test, quality targets |
| `.env.example` | Environment variable template |

---

## Navigation Shortcuts

| Need | Go To |
|------|-------|
| "Where does my code go?" | `configs/rules/WORKSPACE_STANDARD.md` §Placement Matrix |
| "Which tier is my task?" | `configs/orchestrator/router.yaml` |
| "What skills exist?" | `.agents/skills/` |
| "How to run quality checks?" | `bash scripts/run_quality_checks.sh` |
| "What decided architecturally?" | `docs/adr/` |
| "How does routing work?" | `.agents/workflows/multi-agent-routing.md` |
| "System health?" | `swarmctl.py doctor` |

---

## Philosophy

> We are not writing code to make it work.
> We are building systems that **scale**, **read cleanly**, and **feel inevitable**.

Antigravity is not a sandbox.
Antigravity is a **platform**.

Every contribution either **strengthens the platform** or **accumulates debt**.
There is no middle ground.
