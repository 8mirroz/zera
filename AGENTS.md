# 🌌 AGENTS — Antigravity Core Protocol

> [!IMPORTANT]
> **Entry point for all autonomous agents.** This is the operating contract — not a guide.
> Read it. Internalize it. Execute against it.
> This is the **Thin Layer**. Deep knowledge is accessed via **Progressive Disclosure** (Skills → Rules → Workflows).

---

## ⚡ Zero Law: Production or Nothing

```
antigravity-core ≠ playground
antigravity-core = platform
```

**Absolute mandates:**
- ✅ Production-grade code only — no hacks, no "temp" solutions, no "we'll fix it later"
- ✅ Architectural integrity — understand the system before modifying it
- ✅ Premium by default — no generic UIs, no placeholder logic, no lazy defaults
- ✅ Zero chaos — every file, every directory, every change must be intentional

**Violations are not tolerated.** If you're unsure → ask. If you're guessing → stop. If you're uncertain → sandbox first.

---

## 🧭 Navigation Map

The system operates on **4 layers of knowledge**, each accessible on demand:

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — AGENTS.md (you are here)                        │
│  Core protocol, non-negotiable rules, critical paths        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 — RULES.md + rules.registry.yaml → configs/rules/* │
│  Human index + machine manifest for workspace/routing rules  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3 — .agent/skills/*  |  .agent/workflows/*          │
│  Capabilities (what to do)  |  Procedures (how to do it)   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 4 — docs/adr/*  |  docs/ki/*  |  docs/patterns/*    │
│  Decisions              |  Knowledge    |  Reusable code    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 5 — Improvement Platform (NEW)                       │
│  prompts/master/*  |  workflows/definitions/*                │
│  configs/orchestrator/{routing,schedules,quality,registry}   │
│  configs/metadata/*  |  configs/governance/*                  │
│  scripts/{intake,audit,remediation,evaluation,reporting,cleanup} │
│  reports/{audits,updates,tests,summaries}/                     │
│  runtime/{queue,locks,state,manifests,cache}                   │
└─────────────────────────────────────────────────────────────┘
```

**Rule:** Never skip layers. Layer 1 → Layer 2 → Layer 3 → Layer 4. Progressive disclosure is not optional — it's the system's compression algorithm.

---

## 🔗 Critical Artifacts — Read Before Acting

| Artifact | Purpose | When to Read |
|----------|---------|--------------|
| [`RULES.md`](./RULES.md) | Entry point to rule hierarchy + `swarmctl` commands | Always, before any structural change |
| [`rules.registry.yaml`](./configs/rules/rules.registry.yaml) | Machine manifest: canonical order/status/consumers of rule docs | Before loader/catalog/runtime rule changes |
| [`WORKSPACE_STANDARD`](./configs/rules/WORKSPACE_STANDARD.md) | Canonical placement, naming, directory responsibilities | Before creating/moving any file |
| [`router.yaml`](./configs/orchestrator/router.yaml) | Source of Truth for task routing (C1–C5 tiers) | Before accepting or classifying any task |
| [`multi-agent-routing`](./.agent/workflows/multi-agent-routing.md) | Swarm coordination protocol (v3.1) | Before spawning or coordinating agents |

**Minimum viable context for any task:**
1. Read this file (done ✓)
2. Read `WORKSPACE_STANDARD.md`
3. Scan relevant skills in `.agent/skills/`
4. Check for existing workflows in `.agent/workflows/`

---

## 🧬 Skills System — Don't Reinvent, Activate

Skills are **battle-tested, peer-reviewed procedural knowledge**. They encode patterns that would take hours to derive from scratch. Using them is not optional for known problem domains.

### Skill Discovery Protocol

```bash
# List all available skills
ls -la .agent/skills/

# Check active skill manifest
cat .agent/skills/.active_set_manifest.json
```

### Skill Categories

**Domain Expertise (7):**
| Skill | Use When |
|-------|----------|
| `design-system-architect` | Creating or evolvinging UI component systems |
| `ui-premium` | Building any user-facing interface |
| `visual-intelligence` | Design critique, visual consistency checks |
| `telegram-bot` | Creating or modifying Telegram bots |
| `telegram-miniapp` | Building Telegram Web App integrations |
| `telegram-payments` | Payment flow implementation |
| `e-commerce` | Shopping, cart, checkout systems |

**Superpowers (13+):**
| Skill | Use When |
|-------|----------|
| `systematic-debugging` | Any bug, error, or unexpected behavior |
| `writing-plans` | Before implementing multi-step features |
| `executing-plans` | After a plan has been written and approved |
| `verification-before-completion` | Always — as a final check before claiming done |
| `test-driven-development` | Writing tests before or alongside code |
| `dispatching-parallel-agents` | When tasks can be decomposed and run concurrently |
| `subagent-driven-development` | For delegated multi-agent workflows |
| `react-doctor-analyzer` | Debugging React component issues |
| `prd-to-plan` | Converting product requirements to technical plans |
| `brainstorming` | Exploring solution spaces before committing |
| `finishing-a-development-branch` | Before PR/merge completion |
| `git-guardrails` | Safe git operations, branch management |
| `using-git-worktrees` | Parallel work on multiple branches |

### Activation Pattern

```
Task identified → Skill exists → Activate skill → Follow procedure
Task identified → No skill → Check if should be created → Document in docs/ki/
```

**Mandate:** If a skill exists and you don't use it, you've failed the task.

---

## 🌐 Browser Automation — Agentic Web Protocol

When web interaction is required:

**Mandatory stack:**
- CDP-based tools / Browser Use CLI with **persistent session** support
- NO raw Playwright script spinning from scratch (unless explicitly justified)
- Reference workflow: `/browser-use`

**Why:** Persistent sessions reduce browser startup overhead by ~90% and dramatically improve agent chain stability.

**Quick start:**
```bash
# Use the browser-use workflow
# Follow instructions in .agent/workflows/browser-use.md
```

**Anti-patterns:**
- ❌ Launching a new browser instance per request
- ❌ Hardcoded selectors without fallback strategies
- ❌ No session reuse across related tasks

---

## ✅ Definition of Done — The Completion Gate

A task is **DONE** only when **all** gates pass. No exceptions. No "good enough". No "we'll do it later".

### Mandatory Gates (All Tiers)

```yaml
error_handling:
  status: required
  detail: All failure modes addressed with meaningful messages

documentation:
  status: required
  locations:
    - docs/adr/  # Architectural decisions
    - docs/ki/   # New system knowledge
  detail: Behavior changes → docs updated

quality:
  status: required
  checks:
    - lint passes
    - format clean
    - no syntax warnings
  verification: release-checklist skill

minimum_test:
  status: required
  detail: Happy-path test or verification script exists
```

### Tier-Gated Gates (C1–C5)

| Gate | C1 | C2 | C3 | C4 | C5 |
|------|:--:|:--:|:--:|:--:|:--:|
| Tests | — | ✅ | ✅ | ✅ | ✅ |
| Retrospective | — | — | ✅ | ✅ | ✅ |
| Code Review | — | — | ✅ | ✅ | ✅ |
| Pattern Extraction | — | — | — | ✅ | ✅ |
| Human Audit | — | — | — | ✅ | ✅ |
| ADR Update | — | — | — | — | ✅ |
| Council Review | — | — | — | — | ✅ |

**If any applicable gate is missed → task is NOT DONE.**

---

## 🔌 MCP Servers — Reality Interface Protocol

The system connects to external capabilities via **Model Context Protocol**. This is not optional infrastructure — it is the primary interface to reality.

### Usage Mandate

```
MCP tools available → use them FIRST
No MCP tool → search fallback (search_web)
```

**Common MCP tools:**
- `stitch` — UI generation via Design System
- `context7` — Documentation access
- Filesystem servers — File operations with path validation
- BM25 memory — Semantic retrieval from agent memory

**Configuration:** `mcp_config.json`

**Security:** All MCP requests are audited. Path validation is enforced per ADR-005. Rate limiting is active.

### Anti-Patterns

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| Using `search_web` for known docs | Use `context7` MCP first |
| Building UI from scratch | Use `stitch` MCP first |
| Direct file operations without validation | Use filesystem MCP (path-guaranteed) |
| Ignoring rate limit rejections | Back off, retry with exponential delay |

---

## 🏛️ Architecture Quick Reference

### Task Routing System

```
Incoming Task
    │
    ▼
┌─────────────────────┐
│  Classification     │  C1 → Trivial   (1 agent, 8 tools max)
│  C1–C5 Tier         │  C2 → Simple    (1 agent, 12 tools max)
│                     │  C3 → Medium    (2 agents, 20 tools max)
│                     │  C4 → Complex   (3 agents, 30 tools, human audit)
│                     │  C5 → Critical  (3 agents, 50 tools, human audit)
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Model Selection     │  Primary: qwen (best quality)
│  + CLI Routing       │  Fallback: kiro / opencode
│                     │  Premium: codex / kiro (supervisor)
└─────────────────────┘
```

### Directory Responsibility Matrix

```
antigravity-core/
│
├── configs/          → Governance, rules, orchestrator, skills source
├── docs/             → Knowledge storage (ki, adr, guides, patterns)
├── repos/            → Production code (apps, telegram, data, mcp, packages)
├── sandbox/          → Experimental work (entry point for all new code)
└── templates/        → Starter kits (clean, minimal, opinionated)
```

**Placement rule:** See [`WORKSPACE_STANDARD.md`](./configs/rules/WORKSPACE_STANDARD.md) §Placement Matrix

---

## 🚫 Absolute Prohibitions

These are not guidelines. These are **hard stops**. Violating any of these constitutes a task failure.

```yaml
prohibitions:
  - NO assumptions about architecture or placement
  - NO silent refactors (state intent before changing structure)
  - NO undocumented behavior (code must be self-explanatory or documented)
  - NO "temporary" hacks in repos/ (sandbox is for experiments)
  - NO creating root-level directories without explicit approval
  - NO modifying configs/rules/* unless explicitly requested
  - NO skipping skills when a relevant skill exists
  - NO claiming DONE without passing all applicable gates
```

---

## 🎨 Design DNA — Premium by Default

All user-facing output must adhere to these principles:

```yaml
design_principles:
  premium_first:
    - No generic UI components without customization
    - No default color schemes
    - No placeholder visuals

  modern_aesthetics:
    - Dark mode by default
    - Glassmorphism, depth, layered gradients
    - Smooth micro-interactions (hover, focus, transitions)

  typography:
    preferred: [Inter, Outfit, Roboto]
    hierarchy: Clear, deliberate, consistent
    legibility: Non-negotiable

  motion:
    - Subtle, meaningful animations
    - Purposeful state transitions
    - No gratuitous motion
```

**Rule:** If it looks like a tutorial template, it's wrong.

---

## 🗣️ Language Policy

```yaml
technical_output: English       # Code, logs, CLI commands, error messages
system_reports: Russian         # Reports to owner, plans, retrospectives
communication: Russian          # Agent → owner interaction
technical_terms: English        # When tools/conventions require it
```

**Rule:** Any English system message in a Russian report must include a Russian explanation.

---

## ⚙️ Operational Commands

```bash
# System health check
python3 repos/packages/agent-os/scripts/swarmctl.py doctor

# Publish active skills
python3 repos/packages/agent-os/scripts/swarmctl.py publish-skills

# Quality gates (full suite)
bash scripts/run_quality_checks.sh

# CLI tools check
bash scripts/cli_tools_check.sh

# ─── Improvement Platform Commands ───────────────────────────────

# List configured schedules
python3 scripts/intake/scheduler.py --list-schedules

# Run audit for specific scope
python3 scripts/intake/scheduler.py --scope configs-global

# Validate document front-matter and naming compliance
python3 scripts/cleanup/validate_documents.py

# Check active scope locks
python3 -c "from scripts.intake.scope_lock import ScopeLock; print(ScopeLock.list_active_locks())"

# Generate artifact ID
python3 -c "from scripts.intake.run_id import generate_artifact_id; print(generate_artifact_id('AUD', 'configs-global'))"
```

---

## 🧠 Operating Philosophy

> We are not writing code to make it work.
> We are building systems that **scale**, **read cleanly**, and **feel inevitable**.

Antigravity is not a sandbox.
Antigravity is a **platform**.

Every contribution either:
- **Strengthens the platform** — or —
- **Accumulates debt**

There is no middle ground.

---

*Protocol version: 2.0.0 | Last updated: 2026-04-09 | Status: Active*
