---
name: prd-to-plan
description: Turn a PRD into a multi-phase implementation plan using tracer-bullet vertical slices. Use when user has a PRD and wants an implementation plan, or mentions "turn PRD into plan".
source: https://github.com/mattpocock/skills/tree/main/prd-to-plan
---

# PRD to Plan

Converts a PRD (GitHub issue or document) into a phased implementation plan with tracer-bullet vertical slices.

## Process

1. **Read the PRD** — locate the GitHub issue or document. Ask user if not found.

2. **Identify modules** — list all modules from Implementation Decisions. Map dependencies between them.

3. **Design tracer bullet** — find the thinnest vertical slice that touches all layers (UI → API → DB). This is Phase 1.

4. **Phase the work**:
   - Phase 1: Tracer bullet (end-to-end skeleton, no polish)
   - Phase 2–N: Vertical slices adding one behavior at a time
   - Final phase: Polish, error handling, edge cases

5. **Write the plan** to `docs/plans/YYYY-MM-DD-<feature>-plan.md`:

```md
## Phase 1: Tracer Bullet
Goal: [thin end-to-end slice]
- [ ] [task]

## Phase 2: [Behavior]
Goal: [what user can do after this phase]
- [ ] [task]

## Out of Scope
[Explicit exclusions]
```

6. **File as GitHub issue** linking back to the PRD issue.

## Key Rules
- Each phase = deployable increment
- Vertical slices only (no horizontal layers)
- Tracer bullet first — always
- Reference `writing-plans` skill for plan format standards
