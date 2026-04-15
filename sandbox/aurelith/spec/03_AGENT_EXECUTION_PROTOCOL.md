# AURELITH — Agent Execution Protocol
Version: 1.0
Role: L1 / Deterministic Build Protocol
Owner: Orchestrator Agent
Depends on:
- 01_MASTER_CREATIVE_EXECUTION_BRIEF.md
- 02_PRODUCT_UX_UI_MOTION_SYSTEM_SPEC.md

## 1. Purpose

This protocol instructs the agent to execute the landing-page task from concept to production-ready specification and partial implementation pattern with full traceability.

The agent must not jump directly into code.
The agent must follow phase gates.

---

## 2. Execution Model

Execution graph:
discovery -> concept lock -> IA lock -> UI/motion lock -> architecture lock -> implementation skeleton -> QA/governance -> release-ready package

Each phase must end with:
- outputs produced
- decisions logged
- risks recorded
- unresolved items listed
- gate status assigned

Gate statuses:
- PASS
- PASS_WITH_WARNINGS
- BLOCKED

---

## 3. Mandatory Deliverables Per Phase

### Phase 1 — Discovery
Goal:
understand the brief and lock the product narrative

Required outputs:
- product definition summary
- emotional positioning summary
- brand promise summary
- visual metaphor lock
- conversion model lock

Checks:
- fictional product coherent
- premium direction credible
- motion narrative justified

### Phase 2 — Information Architecture
Goal:
build full section order and logic

Required outputs:
- ordered section map
- per-section purpose
- question each section answers
- CTA logic map
- content density rhythm map

Checks:
- no filler sections
- no duplicated selling logic
- narrative progression coherent

### Phase 3 — UI + Motion Spec
Goal:
fully describe visible system behavior

Required outputs:
- section-by-section UI spec
- hero breakdown
- motion categories
- responsive adaptation rules
- reduced-motion behavior

Checks:
- motion supports clarity
- typography remains readable
- desktop/mobile parity preserved conceptually

### Phase 4 — Frontend Architecture
Goal:
translate design system into build system

Required outputs:
- component tree
- file/folder structure
- token map
- client/server boundary notes
- GSAP/Framer separation strategy

Checks:
- architecture production-buildable
- no animation conflict risk
- no unnecessary clientification

### Phase 5 — Partial Implementation Skeleton
Goal:
provide correct implementation patterns

Required outputs:
- Lenis setup
- ScrollTrigger hook pattern
- Framer variants pattern
- reusable reveal hook
- reduced motion hook
- magnetic button pattern
- optional lazy R3F pattern

Checks:
- patterns are reusable
- code is typed
- cleanup logic present
- performance traps avoided

### Phase 6 — QA + Governance
Goal:
make delivery resilient and reviewable

Required outputs:
- QA checklist
- acceptance criteria
- performance rules
- accessibility rules
- release risk register

Checks:
- no missing launch-critical category
- measurable acceptance criteria exist
- reduced motion and keyboard flow covered

---

## 4. Agent Reasoning Rules

The agent must explicitly document:
- why GSAP is used in a given section
- why Framer Motion is used in a given component
- why a section is pinned or not pinned
- why 3D is included or excluded
- why a given CTA model is optimal
- why mobile behavior differs from desktop

The agent must reject vague decisions.

Bad:
“Use animation for premium feel.”

Good:
“Use GSAP pinned storytelling in the hero because the product metaphor requires layered reveal across 180–220vh, and this cannot be expressed as a simple component-local interaction without narrative collapse.”

---

## 5. Library and Build Tracking

The agent must track:

### Configs
- Next.js app settings relevant to metadata and rendering
- Tailwind or token config
- motion config layer
- lint/type settings if referenced

### Build Decisions
- which libraries are used
- where they are used
- where they are explicitly forbidden
- performance impact of each heavy dependency

### Agent Library Usage
If the surrounding system has agent libraries, templates, prompt packs, motion snippets, architecture templates, or code patterns, the agent must:
- inspect what is available
- rank relevance
- choose selectively
- record why selected or rejected

---

## 6. Subagent Invocation Protocol

The main agent may call subagents, but only with scoped briefs.

Allowed subagent classes:
- brand strategist
- creative director
- UX architect
- motion director
- frontend architect
- performance engineer
- accessibility auditor
- QA reviewer
- copy specialist

Each subagent brief must contain:
- narrow scope
- expected output format
- constraints
- no-overlap boundary
- acceptance signal

Subagent outputs must be merged by the orchestrator, not pasted blindly.

---

## 7. Progress Trace Format

For every major phase, record:

- Phase Name
- Objective
- Inputs Used
- Decisions Made
- Rejected Alternatives
- Risks
- Output Files Updated
- Gate Status

---

## 8. Failure Handling

If a section becomes too decorative:
- reduce motion density
- simplify surface effects
- strengthen information hierarchy

If performance risk rises:
- remove blur/filter-heavy layers
- replace continuous animation with event-driven motion
- lazy-load optional visuals
- drop 3D before sacrificing readability

If accessibility conflict appears:
- accessibility wins over spectacle
- provide alternative interaction pattern
- preserve meaning in reduced motion

---

## 9. Hard Prohibitions

Do not:
- animate every section equally
- build a hero that delays user action
- rely on 3D for core information
- put essential text inside inaccessible graphics
- create hover-only meaning
- create mobile-hostile pin sections
- create implementation plans without cleanup logic
- produce specs without measurable QA gates
